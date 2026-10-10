import {test} from 'node:test';
import assert from 'node:assert/strict';
import {importVideos,parseCSV,summarize,recommendations} from '../public/analytics.js';
test('Studio export skips total and computes weighted CTR',() => {
  const rows = importVideos('Content,Video title,Views,Watch time (hours),Subscribers,Impressions,Impressions click-through rate (%)\nTotal,,300,12,3,4000,5\na,"A, video",100,4,1,1000,2\nb,B,200,8,2,3000,6');
  assert.equal(rows.length,2); assert.equal(rows[0].title,'A, video');
  assert.deepEqual(summarize(rows),{views:300,hours:12,subscribers:3,ctr:5});
});
test('Turkish semicolon CSV, decimal commas, negative subscribers',() => {
  const rows = importVideos('Video başlığı;Görüntüleme;İzlenme süresi (saat);Aboneler;Gösterimler;Gösterimlerin tıklama oranı (%)\nDeneme;120;2,5;-1;1.000;3,5');
  assert.equal(rows[0].hours,2.5); assert.equal(rows[0].ctr,3.5); assert.equal(rows[0].subscribers,-1);
});
test('missing metrics stay unknown and malformed input fails',() => {
  assert.deepEqual(summarize(importVideos('Video title,Views\nA,0')),{views:0,hours:null,subscribers:null,ctr:null});
  assert.throws(() => importVideos('Video title,Views\nA,nope'));
  assert.throws(() => importVideos('Video title,Views\nA,-1'));
  assert.throws(() => importVideos('Video title,Views\nA,1,2'));
  assert.throws(() => parseCSV('"unfinished'));
});
test('escaped quotes and newlines in titles survive parsing',() => {
  assert.equal(importVideos('Video title,Views\n"A ""title""\nline",100')[0].title,'A "title"\nline');
});
test('CTR recommendation needs sufficient impression evidence',() => {
  const videos = [{title:'A',views:200,impressions:1000,ctr:2},{title:'B',views:300,impressions:2000,ctr:6}];
  assert.equal(recommendations(videos).length,3);
  assert.equal(recommendations(videos.map(v => ({...v,impressions:10}))).length,2);
});
