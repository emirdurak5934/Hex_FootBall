# FootballDatabase V2 — Yaşayan İş Akışı ve Mimari Şeması

Bu belge projenin ortak çalışma haritasıdır. Yeni modül, özellik, hata düzeltmesi veya mimari değişiklik tamamlandığında ilgili düğümler, bağlantılar ve değişiklik günlüğü güncellenmelidir.

Son güncelleme: 12 Eylül 2026

## Görsel ana şema

![FootballDatabase V2 yaşayan iş akışı](PROJECT_WORKFLOW.png)

Görsel dosya `PROJECT_WORKFLOW.png` olarak doğrudan açılabilir. Düzenlenebilir vektör kaynağı `PROJECT_WORKFLOW.svg` dosyasıdır. Aşağıdaki Mermaid bölümleri ise şemanın metin tabanlı ayrıntılı kaynağıdır.

## 1. Uygulamanın ana akışı

```mermaid
flowchart TD
    USER["Kullanıcı / Tarayıcı"]
    PUBLIC["Değiştirilebilir Yayın Sağlayıcısı<br/>Cloudflare Quick Tunnel / gelecek adaptörler"]
    SERVER["Sunucu Yönetim Modülü<br/>server/"]
    HTTP["Flask HTTP Katmanı<br/>app.py"]
    SOCKET["Socket.IO Gerçek Zamanlı Katman<br/>app.py"]
    MATCHMAKING["Oyun Bazlı Rastgele Eşleştirme Kuyrukları<br/>yalnızca giriş yapmış hesaplar"]
    UI["Jinja Arayüzleri<br/>templates/"]
    FRONTEND["Tarayıcı Kodları<br/>static/*.js ve static/*.css"]

    USER <-->|"HTTPS ve WebSocket"| PUBLIC
    PUBLIC --> SERVER
    SERVER --> HTTP
    SERVER --> SOCKET
    HTTP -->|"HTML üretir"| UI
    UI --> FRONTEND
    FRONTEND -->|"HTTP / JSON"| HTTP
    FRONTEND <-->|"Socket.IO olayları"| SOCKET

    HTTP --> AUTH["Hesap ve Profil<br/>profile_store.py"]
    HTTP --> SOCIAL["Arkadaşlık Sistemi<br/>friend_store.py"]
    HTTP --> GAMES["Oyun Modları"]
    SOCKET --> MATCHMAKING
    MATCHMAKING --> ROOMS["Oda, Davet ve Maç Durumu<br/>Bellek içi çalışma zamanı"]
    SOCKET --> ROOMS
    ROOMS --> GAMES

    AUTH --> SQLITE[("SQLite<br/>instance/football_match.sqlite3")]
    SOCIAL --> SQLITE
    GAMES --> CRITERIA["Merkezi Kriter Motoru<br/>criterion_engine.py"]
    GAMES --> TIKI["Tiki Taka Motoru<br/>tiki_taka_engine.py"]
    CRITERIA --> PLAYERS[("Futbolcu Verisi<br/>data/players.json")]
    TIKI --> PLAYERS
    GAMES --> XI[("Missing XI Maçları<br/>data/missing_xi_matches.json")]
```

## 2. Oyun modları

