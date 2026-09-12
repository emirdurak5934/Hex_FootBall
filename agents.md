# POSSESSION / FUTBOL OYUNU — CODEX ANA PROJE TALİMATI

## 1. PROJENİN AMACI

Bu proje futbol bilgisine dayalı, mobil öncelikli bir oyun platformudur.

Uygulamanın ana hedefi tek bir uygulama içerisinde birden fazla futbol bilgi oyununu sunmaktır.

Şu anda planlanan 4 ana oyun modu:

1. Possession
2. Isı Haritası (Heatmap)
3. Kayıp İlk 11 (Missing XI)
4. Tiki Taka Toe

Projeyi geliştirirken mevcut çalışan özellikleri koru. Bir görev verilmediği sürece oyun kurallarını, veri yapısını veya çalışan sistemleri kendi kararınla değiştirme.

---

# 2. GENEL GELİŞTİRME KURALLARI

Codex bu proje üzerinde çalışırken aşağıdaki kurallara uymalıdır.

### Mevcut sistemi koru

Bir özellik üzerinde çalışırken ilgisiz dosyalarda gereksiz değişiklik yapma.

Çalışan oyun mekaniklerini değiştirme.

Bir hatayı düzeltirken başka özelliklerin davranışını değiştirmemeye çalış.

### Küçük ve kontrollü değişiklikler yap

Büyük çaplı yeniden yazımlar yerine mümkün olduğunca mevcut kod üzerinde küçük değişiklikler yap.

Örneğin kullanıcı:

> "Mobil görünümde peteklerin taşmasını düzelt."

derse sadece bu problem için gerekli HTML/CSS/JS değişikliklerini yap.

Oyunun geri kalanını yeniden tasarlama.

### Önce projeyi incele

Bir görev geldiğinde:

1. Proje klasör yapısını incele.
2. İlgili dosyaları belirle.
3. Mevcut kodun nasıl çalıştığını anla.
4. Değişikliğin başka sistemleri etkileyip etkilemeyeceğini kontrol et.
5. Sonra değişikliği yap.
6. Mümkünse çalıştır/test et.
7. Oluşan hata varsa düzelt.
8. Yapılan değişiklikleri kullanıcıya kısa şekilde açıkla.

### Kullanıcı onayı olmadan büyük mimari değişiklik yapma

Örneğin:

* framework değiştirme
* veri tabanı sistemini değiştirme
* klasör yapısını tamamen değiştirme
* büyük refactor
* çalışan sistemi baştan yazma
* yeni bağımlılık ekleme

gibi işlemleri kendiliğinden yapma.

Önce neden gerekli olduğunu açıkla.

---

# 3. OYUNCU VERİ TABANI

Projenin önemli parçalarından biri futbolcu veri tabanıdır.

Ana oyuncu verisi:

`data/players.json`

Dosyada binlerce futbolcu bulunabilir.

Oyuncularla ilgili temel olarak şu bilgiler tutulmaktadır/tutulacaktır:

* id
* name
* clubs
* nationality
* position
* trophies
* leagues
* individual achievements

Gereksiz istatistik verileri eklenmemelidir.

Oyuncu geçmişindeki kulüpler oyunun temel doğrulama mekanizmalarından biri olduğu için korunmalıdır.

---

# 4. MİLLİYET KURALI

Oyuncunun `nationality` değeri mümkün olduğunca oyuncunun temsil ettiği **A Milli Takımı** ifade etmelidir.

Doğum ülkesi esas alınmamalıdır.

Örnek:

Bir futbolcu İspanya'da doğmuş fakat Arjantin A Milli Takımı'nı temsil etmişse oyun açısından:

`nationality = Argentina`

olmalıdır.

Milli takım güncellemesi için daha önce `update_nationalities` sistemi üzerinde çalışılmıştır.

Bu sistemi değiştirirken mevcut JSON kayıtlarının zarar görmemesine özellikle dikkat et.

---

# 5. KULÜP VERİLERİ

Oyuncuların geçmişte oynadığı kulüpler önemlidir.

Kulüp geçmişi futbolcu cevaplarının doğrulanmasında kullanılacaktır.

Projeye veri eklenen önemli kulüpler arasında şunlar bulunmaktadır:

