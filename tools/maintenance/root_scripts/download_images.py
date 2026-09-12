import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import os
import io
import time
import requests

from PIL import Image


# ==================================================
# AYARLAR
# ==================================================

COMMONS_API = (
    "https://commons.wikimedia.org/w/api.php"
)

HEADERS = {
    "User-Agent":
        "FootballDatabaseGame/1.0 "
        "(trophy image downloader)"
}

TIMEOUT = 30
WAIT_SECONDS = 6
MAX_RETRIES = 6
IMAGE_SIZE = 512


# ==================================================
# KLASÖR
# ==================================================

OUTPUT_DIR = "static/trophies"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ==================================================
# LİG / KUPA / ÖDÜL
#
# Dosya adı -> Commons arama sorguları
# ==================================================

TROPHIES = {

    # ==================================================
    # LİGLER
    # ==================================================

    "premier_league.png": [
        "Premier League logo",
        "Premier League lion logo"
    ],

    "super_lig.png": [
        "Süper Lig logo",
        "Turkish Süper Lig logo"
    ],

    "la_liga.png": [
        "La Liga logo",
        "LaLiga logo"
    ],

    "serie_a.png": [
        "Serie A logo Italy",
        "Serie A football logo"
    ],

    "bundesliga.png": [
        "Bundesliga logo",
        "Bundesliga football logo Germany"
    ],

    "ligue_1.png": [
        "Ligue 1 logo",
        "Ligue 1 France football logo"
    ],


    # ==================================================
    # AVRUPA KUPALARI
    # ==================================================

    "champions_league.png": [
        "UEFA Champions League logo",
        "UEFA Champions League starball"
    ],

    "europa_league.png": [
        "UEFA Europa League logo",
        "Europa League logo"
    ],


    # ==================================================
    # MİLLİ TAKIM KUPALARI
    # ==================================================

    "world_cup.png": [
        "FIFA World Cup Trophy",
        "FIFA World Cup trophy football"
    ],

    "euro.png": [
        "UEFA European Championship trophy",
        "Henri Delaunay Trophy"
    ],

    "copa_america.png": [
        "Copa América trophy",
        "Copa America trophy football"
    ],


    # ==================================================
    # BİREYSEL
    # ==================================================

    "ballon_dor.png": [
        "Ballon d'Or trophy",
        "Ballon d'Or award"
    ],


    # ==================================================
    # YEREL KUPALAR
    # ==================================================

    "fa_cup.png": [
        "FA Cup trophy",
        "Football Association Challenge Cup trophy"
    ],

    "coppa_italia.png": [
        "Coppa Italia trophy",
        "Coppa Italia cup"
    ],

    "copa_del_rey.png": [
        "Copa del Rey trophy",
        "Copa del Rey cup"
    ]

}


# ==================================================
# SESSION
# ==================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ==================================================
# SAFE GET
# ==================================================