```mermaid
flowchart LR
    HUB["Ana Oyun Merkezi<br/>/"]

    HUB --> POS["Possession<br/>/possession"]
    HUB --> HEAT["Heatmap<br/>/heatmap"]
    HUB --> MISS["Missing XI<br/>/missing-xi"]
    HUB --> TTT["Tiki Taka Toe<br/>/tiki-taka-toe"]

    POS --> POSLOGIC["Hex tahta, komşuluk,<br/>hücre alma ve çalma"]
    POS --> ONLINE["Socket.IO odası, rastgele eşleşme,<br/>hesap adları, petek üstünde 2 sn cevap,<br/>hamle, süre ve rövanş"]
    ONLINE --> ADS["ads.py maç sonu reklam politikası<br/>yalnız tamamlanan maç + 5 sn üst sınır"]

    HEAT --> HEATLOGIC["Hex tahta, kombo,<br/>Reheat ve Heat Density"]

    MISS --> WORDLE["11 pozisyon ve<br/>Wordle harf geri bildirimi"]

    TTT --> GRID["3 × 3 kriter kesişimi"]
    TTT --> LOCAL["Yerel oyun"]
    TTT --> ONLINE

    POSLOGIC --> VALIDATE["Futbolcu ve kriter doğrulama"]
    HEATLOGIC --> VALIDATE
    WORDLE --> VALIDATE
    GRID --> VALIDATE
    VALIDATE --> DATA[("players.json")]
```

## 3. Kullanıcı, sosyal ve ilerleme akışı

```mermaid
flowchart TD
    GUEST["Misafir"] --> REGISTER["Kayıt / Giriş"]
    REGISTER --> USER["Oturum açmış kullanıcı"]

    USER --> PROFILE["Profil ve avatar"]
    USER --> FRIENDS["Arkadaş ara / ekle / çıkar"]
    USER --> INVITE["Arkadaşına oyun daveti"]
    USER --> MATCH["Oyun veya çevrimiçi maç"]

    INVITE --> MATCH
    MATCH --> RESULT["Sonuç ve oyun metrikleri"]
    RESULT --> XP["XP ve seviye"]
    RESULT --> STATS["Mod bazlı istatistikler"]
    XP --> LEADERBOARD["Liderlik tablosu"]
    STATS --> PROFILE

    PROFILE --> DB[("SQLite")]
    FRIENDS --> DB
    XP --> DB
    STATS --> DB
```

## 4. Veri bakım akışı

Bu alan çalışan web uygulamasından ayrıdır. Bakım scriptleri `tools/maintenance/` altında bulunur ve proje kökünü kendi `__file__` konumlarından `os.path` ile hesaplar.

```mermaid
flowchart LR
    SOURCES["Haricî kaynaklar<br/>Wikidata / Transfermarkt"]
    COLLECT["Toplama scriptleri"]
    ENRICH["Doğum tarihi, milliyet,<br/>pozisyon, kulüp ve kupa zenginleştirme"]
    AUDIT["Audit / check / inspect"]
    BACKUP["İşlem öncesi yedek"]
    CLEAN["Temizleme ve mükerrer birleştirme"]
    REPORT["JSON / TXT raporları"]
    DATA[("data/players.json")]
    TESTS["tests/"]

    SOURCES --> COLLECT
    COLLECT --> ENRICH
    DATA --> AUDIT
    ENRICH --> AUDIT
    AUDIT -->|"Sorun yok"| BACKUP
    AUDIT -->|"İnceleme sonucu"| REPORT
    BACKUP --> CLEAN
    CLEAN --> DATA
    CLEAN --> REPORT
    DATA --> TESTS
```

## 5. Yeni istek ve modül geliştirme akışı

Bundan sonraki talepler bu akış üzerinden ele alınacaktır.

```mermaid
flowchart TD
    REQUEST["1. Yeni istek / modül tanımı"]
    SCOPE["2. Etkilenen şema düğümlerini belirle"]
    CONTRACT["3. Veri, API, oyun kuralı<br/>ve arayüz sözleşmesini netleştir"]
    IMPLEMENT["4. En küçük güvenli uygulama"]
    VERIFY["5. Sözdizimi, test ve açılış kontrolü"]
    DECISION{"Kontroller başarılı mı?"}
    FIX["Sorunu düzelt"]
    DOCS["6. README ve bu şemayı güncelle"]
    LOG["7. Değişiklik günlüğüne kayıt ekle"]
    DONE["Tamamlandı"]

    REQUEST --> SCOPE --> CONTRACT --> IMPLEMENT --> VERIFY --> DECISION
    DECISION -->|"Hayır"| FIX --> VERIFY
    DECISION -->|"Evet"| DOCS --> LOG --> DONE
```

