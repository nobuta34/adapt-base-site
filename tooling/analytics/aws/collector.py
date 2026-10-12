"""Lambda: refresh an OAuth token, fetch GA4/GSC reports, save private JSON to S3."""
import datetime as dt
import json
import os
import urllib.parse
import urllib.request


def post(url, payload, token=None, form=False):
    data = urllib.parse.urlencode(payload).encode() if form else json.dumps(payload).encode()
    headers = {'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def collect(token, property_id, site_url, start, end):
    reports = {}
    for name, dimensions, metrics in [
        ('ga4_pages', ['date', 'pagePath'], ['screenPageViews', 'sessions', 'totalUsers']),
        ('ga4_events', ['date', 'eventName'], ['eventCount']),
    ]:
        rows, offset = [], 0
        while True:
            result = post(f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport', {
                'dateRanges': [{'startDate': start, 'endDate': end}],
                'dimensions': [{'name': v} for v in dimensions],
                'metrics': [{'name': v} for v in metrics], 'limit': '10000', 'offset': str(offset)
            }, token)
            batch = result.get('rows', [])
            rows.extend(batch)
            offset += len(batch)
            if not batch or offset >= result.get('rowCount', 0):
                break
        reports[name] = {'rows': rows, 'dimensionHeaders': result.get('dimensionHeaders', []),
                         'metricHeaders': result.get('metricHeaders', []), 'metadata': result.get('metadata', {})}
    rows, offset = [], 0
    while True:
        result = post('https://www.googleapis.com/webmasters/v3/sites/' + urllib.parse.quote(site_url, safe='') + '/searchAnalytics/query', {
            'startDate': start, 'endDate': end, 'dimensions': ['date', 'page'],
            'rowLimit': 25000, 'startRow': offset, 'dataState': 'final'
        }, token)
        batch = result.get('rows', [])
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < 25000:
            break
    reports['search_console_pages'] = {'rows': rows, 'coverage': 'API returns available top rows, not guaranteed exhaustive'}
    return {'startDate': start, 'endDate': end, 'propertyId': property_id, 'siteUrl': site_url, 'reports': reports}


def handler(event, context):
    import boto3
    # No credentials or collected customer data are logged.
    secret = json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=os.environ['OAUTH_SECRET_ARN'])['SecretString'])
    token = post('https://oauth2.googleapis.com/token', {
        'client_id': secret['client_id'], 'client_secret': secret['client_secret'],
        'refresh_token': secret['refresh_token'], 'grant_type': 'refresh_token'
    }, form=True)['access_token']
    now = dt.datetime.now(dt.timezone.utc)
    end = (now.date() - dt.timedelta(days=3)).isoformat()
    start = (now.date() - dt.timedelta(days=10)).isoformat()
    result = collect(token, os.environ['GA4_PROPERTY_ID'], os.environ['GSC_SITE_URL'], start, end)
    key = 'analytics/' + now.strftime('%Y/%m/%d/%H%M%S') + '-' + context.aws_request_id + '.json'
    boto3.client('s3').put_object(Bucket=os.environ['OUTPUT_BUCKET'], Key=key,
        Body=json.dumps(result).encode(), ContentType='application/json', ServerSideEncryption='AES256')
    return {'status': 'saved', 'key': key, 'startDate': start, 'endDate': end}
