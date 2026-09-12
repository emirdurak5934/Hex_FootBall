import os as _path_os
import sys as _path_sys

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in _path_sys.path:
    _path_sys.path.insert(0, PROJECT_ROOT)
_path_os.chdir(PROJECT_ROOT)
import json
import time
import unicodedata
import string
import re
import requests

from bs4 import BeautifulSoup


# ==================================================
# AYARLAR
# ==================================================

PLAYERS_FILE = "data/players.json"

START_YEAR = 1990

WAIT_SECONDS = 3


BASE_URL = (
    "https://www.transfermarkt.com/"
    "real-madrid/alumni/verein/418/"
    "buchstabe/{letter}/land_id/0/"
    "position/alle/detailposition/alle/"
    "plus/1"
)


HEADERS = {

    "User-Agent":
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"

}


# ==================================================
# NORMALIZE
# ==================================================

CONFUSABLE_CHARACTERS = {

    # YUNANCA

    "Α": "A",
    "α": "a",

    "Β": "B",
    "β": "b",

    "Ε": "E",
    "ε": "e",

    "Ι": "I",
    "ι": "i",

    "Κ": "K",
    "κ": "k",

    "Μ": "M",
    "μ": "m",

    "Ν": "N",

    "Ο": "O",
    "ο": "o",

    "Ρ": "P",
    "ρ": "p",

    "Τ": "T",
    "τ": "t",

    "Χ": "X",
    "χ": "x",


    # KİRİL

    "А": "A",
    "а": "a",

    "В": "B",

    "Е": "E",
    "е": "e",

    "К": "K",
    "к": "k",

    "М": "M",
    "м": "m",

    "Н": "H",

    "О": "O",
    "о": "o",

    "Р": "P",
    "р": "p",

    "С": "C",
    "с": "c",

    "Т": "T",
    "т": "t",

    "Х": "X",
    "х": "x"

}


def normalize(text):

    text = str(
        text
    ).strip()


    text = "".join(
        CONFUSABLE_CHARACTERS.get(
            char,
            char
        )
        for char in text
    )


    text = text.lower()


    text = unicodedata.normalize(
        "NFKD",
        text
    )


    text = "".join(
        char
        for char in text
        if not unicodedata.combining(
            char
        )
    )


    text = " ".join(
        text.split()
    )


    return text


# ==================================================
# TARİHTEN YIL ÇIKAR
# ==================================================

def extract_year(text):

    if not text:

        return None


    text = str(
        text
    ).strip()


    # Örnek:
    #
    # 30/06/2025
    # 01/07/2012
    # 2025
    #
    # gibi değerlerden yıl bul.

    years = re.findall(
        r"\b(19\d{2}|20\d{2})\b",
        text
    )


    if not years:

        return None


    try:

        return int(
            years[-1]
        )

    except ValueError:

        return None


# ==================================================
# DATABASE YÜKLE
# ==================================================

with open(
    PLAYERS_FILE,
    "r",
    encoding="utf-8"
) as file:

    players = json.load(file)


database_names = set()


for player in players:

    name = str(
        player.get(
            "name",
            ""
        )
    ).strip()


    if not name:

        continue


    database_names.add(
        normalize(
            name
        )
    )


print()

print(
    "=" * 70
)

print(
    "REAL MADRID 1990+ DATABASE AUDIT"
)

print(
    "=" * 70
)


print(
    "Database toplam oyuncu:",
    len(players)
)


print(
    "Başlangıç yılı:",
    START_YEAR
)


# ==================================================
# SESSION
# ==================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# ==================================================
# SOURCE OYUNCULAR
# ==================================================

source_players = {}

failed_letters = []


# ==================================================
# A - Z TARAMA
# ==================================================