### İngiltere

* Manchester United
* Liverpool
* Arsenal
* Chelsea
* Newcastle United

### İspanya

* Real Madrid
* Barcelona
* Sevilla
* Atlético Madrid

### İtalya

* Juventus
* Inter
* Milan
* Napoli
* Roma

### Almanya

* Bayern Munich
* Borussia Dortmund

### Fransa

* Paris Saint-Germain
* Monaco

### Portekiz

* Benfica
* Sporting CP

### Hollanda

* Ajax

### Türkiye

* Galatasaray
* Fenerbahçe
* Beşiktaş
* Trabzonspor

Bu liste projenin nihai kulüp listesi değildir. Yeni kulüpler eklenebilir.

---

# 6. KUPALAR

Oyuncuların kazandığı kupaların veri tabanına eklenmesi planlanmıştır/üzerinde çalışılmıştır.

Kupa verileri için tercih edilen kaynak Transfermarkt'tır.

Burada amaç oyuncunun detaylı sezon istatistiklerini çekmek değil, yalnızca kazandığı kupaları kaydetmektir.

`trophies` alanını işlerken mevcut oyuncu JSON yapısını bozma.

---

# 7. OYUN MODU 1 — POSSESSION

Possession projenin ana oyun modlarından biridir.

İki oyunculu, futbol bilgisine dayalı hex-grid oyunudur.

## Tahta

Hedef tahta düzeni:

**4 - 5 - 4 - 5 - 4 - 5 - 4**

şeklinde petek satırlarından oluşur.

Petekler görsel olarak birbirine düzgün bağlanmalıdır.

Mobil ekran önceliklidir.

---

# 8. POSSESSION TEMEL MEKANİĞİ

Oyuncu bir peteğe dokunur.

Bir cevap penceresi/modal açılır.

Modal içerisinde:

* seçilen petek
* ilgili kategori
* gerekiyorsa komşu petekler
* futbolcu giriş alanı

bulunabilir.

Oyuncu futbolcu ismi girer.

Sistem `players.json` üzerinden futbolcunun kategoriye uygun olup olmadığını kontrol eder.

Doğruysa petek oyuncunun olur.

---

# 9. POSSESSION KOMŞU PETEK KURALI

Bu sistem oyunun önemli mekaniklerinden biridir ve kullanıcı açıkça istemedikçe değiştirilmemelidir.

Bir futbolcu seçilen peteğin kategorisine uyuyorsa seçilen petek alınır.

Ardından aynı futbolcu seçilen peteğin **komşu peteklerinin kategorileriyle** de kontrol edilir.

Futbolcu komşu peteğe de uyuyorsa o petek de aynı hamlede alınabilir.

Örneğin bir futbolcu:

* Real Madrid
* Manchester United
* Juventus

kategorilerine uyuyorsa ve bu petekler birbirine komşuysa aynı cevap birden fazla peteği etkileyebilir.

---

# 10. RAKİPTEN PETEK ÇALMA

Possession'da rakibin sahip olduğu bir petek uygun bağlantı ve cevap şartları oluştuğunda çalınabilir.

Bu mekanik oyunun stratejik parçalarından biridir.

Komşuluk sistemi değiştirilirken rakipten petek alma mekanizmasının bozulmamasına dikkat et.

---

# 11. BAĞLANTI KURALI

Bir futbolcu birden fazla kategoriye uyuyor diye tahtanın herhangi bir yerindeki tüm uygun petekler otomatik alınmamalıdır.

Etki **komşuluk/bağlantı sistemi** üzerinden ilerlemelidir.

Bağlantı yoksa yalnızca seçilen uygun petek alınmalıdır.

Bu kural önemlidir.

---

# 12. POSSESSION ARAYÜZÜ

Mobil kullanım önceliklidir.

Peteklerin:

* ekran dışına taşmaması
* birbirinin üzerine binmemesi
* düzgün hex-grid görünümü oluşturması
* logoların peteğin içinde düzgün görünmesi

gerekmektedir.

Daha önce petek yüksekliği ve dikey boşluklarla ilgili düzenlemeler yapılmıştır.

Tasarımla ilgili değişiklik yaparken oyun mekaniğine dokunma.

---

# 13. POSSESSION MODAL

