import os
import unittest
from unittest.mock import patch
import youtube

class ReportsTest(unittest.TestCase):
    def test_summary_converts_watch_minutes_and_net_subscribers(self):
        self.assertEqual(youtube.summary({'views':120,'estimatedMinutesWatched':90,'subscribersGained':5,'subscribersLost':2,'averageViewDuration':45}),{'views':120,'hours':1.5,'subscribers':3,'avgSeconds':45})

    def test_report_maps_video_metadata_and_preserves_missing_metrics(self):
        total={'views':800,'estimatedMinutesWatched':120,'subscribersGained':10,'subscribersLost':3,'averageViewDuration':9}
        with patch.object(youtube,'upload_ids',return_value=(['abcdefghijk'],False)),patch.object(youtube,'query_report',side_effect=[[total],[{'day':'2026-10-01','views':800}],[{'video':'abcdefghijk',**total}]]),patch.object(youtube,'request_json',return_value={'items':[{'id':'abcdefghijk','snippet':{'title':'Test video','publishedAt':'2026-10-01T00:00:00Z','thumbnails':{'medium':{'url':'https://i.ytimg.com/test.jpg'}}}}]}):
            result=youtube.fetch_analytics('dummy',28)
        self.assertEqual(result['summary']['hours'],2)
        self.assertEqual(result['videos'][0]['title'],'Test video')
        self.assertIsNone(result['videos'][0]['ctr'])
        self.assertIsNone(result['videos'][0]['format'])
        self.assertEqual(result['daily'][0]['views'],800)

    def test_no_activity_is_a_valid_empty_report(self):
        with patch.object(youtube,'upload_ids',return_value=([],False)),patch.object(youtube,'query_report',return_value=[]):
            result=youtube.fetch_analytics('dummy',7)
        self.assertEqual(result['summary']['views'],0)
        self.assertIsNone(result['summary']['avgSeconds'])
        self.assertEqual(result['videos'],[])

    def test_new_upload_is_present_without_analytics_and_not_zeroed(self):
        total={'views':923,'estimatedMinutesWatched':126,'subscribersGained':5,'subscribersLost':0,'averageViewDuration':23}
        metadata={'items':[
            {'id':'oldvideo001','snippet':{'title':'Old video','publishedAt':'2026-10-05T12:00:00Z'}},
            {'id':'newvideo001','snippet':{'title':'Yesterday upload','publishedAt':'2026-10-09T12:00:00Z'},'contentDetails':{'duration':'PT45S'},'statistics':{'viewCount':'12'}}]}
        with patch.object(youtube,'upload_ids',return_value=(['newvideo001','oldvideo001'],False)),patch.object(youtube,'query_report',side_effect=[[total],[],[{'video':'oldvideo001',**total}]]),patch.object(youtube,'request_json',return_value=metadata):
            result=youtube.fetch_analytics('dummy',28)
        self.assertEqual(len(result['videos']),2)
        new=result['videos'][0]
        self.assertEqual(new['title'],'Yesterday upload')
        self.assertEqual(new['lifetimeViews'],12)
        self.assertEqual(new['duration'],'0:45')
        self.assertIsNone(new['views'])
        self.assertIsNone(new['hours'])
        self.assertIsNone(new['subscribers'])
        self.assertEqual(new['reportStatus'],'not_reported')
        self.assertEqual(result['summary']['views'],923)

    def test_upload_list_reads_next_page_and_deduplicates(self):
        replies=[{'items':[{'contentDetails':{'relatedPlaylists':{'uploads':'UPLOADS'}}}]},
                 {'items':[{'contentDetails':{'videoId':'A'}}], 'nextPageToken':'PAGE2'},
                 {'items':[{'contentDetails':{'videoId':'A'}},{'contentDetails':{'videoId':'B'}}]}]
        with patch.object(youtube,'request_json',side_effect=replies) as request:
            self.assertEqual(youtube.upload_ids('dummy'),(['A','B'],False))
            self.assertIn('pageToken=PAGE2',request.call_args[0][0])

    def test_upload_list_limit_is_reported(self):
        replies=[{'items':[{'contentDetails':{'relatedPlaylists':{'uploads':'UPLOADS'}}}]},
                 {'items':[{'contentDetails':{'videoId':'A'}}], 'nextPageToken':'PAGE2'}]
        with patch.object(youtube,'request_json',side_effect=replies):
            self.assertEqual(youtube.upload_ids('dummy',limit=1),(['A'],True))

    def test_duration_does_not_assume_short_format(self):
        self.assertEqual(youtube.video_duration('PT1H2M3S'),'1:02:03')
        self.assertEqual(youtube.video_duration('PT2M'),'2:00')
        self.assertIsNone(youtube.video_duration(None))

    def test_hosted_redirect_uses_render_url_with_explicit_override(self):
        config={'YOUTUBE_CLIENT_ID':'dummy','YOUTUBE_CLIENT_SECRET':'dummy','YOUTUBE_REDIRECT_URI':'','RENDER_EXTERNAL_URL':'https://example.onrender.com/'}
        with patch.dict(os.environ,config):
            self.assertEqual(youtube.redirect_uri(),'https://example.onrender.com/auth/callback')
            self.assertTrue(youtube.configuration()['configured'])
        config['YOUTUBE_REDIRECT_URI']='https://custom.example.com/auth/callback'
        with patch.dict(os.environ,config):
            self.assertEqual(youtube.redirect_uri(),config['YOUTUBE_REDIRECT_URI'])
        config['YOUTUBE_REDIRECT_URI']=''
        config['RENDER_EXTERNAL_URL']='http://unsafe.example.com'
        with patch.dict(os.environ,config):
            self.assertFalse(youtube.configuration()['configured'])

    def test_redirect_uri_must_be_https_or_local_callback(self):
        config={'YOUTUBE_CLIENT_ID':'dummy','YOUTUBE_CLIENT_SECRET':'dummy','YOUTUBE_REDIRECT_URI':'http://example.com/auth/callback'}
        with patch.dict(os.environ,config):self.assertFalse(youtube.configuration()['configured'])
        config['YOUTUBE_REDIRECT_URI']='http://localhost:3000/auth/callback'
        with patch.dict(os.environ,config):self.assertTrue(youtube.configuration()['configured'])
        config['YOUTUBE_REDIRECT_URI']='https://example.com/not-callback'
        with patch.dict(os.environ,config):self.assertFalse(youtube.configuration()['configured'])

if __name__=='__main__':unittest.main()