for letter in string.ascii_uppercase:

    print()

    print(
        "=" * 70
    )

    print(
        "HARF:",
        letter
    )

    print(
        "=" * 70
    )


    url = BASE_URL.format(
        letter=letter
    )


    try:

        response = session.get(
            url,
            timeout=30
        )


        print(
            "HTTP:",
            response.status_code
        )


        response.raise_for_status()


    except Exception as error:

        print(
            "HATA:",
            error
        )


        failed_letters.append(
            letter
        )


        time.sleep(
            WAIT_SECONDS
        )


        continue


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    table = soup.select_one(
        "table.items"
    )


    if not table:

        print(
            "Oyuncu tablosu bulunamadı."
        )


        failed_letters.append(
            letter
        )


        time.sleep(
            WAIT_SECONDS
        )


        continue


    rows = table.select(
        "tbody > tr"
    )


    print(
        "Tablodaki satır:",
        len(rows)
    )


    letter_added = 0

    old_skipped = 0

    unknown_date = 0


    for row in rows:

        player_link = row.select_one(
            'a[href*="/profil/spieler/"]'
        )


        if not player_link:

            continue


        player_name = player_link.get_text(
            " ",
            strip=True
        )


        if not player_name:

            continue


        player_url = player_link.get(
            "href",
            ""
        )


        cells = row.find_all(
            "td",
            recursive=False
        )


        cell_texts = [

            cell.get_text(
                " ",
                strip=True
            )

            for cell in cells

        ]


        # ==================================================
        # "IN THE CLUB UNTIL" TARİHİNİ BUL
        #
        # Detailed görünümde satırdaki tarih değerlerinden
        # sonlara doğru olan kulüpten ayrılış tarihini
        # yakalamaya çalışıyoruz.
        # ==================================================

        date_candidates = []


        for cell_text in cell_texts:

            if re.search(
                r"\b\d{1,2}/\d{1,2}/(?:19|20)\d{2}\b",
                cell_text
            ):

                date_candidates.append(
                    cell_text
                )


        # Detailed tabloda genellikle:
        #
        # Doğum tarihi
        # +
        # In the club until
        #
        # bulunur.
        #
        # Son tarih bu nedenle ayrılış tarihidir.

        end_year = None


        if len(
            date_candidates
        ) >= 2:

            end_year = extract_year(
                date_candidates[-1]
            )


        elif len(
            date_candidates
        ) == 1:

            # Tek tarih varsa bunun DOB olma ihtimali var.
            # O nedenle doğrudan güvenmeyip satır metnine
            # ayrıca bakıyoruz.

            row_text = row.get_text(
                " ",
                strip=True
            )


            # "exp. until" current player anlamına gelebilir.
            if (
                "exp. until" in row_text.lower()
                or
                "real madrid" in row_text.lower()
            ):

                end_year = 9999


        # ==================================================
        # CURRENT PLAYER KONTROLÜ
        # ==================================================

        row_text = row.get_text(
            " ",
            strip=True
        )


        if (
            "exp. until" in row_text.lower()
        ):

            end_year = 9999


        # ==================================================
        # TARİH BULUNAMADI
        # ==================================================

        if end_year is None:

            unknown_date += 1


            # Tarih belirsizse yanlışlıkla silmeyelim.
            # Audit raporuna UNKNOWN olarak alacağız.

            status = "UNKNOWN"


        # ==================================================
        # 1990'DAN ÖNCE BİTMİŞ
        # ==================================================

        elif end_year < START_YEAR:

            old_skipped += 1

            continue


        else:

            status = "1990+"


        normalized_name = normalize(
            player_name
        )


        if normalized_name in source_players:

            continue


        source_players[
            normalized_name
        ] = {

            "name":
                player_name,

            "url":
                player_url,

            "end_year":
                end_year,

            "status":
                status

        }


        letter_added += 1


    print(
        "1990+ / kontrol edilecek yeni oyuncu:",
        letter_added
    )


    print(
        "1990 öncesi atlandı:",
        old_skipped
    )


    print(
        "Tarihi belirsiz:",
        unknown_date
    )


    print(
        "Toplam kaynak havuzu:",
        len(source_players)
    )


    time.sleep(
        WAIT_SECONDS
    )


# ==================================================
# DATABASE İLE KARŞILAŞTIR
# ==================================================

missing = []


for normalized_name, info in source_players.items():

    if normalized_name not in database_names:

        missing.append(
            info
        )


missing.sort(
    key=lambda item:
        normalize(
            item["name"]
        )
)


# ==================================================
# KESİN VE BELİRSİZ AYIR
# ==================================================