Petek seçildiğinde cevap modalı açılmalıdır.

Modal mümkün olduğunca hızlı ve sade kullanılmalıdır.

Daha önce kullanılan ayrı bir **"Seç"** butonu kaldırılmıştır.

Petek doğrudan tıklanabilir/dokunabilir olmalıdır.

---

# 14. POSSESSION MAÇ SÜRESİ

Oyuna maç süresi eklenmesi planlanmıştır.

Arayüzde süre gösterilebilir.

Hamle geçmişinin ana oyun ekranında gösterilmesi şu an için istenmemektedir.

Gereksiz lejant da ana ekranda bulunmamalıdır.

---

# 15. NASIL OYNANIR

Ana oyun ekranında küçük bir soru işareti / yardım butonu bulunabilir.

Tıklandığında "Nasıl Oynanır?" açıklaması modal şeklinde açılmalıdır.

Ana ekranı uzun açıklamalarla doldurma.

---

# 16. POSSESSION MULTIPLAYER

Possession'ın çevrimiçi iki oyunculu olması hedeflenmektedir.

İki temel multiplayer seçeneği vardır:

### Rastgele Rakip

Oyuncu matchmaking sistemine girer ve başka bir oyuncuyla eşleşir.

### Arkadaşınla Oyna

Oyuncu bu bölüme girdiğinde iki seçenek görmelidir:

**Oda Kur**

ve

**Oda Kodu Gir**

---

# 17. ODA SİSTEMİ

`Oda Kur` seçildiğinde sistem bir oda oluşturmalıdır.

Odaya benzersiz bir oda kodu verilmelidir.

Kullanıcı bu kodu arkadaşına gönderebilir.

Diğer oyuncu:

`Oda Kodu Gir`

bölümünden kodu yazarak aynı maça katılır.

---

# 18. KULLANICI HESAPLARI

Uygulamada kalıcı kullanıcı hesapları/profilleri olması hedeflenmektedir.

Online maç sonuçları kullanıcı profilinde saklanmalıdır.

Minimum istatistikler:

* toplam maç
* galibiyet
* mağlubiyet
* kazanma oranı

---

# 19. GELİŞMİŞ PROFİL İSTATİSTİKLERİ

İleride şu istatistiklerin de tutulması planlanmaktadır:

### Genel

* toplam maç
* toplam galibiyet
* toplam mağlubiyet
* win rate
* mevcut galibiyet serisi
* en iyi galibiyet serisi

### Possession

* oynanan maç
* kazanılan maç
* kaybedilen maç
* alınan toplam petek
* rakipten çalınan toplam petek

### Heatmap

* en yüksek skor
* Heat Density rekoru

### Missing XI

* tamamlanan bulmacalar
* doğruluk oranı

### Tiki Taka Toe

* tamamlanan gridler
* en hızlı tamamlama
* geçerli bulunan toplam futbolcu

Bu sistemler henüz tamamen uygulanmamış olabilir.

Kodda bulunmayan özelliği mevcutmuş gibi varsayma.

---

# 20. OYUN MODU 2 — ISI HARİTASI / HEATMAP

Bu tek oyunculu bir moddur.

Oyuncu boş bir petek seçer.

Kategoriye uygun futbolcu girer.

Doğru cevap verilirse petek alınır.

Aynı futbolcu komşu peteklerin kategorilerine de uyuyorsa komşular da alınabilir.

---

# 21. HEATMAP KOMBO PUANI

Tek hamlede alınan petek sayısına göre puan artar.

Temel sistem:

* 1 petek = 1 puan
* 2 petek = 3 puan
* 3 petek = 6 puan
* 4 petek = 10 puan

Mantık üçgensel biçimde artan kombo ödülüdür.

---

# 22. REHEAT

Heatmap içerisinde daha önce doldurulmuş komşu petekler yeni cevapla tekrar eşleşirse:

* +1 puan
* petek tekrar "ısınmış" kabul edilir

Bu sisteme **Reheat** denir.

---

# 23. HEAT DENSITY

Tüm petekler dolduğunda oyun biter.

Oyun sonunda **Heat Density** değeri gösterilir.

Bu değer genel olarak tahtanın ne kadar verimli/yoğun şekilde ısıtıldığını temsil eder.

