"""Read-only Google OAuth and YouTube reports. Credentials never reach the browser."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SCOPES = 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly'

class YouTubeError(Exception):
    pass

def redirect_uri():
    explicit = os.environ.get('YOUTUBE_REDIRECT_URI', '').strip()
    if explicit:
        return explicit
    # Render injects this server-side; never infer an OAuth URI from a Host header.
    external = os.environ.get('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
    return external + '/auth/callback' if external else ''

def configuration():
    names = ['YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET']
    missing = [name for name in names if not os.environ.get(name)]
    uri = redirect_uri()
    if not uri:
        missing.append('YOUTUBE_REDIRECT_URI')
    parsed = urllib.parse.urlsplit(uri)
    valid_uri = parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'))
    if uri and (not valid_uri or parsed.path != '/auth/callback' or parsed.query or parsed.fragment):
        missing.append('YOUTUBE_REDIRECT_URI (geçerli /auth/callback adresi)')
    return {'configured': not missing, 'missing': missing, 'redirect_uri': uri}

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
        'redirect_uri': redirect_uri(),
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

def upload_ids(token, limit=1000):
    """Discover recent uploads even when Analytics has not processed them yet."""
    url = 'https://www.googleapis.com/youtube/v3/channels?' + urllib.parse.urlencode({'part':'contentDetails','mine':'true'})
    channels = request_json(url, token=token).get('items', [])
    if not channels:
        raise YouTubeError('Kanalın yüklenen içerik listesi okunamadı. Kanalını yeniden bağla.')
    playlist = channels[0].get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
    if not playlist:
        raise YouTubeError('Kanalın yükleme oynatma listesi bulunamadı.')
    ids, page_token = [], None
    seen_pages = set()
    while True:
        params = {'part':'contentDetails','playlistId':playlist,'maxResults':50}
        if page_token:
            params['pageToken'] = page_token
        page = request_json('https://www.googleapis.com/youtube/v3/playlistItems?' + urllib.parse.urlencode(params), token=token)
        for item in page.get('items', []):
            video_id = item.get('contentDetails', {}).get('videoId')
            if video_id and video_id not in ids:
                ids.append(video_id)
        next_token = page.get('nextPageToken')
        if not next_token:
            return ids[:limit], len(ids)>limit
        if len(ids)>=limit:
            return ids[:limit], True
        if next_token in seen_pages:
            raise YouTubeError('Google içerik listesinin sonraki sayfasını okuyamadık. Yeniden dene.')
        seen_pages.add(next_token)
        page_token = next_token

def video_duration(value):
    match = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', value or '')
    if not match:
        return None
    hours, minutes, seconds = (int(n or 0) for n in match.groups())
    total = hours*3600+minutes*60+seconds
    return f'{total//3600}:{total%3600//60:02d}:{total%60:02d}' if total>=3600 else f'{total//60}:{total%60:02d}'

def channel_totals(token):
    url='https://www.googleapis.com/youtube/v3/channels?' + urllib.parse.urlencode({'part':'statistics','mine':'true'})
    items=request_json(url,token=token).get('items',[])
    stats=items[0].get('statistics',{}) if items else {}
    def count(key):
        value=stats.get(key)
        return int(value) if value is not None else None
    return {'views':count('viewCount'),
            'subscribers':None if stats.get('hiddenSubscriberCount') else count('subscriberCount'),
            'videos':count('videoCount')}

def fetch_analytics(token, days):
    start, end = date_range(days)
    metrics = 'views,estimatedMinutesWatched,subscribersGained,subscribersLost,averageViewDuration'
    total = query_report(token,start,end,metrics=metrics)
    daily = query_report(token,start,end,metrics='views',dimensions='day',sort='day')
    rows = query_report(token,start,end,metrics=metrics,dimensions='video',sort='-views',maxResults=50)
    reported = {row['video']:row for row in rows}
    uploads, truncated = upload_ids(token)
    # Keep older reported videos too, but do not hide yesterday's uploads just
    # because they have no Analytics row yet.
    ids = list(dict.fromkeys(uploads + list(reported)))
    metadata = {}
    for offset in range(0, len(ids), 50):
        url='https://www.googleapis.com/youtube/v3/videos?' + urllib.parse.urlencode({'part':'snippet,contentDetails,statistics','id':','.join(ids[offset:offset+50])})
        metadata.update({item['id']:item for item in request_json(url,token=token).get('items',[])})
    videos=[]
    for video_id in ids:
        item = metadata.get(video_id, {})
        snippet=item.get('snippet',{})
        thumbnail=snippet.get('thumbnails',{}).get('medium',{}).get('url')
        if thumbnail and urllib.parse.urlsplit(thumbnail).hostname not in ('i.ytimg.com','i9.ytimg.com'):
            thumbnail=None
        row=reported.get(video_id)
        value=summary(row) if row is not None else {'views':None,'hours':None,'subscribers':None,'avgSeconds':None}
        lifetime=item.get('statistics',{}).get('viewCount')
        videos.append({'id':video_id, 'title':snippet.get('title','Video bilgisi mevcut değil'),
                       'published':snippet.get('publishedAt','')[:10] or 'Yayın tarihi bilinmiyor',
                       'image':thumbnail, 'format':None, 'impressions':None,'ctr':None,
                       'duration':video_duration(item.get('contentDetails',{}).get('duration')),
                       'lifetimeViews':int(lifetime) if lifetime is not None else None,
                       'reportStatus':'available' if row is not None else 'not_reported', **value})
    totals_error=None
    try:
        totals=channel_totals(token)
    except YouTubeError as error:
        totals={'views':None,'subscribers':None,'videos':None}
        totals_error=str(error)
    period_summary=summary(total[0] if total else {})
    if not total and videos:
        period_summary={'views':None,'hours':None,'subscribers':None,'avgSeconds':None}
    return {'start':start,'end':end,'summary':period_summary,
            'summaryAvailable':bool(total), 'channelTotals':totals, 'channelTotalsError':totals_error,
            'latestDailyDate':max((row['day'] for row in daily),default=None),
            'daily':[{'date':row['day'],'views':row['views']} for row in daily], 'videos':videos,
            'libraryTruncated':truncated, 'libraryLimit':1000, 'reportVideoLimit':50}
