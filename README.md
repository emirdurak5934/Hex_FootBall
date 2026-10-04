# FootballDatabase V2

Bu klasör, orijinal `FootballDatabase` projesine dokunulmadan hazırlanmış düzenlenmiş kopyadır.

Projenin yaşayan mimari ve geliştirme haritası `PROJECT_WORKFLOW.md` dosyasındadır. Görsel sürüm `PROJECT_WORKFLOW.png`, düzenlenebilir kaynak ise `PROJECT_WORKFLOW.svg` olarak açılabilir. Yeni özellik veya modül tamamlandığında bu dosyalar da güncellenmelidir.

Possession ve Tiki Taka Toe çevrimiçi modlarında oda koduna ek olarak giriş yapmış kullanıcılar için rastgele rakip eşleştirme bulunur. Çevrimiçi maç ekranlarında oyuncular hesap adlarıyla gösterilir.

Çevrimiçi maç sırasında verilen futbolcu cevabı iki oyuncunun ekranında 2 saniye gösterilir. Possession oyununda yalnızca futbolcunun adı, cevap verilen peteğin sınırlarından taşmayacak şekilde görünür.
Possession cevap bilgisi hem anlık Socket.IO olayıyla hem de paylaşılan oyun durumuyla iletilir; böylece iki oyuncu da bildirimi alır.

Tiki Taka Toe'da üç satır kulübü yalnızca A sınıfı havuzdan seçilir:
Arsenal, Liverpool, Manchester United, Manchester City, Chelsea, Barcelona,
Real Madrid, Juventus, Paris Saint-Germain ve Bayern Munich. Sütunlar soldan
sağa daima bir kulüp, bir ülke/milliyet ve bir kupa kriteridir. Sütundaki kulüp
25 takımlık havuzdan seçilir; Newcastle United ve AS Monaco bu oyunun kulüp
kriteri havuzuna dahil değildir.
Tahtanın satır ve sütun kriter kutularında isim/tür yazısı yerine mevcut kulüp
armaları, ülke bayrakları ve kupa simgeleri gösterilir. Kriter adı erişilebilirlik
etiketinde ve futbolcu arama penceresinde korunur.

## 21 Eylül 2026 çalışma günlüğü

- Tiki Taka Toe'nun üç satır kulübü 10 A sınıfı takımla sınırlandı; sütun
  kriterleri değiştirilmedi.
- 100 rastgele tahta testinde yeni satır kuralı, tahta üretimi ve cevapsız
  hücre kontrolleri başarıyla doğrulandı.
- Sütun düzeni sabitlendi: solda bir kulüp, ortada bir milliyet/ülke, sağda
  bir kupa. İki kulüplü sütun düzenleri kaldırıldı.
- Tiki Taka Toe kriter kutularındaki kulüp, ülke ve kupa yazıları mevcut logo,
  bayrak ve kupa görselleriyle değiştirildi; 52 görsel eşleşmesi doğrulandı.
- Tiki Taka Toe kulüp havuzundan Newcastle United ve AS Monaco çıkarıldı;
  sütun kulübü için 25 takım kaldı. Satırdaki 10 A sınıfı takım değişmedi.

## Maç sonu reklam modülü

Maç sonu reklam politikası, Capacitor/AdMob köprüsü ve tarayıcı denetleyicisi
`ads.py` içinde tutulur. Tamamlanan Possession, Tiki Taka Toe, Isı Haritası ve
Missing 11 maçları reklam için uygun; pes etme ve bağlantı kopmasıyla biten
maçlar uygun değildir. Reklam sağlayıcısı en fazla 5 saniye içinde yanıt
vermezse sonuç ekranı reklamsız açılır.

iOS kabuğu `@capacitor-community/admob` kullanır. Varsayılan `test` modu
Google'ın iOS demo interstitial kimliğini kullanır; geliştirme sırasında canlı
reklama istek atılmaz. GitHub Actions, `ADMOB_IOS_APP_ID` repository secret'ı
yoksa Google'ın demo App ID'siyle test IPA'sı üretir.

