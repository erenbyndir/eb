import io
import hashlib
import base64
import http.cookiejar
import json
import os
import threading
import time
import unittest
import urllib.request
import urllib.parse
import urllib.error
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import server
import youtube

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.httpd.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join()
    def setUp(self):
        server.SESSIONS.clear()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),NoRedirect())
    def get(self,path):
        try:response=self.opener.open(self.base+path)
        except urllib.error.HTTPError as e:response=e
        result=io.BytesIO(response.read());result.code=response.code;result.headers=response.headers;response.close();return result
    def test_missing_config_and_disconnected_request_are_explicit(self):
        with patch.dict(os.environ,{'YOUTUBE_CLIENT_ID':'','YOUTUBE_CLIENT_SECRET':'','YOUTUBE_REDIRECT_URI':''}):
            self.assertFalse(json.load(self.get('/api/status'))['configured'])
            self.assertEqual(self.get('/auth/start').code,503)
        self.assertEqual(self.get('/api/analytics').code,401)
    def test_oauth_pkce_callback_and_cache(self):
        config={'YOUTUBE_CLIENT_ID':'test-id','YOUTUBE_CLIENT_SECRET':'test-secret','YOUTUBE_REDIRECT_URI':self.base+'/auth/callback'}
        with patch.dict(os.environ,config):
            response=self.get('/auth/start');self.assertEqual(response.code,302)
            params=urllib.parse.parse_qs(urllib.parse.urlsplit(response.headers['Location']).query)
            self.assertEqual(params['code_challenge_method'],['S256'])
            self.assertEqual(set(params['scope'][0].split()),set(youtube.SCOPES.split()))
            session=next(iter(server.SESSIONS.values()))
            self.assertEqual(params['code_challenge'][0],base64.urlsafe_b64encode(hashlib.sha256(session['verifier'].encode()).digest()).decode().rstrip('='))
            token={'access_token':'dummy','refresh_token':'refresh','expires_in':3600,'scope':youtube.SCOPES}
            with patch.object(youtube,'exchange_code',return_value=token),patch.object(youtube,'get_channel',return_value={'id':'UCdummy','title':'Eren','handle':'@erenbyndir'}):
                callback=self.get('/auth/callback?'+urllib.parse.urlencode({'state':params['state'][0],'code':'dummy-code'}))
                self.assertEqual(callback.headers['Location'],'/?connected=1')
            self.assertTrue(json.load(self.get('/api/status'))['connected'])
            self.assertEqual(self.get('/api/analytics?days=999').code,400)
            with patch.object(youtube,'fetch_analytics',return_value={'videos':[]}) as fetch:
                self.assertEqual(json.load(self.get('/api/analytics?days=28')),{'videos':[]})
                self.get('/api/analytics?days=28');self.assertEqual(fetch.call_count,1)
            # Callback cannot be replayed.
            self.assertIn('auth_error',self.get('/auth/callback?'+urllib.parse.urlencode({'state':params['state'][0],'code':'dummy-code'})).headers['Location'])
            request=urllib.request.Request(self.base+'/api/disconnect',data=b'')
            with self.assertRaises(urllib.error.HTTPError) as denied:self.opener.open(request)
            self.assertEqual(denied.exception.code,403)
            denied.exception.close()
            request.add_header('X-Creator-Request','1')
            with self.opener.open(request) as response:self.assertTrue(json.load(response)['disconnected'])
            self.assertFalse(json.load(self.get('/api/status'))['connected'])
    def test_hosted_https_callback_sets_secure_cookie_and_health(self):
        config={'YOUTUBE_CLIENT_ID':'test-id','YOUTUBE_CLIENT_SECRET':'test-secret','YOUTUBE_REDIRECT_URI':'','RENDER_EXTERNAL_URL':'https://example.onrender.com'}
        with patch.dict(os.environ,config):
            response=self.get('/auth/start')
            self.assertIn('; Secure',response.headers['Set-Cookie'])
            params=urllib.parse.parse_qs(urllib.parse.urlsplit(response.headers['Location']).query)
            self.assertEqual(params['redirect_uri'],['https://example.onrender.com/auth/callback'])
        self.assertEqual(json.load(self.get('/health')),{'ok':True})

    def test_wrong_oauth_state_does_not_exchange_code(self):
        config={'YOUTUBE_CLIENT_ID':'x','YOUTUBE_CLIENT_SECRET':'x','YOUTUBE_REDIRECT_URI':self.base+'/auth/callback'}
        with patch.dict(os.environ,config):
            self.get('/auth/start')
            with patch.object(youtube,'exchange_code') as exchange:
                self.assertIn('auth_error',self.get('/auth/callback?state=wrong&code=wrong').headers['Location'])
                exchange.assert_not_called()
    def test_server_source_is_not_served(self):
        self.assertEqual(self.get('/server.py').code,404)
        self.assertEqual(self.get('/youtube.py').code,404)
        response=self.get('/')
        self.assertEqual(response.code,200)
        self.assertIn('frame-ancestors',response.headers['Content-Security-Policy'])

if __name__=='__main__':unittest.main()
