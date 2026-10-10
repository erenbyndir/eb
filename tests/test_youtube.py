import os
import unittest
from unittest.mock import patch
import youtube

class ReportsTest(unittest.TestCase):
    def test_summary_converts_watch_minutes_and_net_subscribers(self):
        self.assertEqual(youtube.summary({'views':120,'estimatedMinutesWatched':90,'subscribersGained':5,'subscribersLost':2,'averageViewDuration':45}),{'views':120,'hours':1.5,'subscribers':3,'avgSeconds':45})

    def test_report_maps_video_metadata_and_preserves_missing_metrics(self):
        total={'views':800,'estimatedMinutesWatched':120,'subscribersGained':10,'subscribersLost':3,'averageViewDuration':9}
        with patch.object(youtube,'query_report',side_effect=[[total],[{'day':'2026-10-01','views':800}],[{'video':'abcdefghijk',**total}]]),patch.object(youtube,'request_json',return_value={'items':[{'id':'abcdefghijk','snippet':{'title':'Test video','publishedAt':'2026-10-01T00:00:00Z','thumbnails':{'medium':{'url':'https://i.ytimg.com/test.jpg'}}}}]}):
            result=youtube.fetch_analytics('dummy',28)
        self.assertEqual(result['summary']['hours'],2)
        self.assertEqual(result['videos'][0]['title'],'Test video')
        self.assertIsNone(result['videos'][0]['ctr'])
        self.assertIsNone(result['videos'][0]['format'])
        self.assertEqual(result['daily'][0]['views'],800)

    def test_no_activity_is_a_valid_empty_report(self):
        with patch.object(youtube,'query_report',return_value=[]):
            result=youtube.fetch_analytics('dummy',7)
        self.assertEqual(result['summary']['views'],0)
        self.assertIsNone(result['summary']['avgSeconds'])
        self.assertEqual(result['videos'],[])

    def test_redirect_uri_must_be_https_or_local_callback(self):
        config={'YOUTUBE_CLIENT_ID':'dummy','YOUTUBE_CLIENT_SECRET':'dummy','YOUTUBE_REDIRECT_URI':'http://example.com/auth/callback'}
        with patch.dict(os.environ,config):self.assertFalse(youtube.configuration()['configured'])
        config['YOUTUBE_REDIRECT_URI']='http://localhost:3000/auth/callback'
        with patch.dict(os.environ,config):self.assertTrue(youtube.configuration()['configured'])
        config['YOUTUBE_REDIRECT_URI']='https://example.com/not-callback'
        with patch.dict(os.environ,config):self.assertFalse(youtube.configuration()['configured'])

if __name__=='__main__':unittest.main()