confirmed_missing = [

    item

    for item in missing

    if item[
        "status"
    ] == "1990+"

]


unknown_missing = [

    item

    for item in missing

    if item[
        "status"
    ] == "UNKNOWN"

]


# ==================================================
# SONUÇ
# ==================================================

print()

print(
    "=" * 70
)

print(
    "REAL MADRID 1990+ AUDIT SONUCU"
)

print(
    "=" * 70
)


print(
    "1990+ kaynak havuzu:",
    len(source_players)
)


print(
    "Database'de toplam eksik:",
    len(missing)
)


print(
    "1990+ olduğu doğrulanan eksik:",
    len(confirmed_missing)
)


print(
    "Tarihi kontrol edilmesi gereken eksik:",
    len(unknown_missing)
)


# ==================================================
# KESİN EKSİKLER
# ==================================================

print()

print(
    "=" * 70
)

print(
    "1990+ KESİN EKSİK OYUNCULAR"
)

print(
    "=" * 70
)


if not confirmed_missing:

    print(
        "Yok."
    )


for index, info in enumerate(
    confirmed_missing,
    start=1
):

    year_text = (
        "CURRENT"
        if info[
            "end_year"
        ] == 9999
        else str(
            info[
                "end_year"
            ]
        )
    )


    print(
        f"{index}. "
        f"{info['name']} "
        f"| Real Madrid son yıl: "
        f"{year_text}"
    )


# ==================================================
# BELİRSİZLER
# ==================================================

print()

print(
    "=" * 70
)

print(
    "TARİHİ BELİRSİZ EKSİKLER"
)

print(
    "=" * 70
)


if not unknown_missing:

    print(
        "Yok."
    )


for index, info in enumerate(
    unknown_missing,
    start=1
):

    print(
        f"{index}. "
        f"{info['name']}"
    )


# ==================================================
# LUKA MODRIC
# ==================================================

print()

print(
    "=" * 70
)

print(
    "LUKA MODRIC TESTİ"
)

print(
    "=" * 70
)


luka_key = normalize(
    "Luka Modrić"
)


if luka_key in database_names:

    print(
        "Luka Modrić database'de VAR."
    )

else:

    print(
        "Luka Modrić database'de YOK."
    )


if luka_key in source_players:

    print(
        "Luka Modrić 1990+ kaynak havuzunda VAR."
    )

    print(
        "Kayıt:",
        source_players[
            luka_key
        ]
    )

else:

    print(
        "Luka Modrić 1990+ kaynak havuzunda YOK."
    )


# ==================================================
# BAŞARISIZ HARFLER
# ==================================================

print()

print(
    "=" * 70
)

print(
    "BAŞARISIZ HARFLER"
)

print(
    "=" * 70
)


if failed_letters:

    print(
        ", ".join(
            failed_letters
        )
    )

else:

    print(
        "Yok."
    )


# ==================================================
# RAPOR
# ==================================================

REPORT_FILE = (
    "real_madrid_missing_1990.txt"
)


with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "REAL MADRID 1990+ EKSİK OYUNCULAR\n"
    )

    file.write(
        "=" * 70
        +
        "\n\n"
    )


    file.write(
        "KESİN 1990+ EKSİKLER\n"
    )

    file.write(
        "-" * 70
        +
        "\n"
    )


    for index, info in enumerate(
        confirmed_missing,
        start=1
    ):

        year_text = (
            "CURRENT"
            if info[
                "end_year"
            ] == 9999
            else str(
                info[
                    "end_year"
                ]
            )
        )


        file.write(
            f"{index}. "
            f"{info['name']} "
            f"| Son yıl: "
            f"{year_text}\n"
        )


    file.write(
        "\n"
    )


    file.write(
        "TARİHİ BELİRSİZ EKSİKLER\n"
    )

    file.write(
        "-" * 70
        +
        "\n"
    )


    for index, info in enumerate(
        unknown_missing,
        start=1
    ):

        file.write(
            f"{index}. "
            f"{info['name']}\n"
        )


print()

print(
    "Rapor kaydedildi:",
    REPORT_FILE
)


print()

print(
    "AUDIT TAMAMLANDI."
)

print()