Yapılandırma ortam değişkenleri:

- `FOOTBALL_ADS_ENABLED=1`
- `FOOTBALL_AD_MODE=test` (varsayılan) veya `live`
- `FOOTBALL_AD_UNIT_PATH` (live sunucuda interstitial kimliği)
- `FOOTBALL_AD_TIMEOUT_MS` (varsayılan ve üst sınır: `5000`)

Canlı modda `FOOTBALL_AD_UNIT_PATH` verilmezse yerel ve Git tarafından yok
sayılan `reklam_kimligi.txt` içindeki geçiş reklamı kimliği okunur. App Store
paketi için GitHub deposunda `ADMOB_IOS_APP_ID` secret'ı tanımlanmalı ve
sunucu `FOOTBALL_ADS_ENABLED=1`, `FOOTBALL_AD_MODE=live` ile başlatılmalıdır. UMP gizlilik mesajı AdMob
panelinden yayımlanmadan canlı moda geçilmemelidir.

## Klasör yapısı

- `app.py`, `run.py` ve kökteki diğer Python modülleri: çalışan Flask uygulaması
- `templates/`: Jinja sayfaları
- `static/`: CSS, JavaScript ve uygulamada kullanılan görseller
- `data/`: futbolcu ve oyun verileri ile bakım raporları
- `instance/`: SQLite kullanıcı/profil veritabanı
- `tests/`: uygulama ve oyun testleri
- `tools/maintenance/root_scripts/`: veri toplama, zenginleştirme ve eski bakım scriptleri
- `tools/maintenance/cleanup/`: ortak veri temizleme araçları
- `tools/maintenance/assets/`: uygulamanın doğrudan kullanmadığı eski indirme çıktıları
- `legacy/`: eski Streamlit sürümü ve referans dosyaları

## Kurulum

PowerShell içinde:

```powershell
cd C:\Users\Emir\Desktop\FootballDatabase_v2
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Çalıştırma

```powershell
.\.venv\Scripts\python.exe run.py
```

`run.py` geriye dönük uyumluluk içindir. Yeni sunucu modülünün doğrudan kullanımı:

```powershell
# Yerel/ağ sunucusu
.\.venv\Scripts\python.exe -m server serve

# Sunucu + Cloudflare Quick Tunnel
.\.venv\Scripts\python.exe -m server public
```

Komut ezberlemeden başlatmak için proje kökündeki `server_olusturucu.py`
dosyasına çift tıklanabilir veya terminalden aşağıdaki komut çalıştırılabilir:

```powershell
.\.venv\Scripts\python.exe .\server_olusturucu.py
```

Menü; aynı Wi-Fi, internet üzerinden Cloudflare yayını, yalnız tünel ve sistem
kontrolü seçeneklerini sunar. Sunucuyu kapatmak için `Ctrl+C` kullanılır.
Çift tıklamayla başlatılan menü hata veya kapanma sonrasında pencereyi açık
tutar; public adres terminalde `TELEFONDAN AÇILACAK SUNUCU ADRESİ` başlığıyla gösterilir.
Başlatıcı her açılışta aktif yerel adresi ve çalışan tünelin public adresini
gösterir. Tünel bilgisi PID ile doğrulanan `instance/active_tunnel.json` dosyasında tutulur.

Tünel ve sunucu ayarlarının ayrıntıları `server/README.md` dosyasındadır. Tünel sağlayıcısı bir adaptördür; ileride Cloudflare yerine başka bir sağlayıcıya geçişte oyun modüllerinin değiştirilmesi gerekmez.

Uygulama varsayılan olarak `0.0.0.0:5000` üzerinde dinler; bu sayede aynı yerel ağdaki telefonlardan bilgisayarın IPv4 adresiyle erişilebilir. Bilgisayarda `http://127.0.0.1:5000`, telefonda ise örneğin `http://192.168.1.25:5000` kullanılır.

Dinleme adresi ve port gerekirse ortam değişkenleriyle değiştirilebilir:

```powershell
$env:FOOTBALL_MATCH_HOST="127.0.0.1"
$env:FOOTBALL_MATCH_PORT="5000"
```

