#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][SecureString]$AccessToken,
    [ValidatePattern('^\d+$')][string]$PropertyId = '558518317',
    [uri]$SiteUrl = 'https://adapt-base.com/',
    [datetime]$StartDate = (Get-Date).Date.AddDays(-10),
    [datetime]$EndDate = (Get-Date).Date.AddDays(-3),
    [string]$OutputDirectory = (Join-Path $PWD 'AnalyticsResults')
)
$ErrorActionPreference = 'Stop'
if ($StartDate -gt $EndDate) { throw 'StartDate must not be after EndDate.' }
$Start = $StartDate.ToString('yyyy-MM-dd')
$End = $EndDate.ToString('yyyy-MM-dd')
$TokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($AccessToken)
try {
    $Headers = @{ Authorization = 'Bearer ' + [Runtime.InteropServices.Marshal]::PtrToStringBSTR($TokenPointer) }
    $null = New-Item -ItemType Directory -Path $OutputDirectory -Force
    foreach ($Report in @(
        @{ Name = 'GA4_Pages'; Dimensions = @('date','pagePath'); Metrics = @('screenPageViews','sessions','totalUsers') },
        @{ Name = 'GA4_Events'; Dimensions = @('date','eventName'); Metrics = @('eventCount') }
    )) {
        $Offset = 0; $Rows = [Collections.Generic.List[object]]::new()
        do {
            $RequestBody = @{
                dateRanges = @(@{startDate=$Start;endDate=$End})
                dimensions = @($Report.Dimensions | ForEach-Object { @{name=$_} })
                metrics = @($Report.Metrics | ForEach-Object { @{name=$_} })
                limit = '10000'; offset = [string]$Offset
            }
            $Result = Invoke-RestMethod -Method Post -Uri "https://analyticsdata.googleapis.com/v1beta/properties/${PropertyId}:runReport" -Headers $Headers -ContentType 'application/json' -Body ($RequestBody | ConvertTo-Json -Depth 10)
            foreach ($Row in $Result.rows) {
                $Values = [ordered]@{}
                for ($I=0; $I -lt $Report.Dimensions.Count; $I++) { $Values[$Report.Dimensions[$I]]=$Row.dimensionValues[$I].value }
                for ($I=0; $I -lt $Report.Metrics.Count; $I++) { $Values[$Report.Metrics[$I]]=$Row.metricValues[$I].value }
                $Rows.Add([pscustomobject]$Values)
            }
            $Offset += @($Result.rows).Where({ $null -ne $_ }).Count
        } while ($Offset -lt $Result.rowCount -and $Result.rows.Count -gt 0)
        $Rows | Export-Csv -Path (Join-Path $OutputDirectory ($Report.Name+'.csv')) -NoTypeInformation -Encoding utf8BOM
        @{ startDate=$Start;endDate=$End;rowCount=$Rows.Count;metadata=$Result.metadata } | ConvertTo-Json -Depth 20 | Set-Content (Join-Path $OutputDirectory ($Report.Name+'_Metadata.json')) -Encoding utf8
    }
    $SearchRows = [Collections.Generic.List[object]]::new(); $Offset = 0
    do {
        $Result = Invoke-RestMethod -Method Post -Uri ('https://www.googleapis.com/webmasters/v3/sites/'+[uri]::EscapeDataString($SiteUrl.AbsoluteUri)+'/searchAnalytics/query') -Headers $Headers -ContentType 'application/json' -Body (@{startDate=$Start;endDate=$End;dimensions=@('date','page');rowLimit=25000;startRow=$Offset;dataState='final'} | ConvertTo-Json -Depth 10)
        foreach ($Row in $Result.rows) { $SearchRows.Add([pscustomobject]@{date=$Row.keys[0];page=$Row.keys[1];clicks=$Row.clicks;impressions=$Row.impressions;ctr=$Row.ctr;position=$Row.position}) }
        $Count = @($Result.rows).Where({$null -ne $_}).Count; $Offset += $Count
    } while ($Count -eq 25000)
    $SearchRows | Export-Csv (Join-Path $OutputDirectory 'SearchConsole_Pages.csv') -NoTypeInformation -Encoding utf8BOM
    Write-Output ([pscustomobject]@{StartDate=$Start;EndDate=$End;OutputDirectory=$OutputDirectory;SearchRows=$SearchRows.Count})
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($TokenPointer)
    if ($Headers) { $Headers.Clear() }
}