## 6. Modül kayıt tablosu

| Alan | Ana dosyalar | Veri kaynağı | Durum |
|---|---|---|---|
| HTTP ve sayfa yönlendirme | `app.py`, `templates/` | Oturum ve oyun verileri | Aktif |
| Sunucu ve yayın yönetimi | `server/`, `run.py`, `server_olusturucu.py` | Ortam değişkenleri, sağlayıcı adaptörleri ve menülü başlatıcı | Aktif |
| Maç sonu reklam politikası | `ads.py` | Maç bitiş türü, reklam yapılandırması ve 5 saniyelik üst sınır | Altyapı aktif, canlı AdMob bekleniyor |
| iOS App Store uygulaması | `IOS_WINDOWS_IPA_PLANI.md`, `capacitor.config.json`, `mobile-shell/`, planlanan `AdService.swift` | Windows geliştirme, değiştirilebilir test sunucusu, bulut macOS/Xcode CI, kalıcı Flask backend | Geliştiriliyor |
| Gerçek zamanlı oyun | `app.py`, `static/game.js`, `static/tiki_taka.js` | Oyun bazlı eşleştirme kuyrukları ve bellek içi oda durumu | Aktif |
| Possession | `app.py`, `templates/index.html`, `static/game.js` | `players.json` | Aktif |
| Heatmap | `app.py`, `templates/heatmap.html`, `static/heatmap.js` | `players.json` | Aktif |
| Missing XI | `app.py`, `templates/missing_xi.html`, `static/missing_xi.js` | `players.json`, `missing_xi_matches.json` | Aktif |
| Tiki Taka Toe | `app.py`, `tiki_taka_engine.py`, `templates/tiki_taka.html`, `static/tiki_taka.js` | `players.json` | Aktif |
| Kriter doğrulama | `criterion_engine.py`, `league_clubs.py` | `players.json` | Aktif |
| Hesap ve profil | `profile_store.py`, `templates/profile.html` | SQLite | Aktif |
| Arkadaşlık ve davet | `friend_store.py`, `templates/friends.html`, `static/friends.js` | SQLite ve Socket.IO | Aktif |
| Liderlik tablosu | `profile_store.py`, `templates/leaderboard.html` | SQLite | Aktif |
| Veri bakımı | `tools/maintenance/` | JSON ve haricî kaynaklar | Uygulamadan ayrılmış |
| Otomatik kontroller | `tests/` | Uygulama ve test verileri | Aktif |
| Eski sürüm | `legacy/` | Eski Streamlit yaklaşımı | Arşiv |

## 7. Şema güncelleme kuralları

Her işlemden sonra:

1. Yeni modül varsa uygun Mermaid şemasına düğüm olarak eklenir.
2. Modüller arası yeni veri veya çağrı ilişkisi varsa oklarla gösterilir.
3. Dosya taşındıysa modül kayıt tablosundaki yolu değiştirilir.
4. Modülün durumu `Planlandı`, `Geliştiriliyor`, `Aktif`, `Pasif` veya `Arşiv` olarak işaretlenir.
5. Veri yapısı değiştiyse veri bakım akışı güncellenir.
6. Son güncelleme tarihi değiştirilir.
7. Aşağıdaki günlüğe kısa bir kayıt eklenir.

## 8. Değişiklik günlüğü