Debug modu için çalıştırmadan önce `FLASK_DEBUG=1` ortam değişkeni verilebilir.

## Yol davranışı

Uygulamanın ana veri yolları `app.py` dosyasının konumundan `os.path` ile hesaplanır.

`tools/maintenance` altındaki her script kendi `__file__` konumundan V2 proje kökünü hesaplar, proje kökünü Python import yoluna ekler ve göreli eski veri yollarını bu köke sabitler. Bu nedenle scriptler yalnızca proje kökünden değil, farklı bir çalışma klasöründen de çağrılabilir.

Örnek:

```powershell
python C:\Users\Emir\Desktop\FootballDatabase_v2\tools\maintenance\root_scripts\check_players_json.py
```

## Notlar

- Orijinal `C:\Users\Emir\Desktop\FootballDatabase` klasörü değiştirilmedi.
- Eski `.venv`, başka bir kullanıcı hesabındaki Python kurulumuna bağlı olduğu için V2'ye kopyalanmadı.
- Bağımlılık listesine Flask, Flask-SocketIO, Beautiful Soup ve Pillow eklendi.
- Üretimde `FOOTBALL_MATCH_SECRET_KEY` ortam değişkeni tanımlanmalıdır.
- `server` modülü bu değişken verilmediğinde geliştirme için kalıcı bir anahtar üretip `instance/server_secret.txt` içinde saklar.

## iPhone 13 üzerinde ilk uygulama testi

13 Eylül 2026 tarihinde Windows ve ücretsiz Apple hesabı kullanılarak ilk gerçek
cihaz kurulumu başarıyla tamamlandı:

1. Capacitor tabanlı iOS kabuğu GitHub'a gönderildi.
2. GitHub Actions macOS/Xcode runner'ı cihaz için ARM64, imzasız
   `EDYN-Football-unsigned.ipa` paketini üretti.
3. IPA'nın `app.edynfootball.mobile` Bundle ID'si, iPhoneOS hedefi, iOS 15 alt
   sınırı ve ARM64 mimarisi doğrulandı.
4. Windows'a web sürümü iTunes, iCloud, Bonjour ve Apple Mobile Device Support
   ile Sideloadly kuruldu.
5. IPA, Sideloadly üzerinden ücretsiz Apple hesabıyla imzalanıp USB bağlantısı
   üzerinden iPhone 13'e yüklendi.
6. EDYN Football telefonda bağımsız uygulama olarak açıldı ve geçici Cloudflare
   sunucusuna bağlandı.

İlk test sunucusu
`https://diving-responsibility-annex-look.trycloudflare.com` adresidir. Bu bir
Quick Tunnel adresidir; üretim ve App Store sürümünde kalıcı
`https://api.edynfootball.app` hedefi kullanılacaktır. Ücretsiz Apple hesabıyla
oluşturulan cihaz imzası yaklaşık yedi gün geçerlidir; süresi dolunca aynı IPA
Sideloadly ile yeniden imzalanıp kurulmalıdır.

## 12 Eylül 2026 çalışma günlüğü

