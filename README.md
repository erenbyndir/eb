# Creator Studio — @erenbyndir

Türkçe, mobil uyumlu kanal analiz çalışma alanı. Genel bakış, günlük izlenme grafiği, aranabilir/sıralanabilir video kütüphanesi, video detayları, kurala dayalı içerik koçu ve tarayıcıda saklanan içerik planı içerir.

## Başlatma

Python 3.9+ ve testler için Node.js 18+ yeterli. Uygulamanın harici paket bağımlılığı yoktur.

```sh
cd /workspace/eb
python3 server.py
```

Varsayılan geliştirme adresi `127.0.0.1:3000`. `HOST` ve `PORT` isteğe bağlıdır. Bu sunucu kişisel yerel geliştirme içindir. İnternete yayın için HTTPS, özel kullanıcı erişimi, dağıtım ve kalıcı token kasası ayrıca yapılandırılmalıdır; geliştirme sunucusunu tek başına herkese açmayın.

## Gerçek YouTube bağlantısı

OAuth ve YouTube Analytics raporlarını okuma altyapısı uygulanmıştır. **Gerçek Google yetkilendirmesi henüz doğrulanmadı:** OAuth istemcisi bu ortamda mevcut değil. Ana ekrandaki demo etiketli değerler ve videolar tamamen kurgusaldır.

1. [Google Cloud Console](https://console.cloud.google.com/) içinde bir proje oluşturun/seçin.
2. **YouTube Data API v3** ve **YouTube Analytics API** servislerini etkinleştirin.
3. Google Auth Platform bölümünde uygulama bilgilerini ve hedef kitleyi ayarlayın. Testing modunda, @erenbyndir kanalının sahibi olan Google hesabını test kullanıcısı olarak ekleyin.
4. **Web application** türünde bir OAuth client oluşturun.
5. **Authorized redirect URIs** alanına bu uygulamanın erişilebilir adresi + `/auth/callback` ekleyin. Yerel geliştirme örneği `http://localhost:3000/auth/callback`; tarayıcı da `localhost` üzerinden uygulamayı açmalıdır. Bulut ortamındaki `localhost`, kullanıcının bilgisayarından erişilemez; bulut kullanımında uygulamaya ait gerçek HTTPS adresi gerekir. Bu adresin dağıtımı henüz yapılmamıştır.
6. Ortam ayarlarında aşağıdaki değişkenleri ayarlayın; sırları sohbet veya Git deposuna koymayın:
   - `YOUTUBE_CLIENT_ID`: oluşturulan OAuth istemcisinin ID’si.
   - `YOUTUBE_CLIENT_SECRET`: OAuth istemcisinin sırrı; güvenli ortam/secret ayarları üzerinden sağlanmalıdır.
   - `YOUTUBE_REDIRECT_URI`: Google’a kaydedilen callback adresiyle birebir aynı adres.
7. Sunucuyu yeniden başlatın. **YouTube’u bağla** düğmesinden Google izin ekranına geçin ve @erenbyndir kanalını seçin.

Yalnızca `youtube.readonly` ve `yt-analytics.readonly` izinleri istenir. Video oluşturma, düzenleme, silme veya yayımlama yetkisi yoktur. Google şifresi uygulamada toplanmaz. OAuth state ve PKCE doğrulanır. Yetki kodları loglanmaz. Tokenlar tarayıcıya verilmez veya diske yazılmaz; HttpOnly/SameSite oturum cookie’si kullanılır (HTTPS callback varsa Secure). Tokenlar sunucu belleğinde en fazla 8 saat tutulur ve gerektiğinde refresh token ile yenilenir. Sunucu yeniden başlayınca tekrar bağlanmak gerekir. Bağlantıyı kaldırmak bu uygulamadaki tokenları siler; Google’daki yetkiyi iptal etmek için Google hesap izinlerini kullanın.

Gerekli sunucu ağ hedefleri: `oauth2.googleapis.com`, `www.googleapis.com`, `youtubeanalytics.googleapis.com`. Google izin ekranı `accounts.google.com` üzerindedir. Kapaklar `i.ytimg.com` / `i9.ytimg.com` üzerinden tarayıcıya yüklenir.

## Hangi veriler okunuyor?

- Son 7, 28 veya 90 gün için kanal görüntüleme, izlenme saati, net abone ve ortalama izlenme süresi.
- Günlük görüntüleme serisi.
- Seçili dönemde en çok izlenen **ilk 50 video**, başlıkları ve kapakları.
- Panel açık ve görünürken 15 dakikada bir yenileme; ayrıca manuel yenileme. Arka planda zamanlanmış görev yoktur.

Kanal toplamları ilk 50 videodan hesaplanmaz; ayrı kanal raporundan alınır. API verileri gecikmeli gelebilir. Güncel günün eksik verisi yerine raporlama zaman diliminde (YouTube/Pasifik) önceki gün kullanılır. Raporlar 15 dakika önbellekte tutulur; manuel yenilemede 30 saniye kota koruması vardır.

Bu sürüm canlı raporda Shorts ayrımı, gösterim/tıklama oranı, retansiyon grafiği veya trafik kaynaklarını getirmez. Eksik veri uydurulmaz. Format filtresi canlı/CSV raporlarda bu yüzden devre dışıdır. Önceki dönem değişimleri yalnızca demo ekranında açıkça örnek olarak gösterilir. Koç önerileri yerel açık kurallardan üretilir; bir LLM servisine bağlı değildir, başarı tahmini/garantisi değildir. Aynı konudaki toplam izlenmeler, yayın tarihi/format farklarını tek başına açıklamaz.

## CSV alternatifi

Bağlantı ve ayarlar → CSV içe aktar. YouTube Studio → Analytics → Gelişmiş mod → İçerik tablosunu CSV dışa aktarın. ZIP indirilirse önce açın. Video başlığı ve görüntüleme sütunları zorunludur. Türkçe/İngilizce sütun adları, virgül ve noktalı virgül desteklenir. İngilizce virgüllü CSV’de ondalık nokta; Türkçe noktalı virgüllü CSV’de ondalık virgül beklenir. Toplam satırı atlanır. Eksik ölçümler “—” olarak gösterilir. Gösterimler varsa CTR ağırlıklı hesaplanır. Dosya tarayıcıda işlenir, sunucuya gönderilmez veya kalıcı saklanmaz. Günlük serisi olmayan dosyalarda grafik video karşılaştırması yapar. Tarih aralığı ve kanal kimliği dosyadan doğrulanmaz.

İçerik planındaki fikirler bu tarayıcının localStorage alanında saklanır; başka cihazlarla eşitlenmez. Silme/durum değiştirme işlemleri YouTube’a yazmaz.

## Testler

```sh
npm test
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

İsteğe bağlı gerçek tarayıcı kontrolleri (Playwright ve Chromium kuruluysa, sunucu açıkken):

```sh
BROWSER_PATH=/usr/bin/chromium python3 tests/ui_smoke.py
```

Tarayıcı testleri filtreler, video detayları, arama, sıralama, içerik planı kalıcılığı, CSV hataları/XSS, mobil menü ve bağlı kanal arayüzünü kapsar. OAuth/API testleri mock yanıtlar kullanır; canlı Google bağlantısının çalıştığını kanıtlamaz.
