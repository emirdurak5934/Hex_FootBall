# FootballDatabase V2

Bu klasör, orijinal `FootballDatabase` projesine dokunulmadan hazırlanmış düzenlenmiş kopyadır.

Projenin yaşayan mimari ve geliştirme haritası `PROJECT_WORKFLOW.md` dosyasındadır. Görsel sürüm `PROJECT_WORKFLOW.png`, düzenlenebilir kaynak ise `PROJECT_WORKFLOW.svg` olarak açılabilir. Yeni özellik veya modül tamamlandığında bu dosyalar da güncellenmelidir.

Possession ve Tiki Taka Toe çevrimiçi modlarında oda koduna ek olarak giriş yapmış kullanıcılar için rastgele rakip eşleştirme bulunur. Çevrimiçi maç ekranlarında oyuncular hesap adlarıyla gösterilir.

Çevrimiçi maç sırasında verilen futbolcu cevabı iki oyuncunun ekranında 2 saniye gösterilir. Possession oyununda yalnızca futbolcunun adı, cevap verilen peteğin sınırlarından taşmayacak şekilde görünür.
Possession cevap bilgisi hem anlık Socket.IO olayıyla hem de paylaşılan oyun durumuyla iletilir; böylece iki oyuncu da bildirimi alır.

## Maç sonu reklam modülü

Maç sonu reklam politikası ve tarayıcı denetleyicisi `ads.py` içinde tutulur. Tamamlanan maçlar reklam için uygun, pes etme ve bağlantı kopmasıyla biten maçlar uygun değildir. Reklam sağlayıcısı en fazla 5 saniye içinde yanıt vermezse sonuç ekranı reklamsız açılır.

Yapılandırma ortam değişkenleri:

- `FOOTBALL_ADS_ENABLED=1`
- `FOOTBALL_AD_PROVIDER`
- `FOOTBALL_AD_UNIT_PATH`
- `FOOTBALL_AD_TIMEOUT_MS` (varsayılan ve üst sınır: `5000`)

Canlı sağlayıcı adaptörü eklenene ve Google reklam birimi tanımlanana kadar reklam sistemi kapalı/fail-open çalışır.

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