| Tarih | Değişiklik | Etkilenen alanlar |
|---|---|---|
| 11 Eylül 2026 | İlk yaşayan iş akışı ve mimari şeması oluşturuldu. | Tüm proje |
| 11 Eylül 2026 | Workflow, doğrudan açılabilen PNG ve düzenlenebilir SVG şemasına dönüştürüldü. | Proje dokümantasyonu |
| 11 Eylül 2026 | Çevrimiçi maç bağlantısı düzeltildi: yalnızca Possession ve Tiki Taka Toe çevrimiçi altyapıya bağlandı; Heatmap ve Missing XI tek oyunculu gösterildi. | Oyun modları, Socket.IO |
| 11 Eylül 2026 | Geliştirme sunucusu aynı Wi-Fi ağındaki mobil cihazlardan erişim için varsayılan olarak `0.0.0.0:5000` üzerinde dinleyecek şekilde ayarlandı. | Sunucu başlangıcı, mobil test |
| 12 Eylül 2026 | Possession ve Tiki Taka Toe için hesap tabanlı rastgele rakip eşleştirme eklendi; çevrimiçi maçlarda Oyuncu 1/2 yerine hesap adları gösterilmeye başlandı. | Socket.IO, Possession, Tiki Taka Toe, kullanıcı arayüzü |
| 12 Eylül 2026 | Sunucu başlatma ve dış yayın işlemleri `server/` modülüne ayrıldı; değiştirilebilir tünel sağlayıcısı sözleşmesi ve Cloudflare Quick Tunnel adaptörü eklendi. | Sunucu, dağıtım, güvenlik, workflow |
| 12 Eylül 2026 | Aynı ağ, Cloudflare dış yayın, yalnız tünel ve sistem kontrolü işlemleri için `server_olusturucu.py` menülü başlatıcısı eklendi. | Sunucu, mobil test, kullanım kolaylığı |
| 12 Eylül 2026 | Menülü sunucu başlatıcısının çift tıklamada kapanması önlendi; gerçek Cloudflare oyun adresi belirginleştirildi ve API adresinin public URL sanılması engellendi. | Sunucu, Cloudflare, kullanım kolaylığı |
| 12 Eylül 2026 | Başlatıcıya her ekranda aktif yerel/public adres gösterimi eklendi; Cloudflare URL durumu çalışan süreç kimliğiyle doğrulanarak kalıcılaştırıldı. | Sunucu, Cloudflare, durum görünürlüğü |
| 12 Eylül 2026 | Possession ve Tiki Taka Toe çevrimiçi maçlarında iki tarafın cevapları, hesap adı ve doğru/yanlış durumuyla 2 saniyelik geçici bildirim olarak gösterilmeye başlandı. | Socket.IO, çevrimiçi oyun arayüzleri |
| 12 Eylül 2026 | Possession cevap olayı petek indeksiyle genişletildi; cevap iki oyuncuda da ilgili peteğin üzerinde 2 saniye gösterilecek biçimde konumlandırıldı ve mobil önbellek sürümü yenilendi. | Possession Socket.IO, mobil arayüz |
| 12 Eylül 2026 | Possession cevap bildirimi en üst görsel katmana taşındı ve kayıp olaya karşı paylaşılan `game_state` içine de eklendi. | Possession Socket.IO, görünürlük ve teslimat |
| 12 Eylül 2026 | Possession petek bildirimi sadeleştirildi; yalnızca futbolcu adı, peteğin ölçüsüne uyarlanarak sınırlar içinde gösteriliyor. | Possession mobil arayüzü |
| 12 Eylül 2026 | Maç sonu reklam politikası `ads.py` modülüne ayrıldı; tamamlanan maçlar uygun, yarım kalan maçlar hariç ve reklam bekleme süresi en fazla 5 saniye olacak şekilde iki oyuna bağlandı. | Reklam modülü, Possession ve Tiki Taka Toe |
| 12 Eylül 2026 | App Store’da yayınlanacak iOS uygulaması hedefi eklendi; `ads.py` → native köprü → AdService → Google Mobile Ads SDK/AdMob interstitial akışı planlandı. | iOS, App Store ve reklam mimarisi |
| 13 Eylül 2026 | Mac sahibi olmadan Windows geliştirme → Capacitor → Git → bulut macOS/Xcode imzalama → TestFlight → iPhone → App Store dönüşüm planı oluşturuldu. | iOS, IPA, CI/CD, backend, TestFlight |
| 13 Eylül 2026 | Capacitor v8 bağımlılıkları ve iOS mobil başlatıcı eklendi; geçici Quick Tunnel varsayılan yapıldı, gelecekteki `api.edynfootball.app` adresi yeniden imza gerektirmeden cihazdan değiştirilebilir tasarlandı. | iOS, Capacitor, sunucu yapılandırması |
| 13 Eylül 2026 | GitHub macOS runner üzerinde Capacitor iOS projesi üretip imzasız simulator build'i doğrulayan ilk CI iş akışı eklendi; yerel kullanıcı verileri ve gereksiz veri yedekleri Git kapsamından çıkarıldı. | GitHub, iOS CI, güvenlik, depo boyutu |
| 13 Eylül 2026 | Hedef kaynak deposu `emirdurak5934/Hex_FootBall` olarak kaydedildi; ilk commit yerelde hazırlandı, GitHub kimlik doğrulaması kullanıcı oturumunda tamamlanmayı bekliyor. | GitHub, kaynak kontrolü, iOS CI |
| 13 Eylül 2026 | İlk IPA testi için değiştirilebilir mobil sunucu bağlantı ekranı ve Capacitor v8 yapılandırması eklendi; geçici Quick Tunnel varsayılan, `api.edynfootball.app` kalıcı hedef olarak izin listesine alındı. | Capacitor, iOS istemcisi, sunucu yapılandırması |
| 13 Eylül 2026 | Kalıcı backend adresi için `edynfootball.app` alan adı ve `https://api.edynfootball.app` API/Socket.IO adresi seçildi; alan adı kaydı bekleniyor. | DNS, Cloudflare Named Tunnel, iOS yapılandırması |

