export function parseCSV(text) {
  text = text.replace(/^\uFEFF/, '');
  const first = text.split(/\r?\n/)[0];
  const delimiter = first.split(';').length > first.split(',').length ? ';' : ',';
  const rows = []; let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else if (!quoted && field.length || quoted && text[i + 1] && ![delimiter, '\r', '\n'].includes(text[i + 1])) throw new Error('CSV tırnak biçimi geçersiz.');
      else quoted = !quoted;
    } else if (!quoted && c === delimiter) { row.push(field); field = ''; }
    else if (!quoted && (c === '\n' || c === '\r')) {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); if (row.some(v => v.trim())) rows.push(row);
      row = []; field = '';
    } else field += c;
  }
  if (quoted) throw new Error('CSV içinde kapanmamış tırnak var.');
  row.push(field); if (row.some(v => v.trim())) rows.push(row);
  return {rows, delimiter};
}
const normalize = value => value.trim().toLocaleLowerCase('tr').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ı/g, 'i');
const aliases = {
  title: ['video title', 'video başlığı', 'başlık', 'title'],
  id: ['content', 'içerik', 'video', 'video id'],
  views: ['views', 'görüntüleme', 'görüntülemeler', 'izlenme'],
  hours: ['watch time (hours)', 'izlenme süresi (saat)', 'izleme süresi (saat)'],
  subscribers: ['subscribers', 'aboneler', 'abone'],
  impressions: ['impressions', 'gösterimler', 'gösterim sayısı'],
  ctr: ['impressions click-through rate (%)', 'gösterimlerin tıklama oranı (%)', 'gösterim tıklama oranı (%)', 'ctr (%)'],
};
function number(value, delimiter) {
  if (value === undefined || !value.trim() || value.trim() === '—' || value.trim() === '-') return null;
  let clean = value.trim().replace(/[%\s\u00a0]/g, '');
  if (delimiter === ';' && clean.includes(',')) clean = clean.replace(/\./g, '').replace(',', '.');
  else clean = clean.replace(/,/g, '');
  const n = Number(clean);
  if (!Number.isFinite(n)) throw new Error(`Sayısal değer okunamadı: ${value.slice(0, 40)}`);
  return n;
}
export function importVideos(text) {
  const {rows, delimiter} = parseCSV(text);
  if (rows.length < 2) throw new Error('Dosyada başlık ve en az bir video satırı olmalı.');
  const headers = rows[0].map(normalize);
  const columns = Object.fromEntries(Object.entries(aliases).map(([key, names]) => [key, headers.findIndex(h => names.map(normalize).includes(h))]));
  if (columns.title < 0 || columns.views < 0) throw new Error('Video başlığı ve görüntüleme sütunları gerekli. YouTube Studio’da İçerik tablosunu dışa aktar.');
  const videos = [];
  for (const [index, row] of rows.slice(1).entries()) {
    if (row.length !== headers.length) throw new Error(`CSV satır ${index + 2}: sütun sayısı başlıkla eşleşmiyor.`);
    const title = row[columns.title].trim();
    const id = columns.id < 0 ? '' : row[columns.id].trim();
    if (['total', 'toplam'].includes(normalize(title)) || ['total', 'toplam'].includes(normalize(id))) continue;
    if (!title) continue;
    const video = {title};
    for (const key of ['views', 'hours', 'subscribers', 'impressions', 'ctr']) video[key] = columns[key] < 0 ? null : number(row[columns[key]], delimiter);
    if (video.views === null || video.views < 0 || video.hours < 0 || video.impressions < 0 || video.ctr !== null && (video.ctr < 0 || video.ctr > 100)) throw new Error(`Satır ${index + 2}: görüntüleme veya oran değeri geçersiz.`);
    videos.push(video);
  }
  if (!videos.length) throw new Error('Analiz edilebilecek video satırı bulunamadı.');
  return videos;
}
export function summarize(videos) {
  const sum = key => videos.every(v => v[key] !== null && v[key] !== undefined) ? videos.reduce((s, v) => s + v[key], 0) : null;
  const impressions = sum('impressions');
  const ctr = impressions > 0 && videos.every(v => v.ctr != null) ? videos.reduce((s, v) => s + v.impressions * v.ctr, 0) / impressions : null;
  return {views: sum('views'), hours: sum('hours'), subscribers: sum('subscribers'), ctr};
}
export function recommendations(videos) {
  const sorted = [...videos].sort((a, b) => b.views - a.views);
  const result = [];
  if (sorted[0]?.views >= 100) result.push({label: 'Konu denemesi', title: 'En çok izlenen konuyu yeniden dene', detail: `“${sorted[0].title}” bu tablodaki en çok izlenen video. Benzer bir konuyu farklı bir açıyla dene. Yayın tarihi ve trafik kaynağı bilinmediği için bunu kesin başarı göstergesi sayma.`});
  const candidates = videos.filter(v => v.impressions >= 1000 && v.ctr != null);
  if (candidates.length >= 2) {
    const low = [...candidates].sort((a, b) => a.ctr - b.ctr)[0];
    const high = Math.max(...candidates.map(v => v.ctr));
    if (high - low.ctr >= 2) result.push({label: 'Başlık ve kapak', title: 'Tıklama oranı farkını incele', detail: `“${low.title}” için oran %${low.ctr.toLocaleString('tr-TR')}. En az 1.000 gösterimli videolarında daha yüksek oranlar var. Trafik kaynaklarını karşılaştırıp başlık veya kapakta tek bir değişikliği test et. Shorts akışı için bu ölçümü kullanma.`});
  }
  result.push({label: 'Sonraki adım', title: 'Karşılaştırma dönemini sabit tut', detail: 'Her hafta aynı tarih aralığındaki verileri dışa aktar. Shorts ve uzun videoları ayrı değerlendir. İzleyici tutma grafiğini Studio’da kontrol et; bu CSV analizi o grafiği içermez.'});
  return result;
}