---

# 24. OYUN MODU 3 — KAYIP İLK 11 / MISSING XI

Bu modda kullanıcı tarihsel bir futbol maçından bir takımın ilk 11'ini tamamlamaya çalışır.

Her pozisyon bir mini Wordle mantığıyla çözülebilir.

Oyuncu isimleri tahmin edilir.

Harfler:

* doğru harf + doğru konum
* doğru harf + yanlış konum
* isimde olmayan harf

şeklinde geri bildirim verebilir.

Örnek oyuncu isimleri:

* MESSI
* NEUER
* VARDY

Ama gerçek bulmacalar tarihsel maçlardan üretilecektir.

---

# 25. OYUN MODU 4 — TIKI TAKA TOE

3 × 3 grid üzerinde oynanan futbol bilgi oyunudur.

Satır ve sütunlarda farklı kriterler bulunur.

Kullanıcı kesişime uygun futbolcu bulmalıdır.

---

# 26. TIKI TAKA TOE — TEKLİ MOD

Oyuncu **Kick Off** ile oyunu başlatır.

Planlanan süre:

**3 dakika**

İki temel hedef düşünülebilir:

1. 9 kutuyu tamamlamak
2. Süre içerisinde mümkün olduğunca fazla geçerli futbolcu bulmak

Günlük yeni grid sistemi planlanmaktadır.

---

# 27. TIKI TAKA TOE KURALLARI

Dikkat edilmesi gereken bazı kurallar:

* Bir futbolcu birden fazla kutuya uygun olabilir.
* Akademide bulunmak tek başına kulüpte oynamış sayılmayabilir.
* Milli takım doğum ülkesinden farklı olabilir.
* Aynı isimli futbolcular doğum tarihi gibi ek bilgilerle ayrıştırılabilir.

---

# 28. TIKI TAKA TOE MULTIPLAYER

Tiki Taka Toe'un iki oyunculu karşılıklı versiyonu da planlanmaktadır.

Multiplayer sistemi geliştirilirken Possession için kurulacak kullanıcı/oda altyapısının tekrar kullanılabilmesi tercih edilir.

Gereksiz yere iki ayrı multiplayer altyapısı oluşturma.

---

# 29. TEKNİK GEÇMİŞ

Projenin erken prototiplerinde Streamlit kullanılmıştır.

Daha sonra Flask tarafına geçilmiştir.

Daha önce karşılaşılan sorunlardan biri:

`signal only works in main thread`

hatasıdır.

Flask çalıştırma tarafında:

`127.0.0.1:5000`

kullanılmıştır.

Projeyi incelemeden mevcut framework'ün hâlâ ne olduğunu varsayma.

Mevcut kod ne kullanıyorsa önce onu tespit et.

---

# 30. ÖNEMLİ DOSYALAR

Projede daha önce kullanılan/konuşulan dosya ve modüller arasında şunlar bulunmaktadır:

* `data/players.json`
* `data/processed_teams.json`
* `data/logs.txt`
* `config`
* `players.py`
* `api.py`
* `main.py`
* `enrich_players`
* `update_nationalities`
* trophies scraper
* HTML dosyaları
* CSS dosyaları
* static klasörü

Dosya isimlerinin güncel projede değişmiş olabileceğini unutma.

Önce mevcut klasör yapısını kontrol et.

---

# 31. JSON GÜVENLİĞİ

`players.json` projenin en değerli dosyalarından biridir.

Bu dosyada toplu işlem yapılırken özellikle dikkat et.

Script yazarken mümkünse:

* hata durumunu yönet
* ilerlemeyi logla
* işlem yarıda kesilirse devam edilebilir tasarla
* mevcut kayıtları gereksiz yere silme
* JSON'u geçersiz hale getirme
* mümkün olduğunda güvenli kayıt yöntemi kullan

Binlerce oyuncunun verisini tek bir hata nedeniyle kaybetme riski oluşturma.

---

# 32. SCRIPT DEVAM EDEBİLİRLİĞİ

Uzun süren veri scriptlerinin kaldığı yerden devam edebilmesi önemlidir.

Script yarıda kesildiğinde tüm oyuncuların baştan işlenmesi mümkün olduğunca engellenmelidir.

