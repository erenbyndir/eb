"""Single-user local development server with read-only YouTube OAuth."""
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import youtube

ROOT=Path(__file__).resolve().parent/'public'
SESSIONS={}
LOCK=threading.RLock()
SESSION_AGE=8*60*60

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)

    def log_message(self,format,*args):
        # OAuth callback query contains a one-time authorization code; never log it.
        path=urllib.parse.urlsplit(self.path).path
        print(f'{self.command} {path}',flush=True)

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https://i.ytimg.com https://i9.ytimg.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        super().end_headers()

    def json(self,data,status=200):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)

    def session(self,create=False):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except Exception:pass
        sid=cookie.get('creator_session')
        sid=sid.value if sid else ''
        now=time.time()
        with LOCK:
            for key in list(SESSIONS):
                if now-SESSIONS[key]['created']>SESSION_AGE:del SESSIONS[key]
            value=SESSIONS.get(sid)
            if value is None and create:
                sid=secrets.token_urlsafe(32)
                value={'created':now,'cache':{},'lock':threading.RLock()}
                SESSIONS[sid]=value
        return sid,value

    def redirect(self,path,cookie=None):
        self.send_response(302)
        if cookie:self.send_header('Set-Cookie',cookie)
        self.send_header('Location',path)
        self.send_header('Content-Length','0')
        self.end_headers()

    def cookie(self,sid):
        secure=urllib.parse.urlsplit(os.environ.get('YOUTUBE_REDIRECT_URI','')).scheme=='https'
        return f'creator_session={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age={SESSION_AGE}'+('; Secure' if secure else '')

    def access_token(self,session):
        if time.time()>=session.get('expires',0)-60:
            refresh=session.get('refresh_token')
            if not refresh:raise youtube.YouTubeError('Oturumun süresi doldu. Kanalını yeniden bağla.')
            token=youtube.refresh_token(refresh)
            session['access_token']=token['access_token']
            session['expires']=time.time()+token.get('expires_in',3600)
        return session['access_token']

    def do_GET(self):
        parsed=urllib.parse.urlsplit(self.path)
        path=parsed.path
        query=urllib.parse.parse_qs(parsed.query)
        if path=='/api/status':
            _,session=self.session()
            config=youtube.configuration()
            return self.json({**config,'connected':bool(session and session.get('access_token')), 'channel':session.get('channel') if session else None})
        if path=='/auth/start':
            if not youtube.configuration()['configured']:
                return self.json({'error':'Google OAuth ayarları eksik. Bağlantı ayarlarını tamamla.'},503)
            sid,session=self.session(create=True)
            state=secrets.token_urlsafe(32)
            verifier=secrets.token_urlsafe(48)
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            with session['lock']:
                session.update({'oauth_state':state,'verifier':verifier,'oauth_started':time.time()})
            params={'client_id':os.environ['YOUTUBE_CLIENT_ID'],'redirect_uri':os.environ['YOUTUBE_REDIRECT_URI'],
                'response_type':'code','scope':youtube.SCOPES,'state':state,'code_challenge':challenge,'code_challenge_method':'S256',
                'access_type':'offline','prompt':'consent select_account'}
            return self.redirect('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode(params),self.cookie(sid))
        if path=='/auth/callback':
            _,session=self.session()
            state=query.get('state',[''])[0]
            if not session:return self.redirect('/?auth_error='+urllib.parse.quote('Bağlantı oturumu bulunamadı. Tekrar başlat.'))
            with session['lock']:
                expected=session.pop('oauth_state','')
                verifier=session.pop('verifier','')
                if not state or not expected or not secrets.compare_digest(state,expected) or time.time()-session.get('oauth_started',0)>600:
                    return self.redirect('/?auth_error='+urllib.parse.quote('Bağlantı oturumu geçersiz veya süresi dolmuş. Tekrar başlat.'))
                if query.get('error') or not query.get('code'):
                    return self.redirect('/?auth_error='+urllib.parse.quote('Google bağlantısına izin verilmedi. İstersen yeniden deneyebilirsin.'))
                try:
                    token=youtube.exchange_code(query['code'][0],verifier)
                    granted=set(token.get('scope','').split())
                    if not set(youtube.SCOPES.split())<=granted:raise youtube.YouTubeError('Kanal bilgisi ve Analytics için iki okuma izni de gerekli.')
                    channel=youtube.get_channel(token['access_token'])
                    # This workspace is explicitly for @erenbyndir. Avoid silently reading another channel.
                    handle=channel.get('handle','').lower().lstrip('@')
                    if handle!='erenbyndir':raise youtube.YouTubeError('Bu çalışma alanı @erenbyndir içindir. Google izin ekranında bu kanalın hesabını seç.')
                    session.update({'access_token':token['access_token'],'refresh_token':token.get('refresh_token'),
                        'expires':time.time()+token.get('expires_in',3600),'channel':channel,'cache':{}})
                    return self.redirect('/?connected=1')
                except youtube.YouTubeError as error:
                    return self.redirect('/?auth_error='+urllib.parse.quote(str(error)))
                except (KeyError,ValueError):
                    return self.redirect('/?auth_error='+urllib.parse.quote('Google yanıtı tamamlanamadı. Yeniden bağlan.'))
        if path=='/api/analytics':
            _,session=self.session()
            if not session or not session.get('access_token'):return self.json({'error':'Önce YouTube kanalını bağla.'},401)
            try:
                days=int(query.get('days',['28'])[0])
                if days not in (7,28,90):raise ValueError()
            except ValueError:return self.json({'error':'Tarih aralığı 7, 28 veya 90 gün olmalı.'},400)
            with session['lock']:
                cached=session['cache'].get(days)
                # Manual refresh still gets a short cooldown to protect API quota.
                age=30 if 'refresh' in query else 900
                if cached and time.time()-cached['time']<age:return self.json(cached['data'])
                try:
                    data=youtube.fetch_analytics(self.access_token(session),days)
                    session['cache'][days]={'time':time.time(),'data':data}
                    return self.json(data)
                except youtube.YouTubeError as error:return self.json({'error':str(error)},502)
                except (KeyError,ValueError,TypeError):return self.json({'error':'Google raporu beklenen biçimde dönmedi. Yeniden dene.'},502)
        if path.startswith('/api/') or path.startswith('/auth/'):
            return self.json({'error':'Bu işlem bulunamadı.'},404)
        return super().do_GET()

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path!='/api/disconnect':return self.json({'error':'Bu işlem bulunamadı.'},404)
        # Cross-site forms cannot set this header; no CORS access is granted.
        if self.headers.get('X-Creator-Request')!='1':return self.json({'error':'İstek doğrulanamadı.'},403)
        sid,_=self.session()
        with LOCK:SESSIONS.pop(sid,None)
        return self.json({'disconnected':True})

if __name__=='__main__':
    address=(os.environ.get('HOST','127.0.0.1'),int(os.environ.get('PORT','3000')))
    print(f'Creator Studio listening on {address[0]}:{address[1]}',flush=True)
    ThreadingHTTPServer(address,Handler).serve_forever()