def safe_get(
    url,
    params=None
):

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                url,
                params=params,
                timeout=TIMEOUT
            )


            if response.status_code == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:

                    wait_time = int(
                        retry_after
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    wait_time = min(
                        15 * attempt,
                        90
                    )


                print(
                    f"429 geldi. "
                    f"{wait_time} saniye bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue


            if response.status_code in [
                500,
                502,
                503,
                504
            ]:

                wait_time = min(
                    10 * attempt,
                    60
                )

                print(
                    f"Sunucu hatası "
                    f"{response.status_code}. "
                    f"{wait_time} saniye bekleniyor..."
                )

                time.sleep(
                    wait_time
                )

                continue


            response.raise_for_status()

            return response


        except requests.RequestException as error:

            print(
                "Request hatası:",
                error
            )

            if attempt == MAX_RETRIES:

                raise


            wait_time = min(
                10 * attempt,
                60
            )

            print(
                f"{wait_time} saniye sonra "
                f"tekrar deneniyor..."
            )

            time.sleep(
                wait_time
            )


    raise RuntimeError(
        "İstek başarısız."
    )


# ==================================================
# COMMONS DOSYA ARAMA
# ==================================================

def search_commons_files(
    query
):

    params = {

        "action":
            "query",

        "format":
            "json",

        "formatversion":
            2,

        "generator":
            "search",

        "gsrsearch":
            query,

        "gsrnamespace":
            6,

        "gsrlimit":
            15,

        "prop":
            "imageinfo",

        "iiprop":
            "url",

        "iiurlwidth":
            IMAGE_SIZE

    }


    response = safe_get(
        COMMONS_API,
        params=params
    )


    data = response.json()


    pages = (
        data
        .get(
            "query",
            {}
        )
        .get(
            "pages",
            []
        )
    )


    return pages


# ==================================================
# SONUÇ PUANLAMA
# ==================================================

def score_result(
    title,
    query
):

    title_lower = title.lower()

    query_words = [

        word.lower()

        for word in query.split()

        if len(word) >= 3

    ]


    score = 0


    # ==================================================
    # İYİ KELİMELER
    # ==================================================

    if "logo" in title_lower:

        score += 22


    if "trophy" in title_lower:

        score += 24


    if "cup" in title_lower:

        score += 12


    if "ballon" in title_lower:

        score += 20


    if "champions league" in title_lower:

        score += 20


    if "europa league" in title_lower:

        score += 20


    if title_lower.endswith(
        ".svg"
    ):

        score += 8


    if title_lower.endswith(
        ".png"
    ):

        score += 5


    # ==================================================
    # QUERY KELİMELERİ
    # ==================================================

    for word in query_words:

        if word in title_lower:

            score += 3


    # ==================================================
    # KÖTÜ KELİMELER
    # ==================================================

    bad_words = [

        "match",
        "game",

        "player",
        "players",

        "team",

        "stadium",

        "fans",
        "supporters",

        "jersey",
        "shirt",
        "kit",

        "poster",

        "ticket",

        "season",

        "final whistle",

        "celebration",

        "winner team",

        "squad",

        "photo of",

        "photograph"

    ]


    for bad_word in bad_words:

        if bad_word in title_lower:

            score -= 35


    return score


# ==================================================
# EN İYİ SONUÇ
# ==================================================

def choose_best_result(
    pages,
    query
):

    candidates = []


    for page in pages:

        title = page.get(
            "title",
            ""
        )


        image_info = page.get(
            "imageinfo",
            []
        )


        if not title:

            continue


        if not image_info:

            continue


        info = image_info[0]


        image_url = (
            info.get(
                "thumburl"
            )
            or
            info.get(
                "url"
            )
        )


        if not image_url:

            continue


        score = score_result(
            title,
            query
        )


        candidates.append(
            (
                score,
                title,
                image_url
            )
        )


    if not candidates:

        return None


    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )


    print(
        "En iyi adaylar:"
    )


    for score, title, _ in candidates[:5]:

        print(
            f"  {score:>3} | {title}"
        )


    best = candidates[0]


    if best[0] < 5:

        return None


    return {

        "score":
            best[0],

        "title":
            best[1],

        "url":
            best[2]

    }


# ==================================================
# PNG KAYDET
# ==================================================

def save_as_png(
    image_bytes,
    output_path
):

    image = Image.open(
        io.BytesIO(
            image_bytes
        )
    )


    image.load()


    if image.mode != "RGBA":

        image = image.convert(
            "RGBA"
        )


    image.thumbnail(
        (
            IMAGE_SIZE,
            IMAGE_SIZE
        ),
        Image.Resampling.LANCZOS
    )


    image.save(
        output_path,
        "PNG",
        optimize=True
    )


# ==================================================
# GÖRSEL İNDİR
# ==================================================

def download_image(
    url,
    output_path
):

    response = safe_get(
        url
    )


    save_as_png(
        response.content,
        output_path
    )


# ==================================================
# TEK KRİTER
# ==================================================

def download_trophy(
    filename,
    queries
):

    output_path = os.path.join(
        OUTPUT_DIR,
        filename
    )


    if os.path.exists(
        output_path
    ):

        print()

        print(
            "ZATEN VAR:",
            output_path
        )

        return True


    print()

    print(
        "=" * 60
    )

    print(
        filename
    )

    print(
        "=" * 60
    )


    for query in queries:

        print()

        print(
            "Commons araması:",
            query
        )


        try:

            pages = search_commons_files(
                query
            )

        except Exception as error:

            print(
                "Arama hatası:",
                error
            )

            continue


        result = choose_best_result(
            pages,
            query
        )


        if not result:

            print(
                "Uygun görsel bulunamadı."
            )

            time.sleep(
                WAIT_SECONDS
            )

            continue


        print()

        print(
            "SEÇİLEN:",
            result["title"]
        )


        try:

            download_image(
                result["url"],
                output_path
            )

        except Exception as error:

            print(
                "İndirme hatası:",
                error
            )

            time.sleep(
                WAIT_SECONDS
            )

            continue


        print(
            "KAYDEDİLDİ:",
            output_path
        )


        return True


    return False


# ==================================================
# BAŞLAT
# ==================================================

print()

print(
    "=" * 60
)

print(
    "TROPHY / LEAGUE IMAGE DOWNLOADER"
)

print(
    "=" * 60
)

print(
    "Toplam kriter:",
    len(TROPHIES)
)


success = 0

failed = 0


for filename, queries in TROPHIES.items():

    try:

        result = download_trophy(
            filename,
            queries
        )

    except Exception as error:

        print(
            "BEKLENMEYEN HATA:",
            error
        )

        result = False


    if result:

        success += 1

    else:

        failed += 1


    print(
        f"\n{WAIT_SECONDS} saniye bekleniyor..."
    )


    time.sleep(
        WAIT_SECONDS
    )


# ==================================================
# EKSİKLER
# ==================================================

print()

print(
    "=" * 60
)

print(
    "SONUÇ"
)

print(
    "=" * 60
)


print(
    "Başarılı:",
    success
)

print(
    "Başarısız:",
    failed
)


print()

print(
    "EKSİK DOSYALAR"
)

print(
    "=" * 60
)


missing = []


for filename in TROPHIES:

    path = os.path.join(
        OUTPUT_DIR,
        filename
    )


    if not os.path.exists(
        path
    ):

        missing.append(
            path
        )


if not missing:

    print(
        "Eksik görsel yok."
    )

else:

    for path in missing:

        print(
            "-",
            path
        )


    print()

    print(
        "Toplam eksik:",
        len(missing)
    )


print()

print(
    "=" * 60
)

print(
    "PROGRAM BİTTİ"
)

print(
    "=" * 60
)

print()