## 9. iOS App Store ve reklam hedefi

```mermaid
flowchart LR
    WEB["Flask web oyunu"] --> POLICY["ads.py<br/>tamamlanan maç kontrolü"]
    POLICY --> BRIDGE["WebView / native köprü"]
    BRIDGE --> IOS["iOS uygulaması<br/>Capacitor veya Swift"]
    IOS --> CONSENT["UMP ve gerekirse ATT"]
    CONSENT --> SERVICE["AdService.swift"]
    SERVICE --> ADMOB["Google Mobile Ads SDK<br/>AdMob interstitial"]
    ADMOB --> DECISION{"5 saniye içinde hazır mı?"}
    DECISION -->|"Evet"| SHOW["Reklamı göster"]
    DECISION -->|"Hayır"| RESULT["Sonuç ekranına geç"]
    SHOW --> RESULT
    RESULT --> STORE["App Store yayın hedefi"]
```

Temel kural: reklam yalnızca normal tamamlanan maçlarda denenir. Maç sonucu reklamdan önce kaydedilir; reklam bulunamaz, gösterilemez veya 5 saniye içinde hazır olmazsa kullanıcı engellenmeden sonuç ekranına geçer.

## 10. Windows'tan IPA üretim hedefi

```mermaid
flowchart LR
    WINDOWS["Windows<br/>kod ve test"] --> CAPACITOR["Capacitor<br/>native iOS kabuğu"]
    CAPACITOR --> REPO["Özel Git deposu"]
    REPO --> MACCI["Bulut macOS<br/>Xcode build + signing"]
    MACCI --> CONNECT["App Store Connect"]
    CONNECT --> TESTFLIGHT["TestFlight"]
    TESTFLIGHT --> IPHONE["iPhone 13 testi"]
    IPHONE --> APPSTORE["App Store"]
    CAPACITOR -->|"HTTPS / WSS"| BACKEND["Kalıcı Flask + Socket.IO backend"]
```

Ayrıntılı kararlar, fazlar ve kabul ölçütleri `IOS_WINDOWS_IPA_PLANI.md` dosyasındadır.