İşlenen kayıtların kaydedilmesi ve gerekirse log/processed sistemi kullanılması tercih edilir.

---

# 33. VERİ KAYNAKLARI

Proje mümkün olduğunca ücretsiz/verimli veri kaynakları kullanmalıdır.

Daha önce:

* Wikidata
* Transfermarkt

üzerinde çalışılmıştır.

Wikidata tarafında zaman zaman `502` gibi bağlantı hataları yaşanmıştır.

Dış servislere yapılan isteklerde:

* timeout
* retry
* rate limit
* bekleme süresi
* hata yönetimi

göz önünde bulundurulmalıdır.

---

# 34. TASARIM FELSEFESİ

Uygulama:

* modern
* sade
* futbol odaklı
* mobil öncelikli
* hızlı anlaşılır
* oyun hissi veren

bir arayüze sahip olmalıdır.

Ancak kullanıcı açıkça tasarım değişikliği istemedikçe çalışan ekranı tamamen yeniden tasarlama.

---

# 35. CODEX İÇİN KRİTİK KURAL

Kullanıcı genellikle belirli bir problemi çözmek isteyecektir.

Örneğin:

> "index.html'deki 5 problemi çöz."

Bu durumda:

**Sadece gerekli problemleri çöz.**

Kullanıcının istemediği yeni özellikler ekleme.

Çalışan özellikleri "daha iyi olur" düşüncesiyle kendiliğinden değiştirme.

---

# 36. HATA DÜZELTME PROSEDÜRÜ

Bir hata verildiğinde şu sırayla ilerle:

1. Hatanın kaynağını belirle.
2. İlgili dosyaları oku.
3. Hatanın nedenini açıkla.
4. En küçük güvenli düzeltmeyi yap.
5. Syntax hatalarını kontrol et.
6. Mümkünse uygulamayı/scripti çalıştır.
7. Yeni hata oluşup oluşmadığını kontrol et.
8. Sonucu kullanıcıya bildir.

---

# 37. YENİ ÖZELLİK PROSEDÜRÜ

Yeni özellik istendiğinde:

1. Önce mevcut mimaride özelliğin nereye ait olduğunu belirle.
2. Var olan sistemleri mümkün olduğunca tekrar kullan.
3. Gereksiz yeni dosya/bağımlılık oluşturma.
4. Backend ve frontend etkilerini kontrol et.
5. Veri tabanı etkisini kontrol et.
6. Özelliği uygula.
7. Test et.
8. Değiştirilen dosyaları kullanıcıya bildir.

---

# 38. PROJENİN ÖNCELİĞİ

Öncelik sırası:

**Çalışan oyun > doğru oyun mekaniği > veri doğruluğu > mobil kullanılabilirlik > görsel iyileştirme**

Görsel güzellik uğruna oyun mantığını bozma.

---

# 39. KULLANICIYLA ÇALIŞMA ŞEKLİ

Kullanıcı yazılım geliştirmeyi proje üzerinde öğrenerek ilerlemektedir.

Bu nedenle yapılan değişiklikleri gereksiz teknik karmaşıklık oluşturmadan açıkla.

Örneğin iş sonunda:

**Değiştirdiğim dosyalar**

* `index.html`
* `style.css`

**Ne yaptım**

* Mobil petek taşmasını düzelttim.
* Hex-grid aralığını düzelttim.
* Oyun mantığına dokunmadım.

**Test**

* Sayfa açılıyor.
* Console'da ilgili hata kalmadı.

gibi kısa bir rapor yeterlidir.

---

# 40. SON TALİMAT

Bu belge projenin bağlamını açıklamak içindir.

Ancak **gerçek kod her zaman mevcut proje klasöründeki dosyalardır.**

Bu nedenle:

**Bu belgede yazan bir şey ile mevcut kod çelişiyorsa kendi başına karar verip büyük değişiklik yapma.**

Önce mevcut implementasyonu incele.

Görev için gerekli değilse çelişen bölüme dokunma.

Önemli bir mimari karar gerekiyorsa kullanıcıya bildir.

Her görevde temel prensip:

> **Önce mevcut sistemi anla → en küçük güvenli değişikliği yap → test et → çalışan sistemi koru.**
