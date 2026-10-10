"""Read-only Google OAuth and YouTube reports. Credentials never reach the browser."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SCOPES = 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly'

class YouTubeError(Exception):
    pass

def configuration():
    names = ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET', 'YOUTUBE_REDIRECT_URI']
    missing = [name for name in names if not os.environ.get(name)]
    uri = os.environ.get('YOUTUBE_REDIRECT_URI', '')
    parsed = urllib.parse.urlsplit(uri)
    valid_uri = parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'))
    if uri and (not valid_uri or parsed.path != '/auth/callback' or parsed.query or parsed.fragment):
        missing.append('YOUTUBE_REDIRECT_URI (geçerli /auth/callback adresi)')
    return {'configured': not missing, 'missing': missing}

def request_json(url, *, token=None, form=None):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not expose request bodies, credentials, tokens or provider diagnostics.
        code = error.code
        if code == 401:
            raise YouTubeError('YouTube yetkisi geçersiz veya süresi dolmuş. Kanalını yeniden bağla.') from None
        if code == 403:
            raise YouTubeError('Google erişimi reddetti. İki YouTube API’sinin etkin olduğunu, izinleri ve API kotasını kontrol et.') from None
        if code == 400:
            raise YouTubeError('Google isteği kabul etmedi. OAuth yönlendirme adresini, istemci ayarlarını ve izinleri kontrol et.') from None
        raise YouTubeError(f'Google servisi şu anda isteği tamamlayamadı (HTTP {code}).') from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise YouTubeError('Google servisine erişilemedi. Ağ bağlantısını kontrol edip tekrar dene.') from None

def exchange_code(code, verifier):
    return request_json('https://oauth2.googleapis.com/token', form={
        'client_id': os.environ['YOUTUBE_CLIENT_ID'],
        'client_secret': os.environ['YOUTUBE_CLIENT_SECRET'],
        'redirect_uri': os.environ['YOUTUBE_REDIRECT_URI'],
        'code': code, 'code_verifier': verifier, 'grant_type': 'authorization_code',
    })

def refresh_token(refresh):
    return request_json('https://oauth2.googleapis.com/token', form={
        'client_id': os.environ['YOUTUBE_CLIENT_ID'],
        'client_secret': os.environ['YOUTUBE_CLIENT_SECRET'],
        'refresh_token': refresh, 'grant_type': 'refresh_token',
    })

def get_channel(token):
    url = 'https://www.googleapis.com/youtube/v3/channels?' + urllib.parse.urlencode({'part':'snippet', 'mine':'true'})
    channels = request_json(url, token=token).get('items', [])
    if not channels:
        raise YouTubeError('Bu Google hesabında erişilebilir YouTube kanalı bulunamadı. Kanalının sahibi olan hesabı seç.')
    channel = channels[0]
    return {'id':channel['id'], 'title':channel['snippet']['title'], 'handle':channel['snippet'].get('customUrl', '')}

def date_range(days):
    # Analytics reporting dates follow YouTube's Pacific reporting timezone; end
    # yesterday to avoid claiming incomplete current-day figures are complete.
    from zoneinfo import ZoneInfo
    end = datetime.now(ZoneInfo('America/Los_Angeles')).date() - timedelta(days=1)
    start = end - timedelta(days=days-1)
    return start.isoformat(), end.isoformat()

def query_report(token, start, end, **kwargs):
    params = {'ids':'channel==MINE','startDate':start,'endDate':end, **kwargs}
    url = 'https://youtubeanalytics.googleapis.com/v2/reports?' + urllib.parse.urlencode(params)
    report = request_json(url, token=token)
    headers = [h['name'] for h in report.get('columnHeaders', [])]
    return [dict(zip(headers,row)) for row in report.get('rows', [])]

def summary(row):
    return {'views':row.get('views',0),'hours':row.get('estimatedMinutesWatched',0)/60,
            'subscribers':row.get('subscribersGained',0)-row.get('subscribersLost',0),
            'avgSeconds':row.get('averageViewDuration')}

def fetch_analytics(token, days):
    start, end = date_range(days)
    metrics = 'views,estimatedMinutesWatched,subscribersGained,subscribersLost,averageViewDuration'
    total = query_report(token,start,end,metrics=metrics)
    daily = query_report(token,start,end,metrics='views',dimensions='day',sort='day')
    rows = query_report(token,start,end,metrics=metrics,dimensions='video',sort='-views',maxResults=50)
    ids = [r['video'] for r in rows]
    metadata = {}
    if ids:
        url='https://www.googleapis.com/youtube/v3/videos?' + urllib.parse.urlencode({'part':'snippet,contentDetails','id':','.join(ids)})
        metadata = {item['id']:item for item in request_json(url,token=token).get('items',[])}
    videos=[]
    for row in rows:
        item = metadata.get(row['video'], {})
        snippet=item.get('snippet',{})
        thumbnail=snippet.get('thumbnails',{}).get('medium',{}).get('url')
        # Only Google's thumbnail host is allowed as an external image source.
        if thumbnail and urllib.parse.urlsplit(thumbnail).hostname not in ('i.ytimg.com','i9.ytimg.com'):
            thumbnail=None
        value=summary(row)
        videos.append({'id':row['video'], 'title':snippet.get('title','Video bilgisi mevcut değil'),
                       'published':snippet.get('publishedAt','')[:10] or 'Yayın tarihi bilinmiyor',
                       'image':thumbnail, 'format':None, 'impressions':None,'ctr':None, **value})
    return {'start':start,'end':end,'summary':summary(total[0] if total else {}),
            'daily':[{'date':row['day'],'views':row['views']} for row in daily], 'videos':videos}
