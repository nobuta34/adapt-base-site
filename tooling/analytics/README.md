# External analytics collection v0.1

管理者: adaptbasejp@gmail.com。GA4プロパティID: 558518317、測定ID: G-ZMGS0R556P。
Search Console対象: https://adapt-base.com/ (URLプレフィックス。wwwの別プロパティやDNSドメイン確認は含まない)。

## 現在の状態
サイト計測とSearch Console所有権確認は完了。外部APIでの実データ取得とAWS配置は未完了。コードは認証済み環境で動作させるための初版。

## 必要なGoogle設定
Google CloudプロジェクトでGoogle Analytics Data APIとSearch Console APIを有効化する。GCP計算サービス・BigQuery・課金契約は、このAPI取得コードの必須条件ではない。
読み取り専用OAuthスコープ: https://www.googleapis.com/auth/analytics.readonly と https://www.googleapis.com/auth/webmasters.readonly 。
OAuthクライアントでadaptbasejp@gmail.comの同意を取得する。OAuth公開状態がTestingの場合、継続運用でrefresh token失効条件を確認し、Testingのまま定期運用しない。認証情報はチャット・Git・サイトへ掲載しない。

## Windows / PowerShell 7
認証済みアクセストークンを安全に取得した後に実行する。以下のプロンプトはアクセストークン用で、Googleアカウントのパスワードではない。

```powershell
$Token = Read-Host 'Google OAuth access token' -AsSecureString
.\Get-AdaptBaseAnalytics.ps1 -AccessToken $Token -PropertyId '558518317' -SiteUrl 'https://adapt-base.com/' -OutputDirectory 'C:\wk\adapt-base\AnalyticsResults'
Remove-Variable Token
```

GA4_Pages.csv、GA4_Events.csv、SearchConsole_Pages.csvとGA4のmetadata JSONを作成する。初期値は10日前～3日前。遅延を考慮して確定データ中心に取得する。空データは登録直後などに発生する。Search Console APIは全行の網羅を保証しない。GA4のmetadataにしきい値・サンプリング情報がある場合は解釈に反映する。
PowerShell実行環境がこの制作環境にないため、実行検証は未実施。AWS側Pythonはモック検証のみ。実APIでの受入試験が必要。

## AWS配置
aws/template.yamlはSAMテンプレート。Secrets Managerの既存secretにOAuthのclient_id、client_secret、refresh_tokenを格納し、そのARNを渡す。独自KMSキーでsecretを暗号化した場合は、キー側の許可とkms:Decrypt権限を追加する必要がある。

```powershell
Set-Location .\aws
sam build --template-file template.yaml
sam deploy --guided --stack-name adapt-base-analytics --capabilities CAPABILITY_IAM --parameter-overrides OAuthSecretArn='<existing-secret-arn>' EnableSchedule=false
```

デプロイ先AWSアカウント・リージョンを確認してから実行する。初期はスケジュール無効。手動Lambda実行でAPI応答とS3保存を確認後、EnableSchedule=trueへ更新する。日本時間07:00にEventBridgeからLambdaを実行。S3は非公開・暗号化・バージョニング有効。AWSの利用料は別途発生する。
raw JSONの保存期間・ログ保持期間・障害通知は本番配置時に決める。月次比較は保存済みデータから対象期間を指定して行う。日次ファイルの集計期間が重複するため、そのまま合算しない。

## サイトマップ診断 (PowerShell)

```powershell
$Response = Invoke-WebRequest -Uri 'https://adapt-base.com/sitemap.xml' -MaximumRedirection 5
[xml]$Xml = $Response.Content
[pscustomobject]@{ Status=$Response.StatusCode; ContentType=$Response.Headers['Content-Type']; Root=$Xml.DocumentElement.LocalName; UrlCount=@($Xml.urlset.url).Count }
```

期待値: HTTP 200、XML、root=urlset。取得が403やHTMLの場合、Cloudflareのセキュリティイベントで該当パス・Googleの取得時刻を確認する。未確認のままWAF等を無効化しない。

## 公式参照
- https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart
- https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-resource-function.html
