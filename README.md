# Creator Studio — @erenbyndir

Türkçe, mobil uyumlu kanal analiz çalışma alanı. Genel bakış, günlük izlenme grafiği, aranabilir/sıralanabilir video kütüphanesi, video detayları, kurala dayalı içerik koçu ve tarayıcıda saklanan içerik planı içerir.

## Tarayıcıdan kullanım — Render

[Render üzerinde kur](https://render.com/deploy?repo=https://github.com/erenbyndir/eb)

Bu bağlantı bir **kurulum ekranıdır**, çalışan uygulama adresi değildir. Render hesabı ve GitHub deposuna erişim gerekir. `render.yaml` hazırdır; Python kurulumu veya dosya indirme gerekmez.

1. Bağlantıyı açın ve GitHub hesabınızla giriş yapın. Render GitHub erişimi isterse `erenbyndir/eb` deposuna izin verin.
2. İstenen `YOUTUBE_CLIENT_ID` ve `YOUTUBE_CLIENT_SECRET` alanlarına oluşturduğunuz Google OAuth istemcisinin bilgilerini girin. Client secret yalnızca Render’ın güvenli ayarına girilmelidir, sohbete veya GitHub’a yazılmamalıdır.
3. Blueprint’i **Deploy / Apply** ile başlatın. Bu sağlayıcı işlemidir; bu sohbet tarafından başlatılmış veya doğrulanmış değildir.
4. Render uygulamanız için gerçek bir HTTPS adresi verir. Panelde **Bağlantı ve ayarlar** ekranındaki geri dönüş adresini kopyalayın. Google Auth Platform → Clients → istemciniz → Authorized redirect URIs alanına ekleyip Save yapın.
5. Panelde **YouTube’u bağla** ile kanalınızın hesabına okuma izni verin.

HTTPS adresi Render’ın `RENDER_EXTERNAL_URL` değişkeninden belirlenir; `YOUTUBE_REDIRECT_URI` girmeniz gerekmez. Bir özel alan adı kullanırsanız bu değişkeni açıkça tanımlayın. Varsayılan `free` plan seçilidir; sağlayıcının güncel uygunluk/limit ve fiyat bilgileri kendi ekranında geçerlidir. Ücretsiz servis uyursa veya yeniden başlarsa Google’a yeniden bağlanmanız gerekir: tokenlar diske kaydedilmez. Yalnızca kişisel kullanım için tek sunucu örneğiyle çalıştırın. Otomatik GitHub deploy kapalıdır; test edilen değişiklikleri Render’dan elle deploy edebilirsiniz.

Blueprint ve barındırılan adres tespiti yerel testlerle doğrulanmıştır; gerçek Render deploy’u ve gerçek Google yetkilendirmesi kullanıcı hesabı/ayarları olmadan doğrulanmamıştır.

## Başlatma

Python 3.9+ ve testler için Node.js 18+ yeterli. Uygulamanın harici paket bağımlılığı yoktur.

```sh
cd /workspace/eb
python3 server.py
```

Varsayılan geliştirme adresi `127.0.0.1:3000`. `HOST` ve `PORT` isteğe bağlıdır. Yerelde yalnızca loopback üzerinden açılır. Render yapılandırması servis portunu açar ve sağlayıcı HTTPS sağlar. Arayüzün demo bölümü herkese açıktır; kanal verileri HttpOnly oturum cookie’sine ve @erenbyndir hesabının Google okuma iznine bağlıdır. Tokenlar yalnızca bellektedir; çok sunuculu kullanım ve kalıcı arka plan raporlaması için ayrıca paylaşılan güvenli oturum/token saklama gerekir.

## Windows’ta kişisel kullanım

GitHub → Code → Download ZIP, ardından Tümünü Ayıkla. `run_local.py` bulunan klasörü açın. Dosya Gezgini adres çubuğuna `cmd` yazıp Enter’a basın. Açılan pencerede:

```bat
py -3 run_local.py
```

Başlatıcı OAuth bilgilerini terminalde sorar; Client secret yazılırken görünmez. Bilgiler dosyaya kaydedilmez. Tarayıcıda `http://localhost:3000` adresini açın. Google’daki yetkili yönlendirme adresi `http://localhost:3000/auth/callback` olmalıdır.

`BASLAT.bat` isteğe bağlı bir kolaylık dosyasıdır. Windows Akıllı Uygulama Denetimi imzasız/indirilen dosyayı engellerse korumayı kapatmayın. Python’u resmi kaynaktan kurun ve yukarıdaki komutu kullanın. Python’un kendisi de engelleniyorsa uyarıdaki dosya adını kontrol edin; korumayı devre dışı bırakmayın.

## Gerçek YouTube bağlantısı

OAuth ve YouTube Analytics raporlarını okuma altyapısı uygulanmıştır. **Gerçek Google yetkilendirmesi henüz doğrulanmadı:** OAuth istemcisi bu ortamda mevcut değil. Ana ekrandaki demo etiketli değerler ve videolar tamamen kurgusaldır.

1. [Google Cloud Console](https://console.cloud.google.com/) içinde bir proje oluşturun/seçin.
2. **YouTube Data API v3** ve **YouTube Analytics API** servislerini etkinleştirin.
3. Google Auth Platform bölümünde uygulama bilgilerini ve hedef kitleyi ayarlayın. Testing modunda, @erenbyndir kanalının sahibi olan Google hesabını test kullanıcısı olarak ekleyin.
4. **Web application** türünde bir OAuth client oluşturun.
5. **Authorized redirect URIs** alanına bu uygulamanın erişilebilir adresi + `/auth/callback` ekleyin. Yerel geliştirme örneği `http://localhost:3000/auth/callback`; tarayıcı da `localhost` üzerinden uygulamayı açmalıdır. Bulut ortamındaki `localhost`, kullanıcının bilgisayarından erişilemez; bulut kullanımında uygulamaya ait gerçek HTTPS adresi gerekir. Render kurulum adımlarını üstte bulabilirsiniz.
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
- Kanalın yükleme oynatma listesinden **en yeni 1.000 video**, başlıkları, kapakları ve süreleri (sayfalar takip edilir).
- Seçili dönemde en çok izlenen **ilk 50 video** için Analytics ölçümleri. Bu listenin dışındaki/henüz raporlanmayan videolar da kütüphanede görünür; dönem ölçümleri “—” olur. Video detayında Data API’nin tüm zamanlar görüntüleme sayısı ayrı etiketlenir.
- Kütüphane sınırına ulaşılırsa açıkça bildirilir; yükleme listesinin dışındaki raporlanan videolar da eklenir.
- Panel açık ve görünürken 15 dakikada bir yenileme; ayrıca manuel yenileme. Arka planda zamanlanmış görev yoktur.

Kanal toplamları video listesinden hesaplanmaz; ayrı kanal raporundan alınır. Yeni yüklemeler YouTube Data API’den listelenir; Analytics raporu gecikmesi videoyu kütüphaneden gizlemez. Dönem raporu olmayan videoda sıfır izlenme varsayılmaz. API verileri gecikmeli gelebilir. Güncel günün eksik verisi yerine raporlama zaman diliminde (YouTube/Pasifik) önceki gün kullanılır. Raporlar 15 dakika önbellekte tutulur; manuel yenilemede 30 saniye kota koruması vardır.

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