- Possession ve Tiki Taka Toe için oda kodunun yanında hesap tabanlı rastgele rakip eşleştirme eklendi.
- Çevrimiçi maçlarda `Oyuncu 1/2` yerine kullanıcıların hesap adları gösterilmeye başlandı.
- Sunucu ve dış yayın işlemleri değiştirilebilir sağlayıcı yapısına sahip bağımsız `server/` modülüne ayrıldı; Cloudflare Quick Tunnel desteği eklendi.
- Aynı portta çalışan eski sunucu süreçlerinin çevrimiçi odaları ayırdığı tespit edildi; sunucu tek süreçle çalışacak şekilde temizlendi.
- Possession cevapları her iki oyuncuya ortak `game_state` ve Socket.IO olayıyla iletilecek şekilde sağlamlaştırıldı.
- Possession’da verilen futbolcu cevabı ilgili peteğin sınırları içinde yalnızca futbolcu adı olarak 2 saniye gösterilecek şekilde sadeleştirildi.
- Maç sonu reklam uygunluğu ve 5 saniyelik fail-open davranışı bağımsız `ads.py` modülüne taşındı.
- Yalnızca normal tamamlanan, süreyle biten, kazanılan veya berabere sonuçlanan maçlar reklam için uygun kabul edildi; pes etme ve bağlantı kopması hariç tutuldu.
- Canlı reklam kimliği bulunmadığı sürece reklam sistemi oyunu engellemeden kapalı çalışacak şekilde ayarlandı.
- Uygulamanın App Store’da yayınlanacak bir iOS uygulamasına dönüştürülmesi hedeflendi.
- iOS reklam hedefi; `ads.py` sunucu politikası, WebView/native köprü, native `AdService.swift`, Google Mobile Ads SDK, UMP izin yönetimi ve AdMob interstitial akışı olarak planlandı.
- iOS sürümünde reklamın maç sırasında önceden yüklenmesi, tamamlanan maç sonunda gösterilmesi ve 5 saniye içinde hazır değilse sonuç ekranına geçilmesi kararlaştırıldı.
- Mobil uygulamada reklam yüklenmeden önce kişiselleştirilmiş veya kişiselleştirmesiz reklam tercihi alınır; tercih cihazda saklanır ve Profil ekranından değiştirilebilir. Kişiselleştirilmiş reklam seçildiğinde iOS izleme izni ayrıca istenir.
- Tamamlanmış çevrimiçi maçtan ayrılma, aktif maç bağlantı kopmasından ayrı değerlendirilir; bitmiş maç için rakibe hükmen galibiyet bildirimi gönderilmez.

## 13 Eylül 2026 çalışma günlüğü

- Proje `emirdurak5934/Hex_FootBall` GitHub deposuna başarıyla yüklendi.
- GitHub Actions üzerinde Capacitor/Xcode doğrulama build'i ve cihaz ARM64
  imzasız IPA üretimi başarıyla tamamlandı.
- `EDYN-Football-unsigned.ipa` indirildi; paket yapısı, Bundle ID, iOS hedefi ve
  ARM64 mimarisi doğrulandı.
- Windows'a Apple cihaz sürücüleri, iTunes, iCloud, Bonjour ve Sideloadly
  kuruldu; Apple iPhone USB bağlantısı doğrulandı.
- IPA ücretsiz Apple hesabıyla Sideloadly üzerinden imzalanarak iPhone 13'e
  yüklendi ve EDYN Football telefonda uygulama olarak başarıyla açıldı.

## 22 Eylül 2026 çalışma günlüğü

- Missing 11 formaları için yalnız sunum katmanında takım renk/desen eşlemesi
  eklendi (`static/missing_xi_kits.js`). Aynı yeniden kullanılabilir forma öğesi
  `solid`, `stripes`, `half`, `sleeves` ve `centerStripe` desenleriyle 11 slota
  uygulanıyor; eşleşmeyen takımlar varsayılan düz formayı kullanıyor.
- Maç/oyuncu verisi, soru üretimi, tahmin doğrulama ve oyun sonucu mantığı
  değiştirilmedi. Takım temaları ve mevcut Missing 11 oynanışı test edildi;
  mobil, tablet ve masaüstü görünümleri kontrol edildi.
- Missing 11 tahmin ekranında ana menüye döndüren üst ok gizlendi. Tahmin
  ekranındaki kendi `GERİ` düğmesi korunuyor; sahaya dönünce ana menü oku
  yeniden görünüyor.
- Sonraki hedef: telefon uygulamasında oyun ekranlarının sayfa gibi kaymaması.
  Bu henüz uygulanmadı. Ekranlar cihaz başına ayrı ayarlarla değil, kullanılabilir
  yükseklik ve güvenli alanlara uyarlanan ortak responsive kurallarla ele alınacak;
  uzun listeler gerektiğinde yalnız kendi alanlarında kayabilecek.
- İş akış şeması, her küçük değişiklikte güncellenmemesi isteği nedeniyle bu
  çalışmada değiştirilmedi.
