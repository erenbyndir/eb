export const baseVideos = [
 {id:'demo-1',title:'Sıfırdan başlamak: ilk adımı atıyorum',format:'long',duration:'8:42',published:'Örnek video · 12 gün önce',image:'/assets/start.svg',weight:0.39},
 {id:'demo-2',title:'Bir gün, bir kamera, yeni bir hikâye',format:'long',duration:'6:18',published:'Örnek video · 8 gün önce',image:'/assets/day.svg',weight:0.27},
 {id:'demo-3',title:'Kimse hazır başlamıyor. Sen de başla.',format:'short',duration:'0:38',published:'Örnek Shorts · 5 gün önce',image:'/assets/short.svg',weight:0.22},
 {id:'demo-4',title:'İlk haftamda öğrendiğim 5 şey',format:'long',duration:'5:24',published:'Örnek video · 3 gün önce',image:'/assets/start.svg',weight:0.12},
];
export function demoData(days = 28, format = 'all') {
 const end = new Date(); end.setUTCHours(12,0,0,0); end.setUTCDate(end.getUTCDate()-1);
 const daily = Array.from({length:days},(_,i) => {
  const date = new Date(end); date.setUTCDate(date.getUTCDate() - days + 1 + i);
  const wave = Math.sin(i*1.5)*95 + Math.cos(i*.72)*120;
  return {date:date.toISOString().slice(0,10),views:Math.round((230+i*9+wave+(i>days*.65?160:0))*(format==='all'?1:format==='short'?.22:.78))};
 });
 const total = daily.reduce((s,d)=>s+d.views,0);
 const selected = baseVideos.filter(v => format==='all'||v.format===format);
 const weight = selected.reduce((s,v)=>s+v.weight,0);
 let allocated = 0;
 const videos = selected.map((v,i)=>{
  const views=i===selected.length-1?total-allocated:Math.round(total*v.weight/weight); allocated+=views;
  const avgSeconds=v.format==='short'?27:Math.round(140+i*24);
  return {...v,views,hours:views*avgSeconds/3600,subscribers:Math.round(views/110),avgSeconds,impressions:null,ctr:null};
 });
 const hours=videos.reduce((s,v)=>s+v.hours,0), subscribers=videos.reduce((s,v)=>s+v.subscribers,0);
 return {videos,daily,summary:{views:total,hours,subscribers,avgSeconds:hours*3600/total},start:daily[0].date,end:daily.at(-1).date};
}
