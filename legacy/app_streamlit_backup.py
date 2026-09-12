import os as _path_os

SCRIPT_DIR = _path_os.path.dirname(_path_os.path.abspath(__file__))
PROJECT_ROOT = _path_os.path.abspath(_path_os.path.join(SCRIPT_DIR, ".."))
_path_os.chdir(PROJECT_ROOT)
import json
import time
import unicodedata
import os

import streamlit as st


PLAYERS_FILE = "data/players.json"


# ==================================================
# SAYFA
# ==================================================

st.set_page_config(
    page_title="Football Hex",
    page_icon="⚽",
    layout="wide"
)


# ==================================================
# VERİTABANI
# ==================================================

def load_players():

    for attempt in range(10):

        try:

            with open(
                PLAYERS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except json.JSONDecodeError:

            time.sleep(1)

    st.error(
        "players.json şu anda güncelleniyor. "
        "Birkaç saniye sonra tekrar dene."
    )

    st.stop()


players = load_players()


# ==================================================
# NORMALIZE
# ==================================================

def normalize(text):

    text = str(text).strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    return text


# ==================================================
# OYUNCU BUL
# ==================================================

def find_player(name):

    target = normalize(name)

    for player in players:

        if normalize(
            player.get(
                "name",
                ""
            )
        ) == target:

            return player

    return None


# ==================================================
# KULÜPLER
# ==================================================

def get_club_names(player):

    clubs = player.get(
        "clubs",
        []
    )

    names = []

    for club in clubs:

        if isinstance(
            club,
            dict
        ):

            name = club.get(
                "name",
                ""
            )

        else:

            name = str(club)

        if name:

            names.append(name)

    return names


def matches_club(
    player,
    club_name
):

    target = normalize(
        club_name
    )

    for club in get_club_names(
        player
    ):

        current = normalize(
            club
        )

        if (
            target == current
            or target in current
            or current in target
        ):

            return True

    return False


# ==================================================
# MİLLİYET
# ==================================================

def matches_nationality(
    player,
    nationality
):

    return normalize(
        player.get(
            "nationality",
            ""
        )
    ) == normalize(
        nationality
    )


# ==================================================
# KUPA
# ==================================================

def matches_trophy(
    player,
    trophy_name
):

    trophies = player.get(
        "trophies",
        []
    )

    target = normalize(
        trophy_name
    )

    for trophy in trophies:

        current = normalize(
            trophy
        )

        if (
            target == current
            or target in current
            or current in target
        ):

            return True

    return False


# ==================================================
# KRİTER
# ==================================================

def matches_condition(
    player,
    condition
):

    if condition["type"] == "club":

        return matches_club(
            player,
            condition["value"]
        )

    if condition["type"] == "nationality":

        return matches_nationality(
            player,
            condition["value"]
        )

    if condition["type"] == "trophy":

        return matches_trophy(
            player,
            condition["value"]
        )

    return False


# ==================================================
# PETEKLER
# ==================================================

conditions = [

    {
        "label": "BARCELONA",
        "type": "club",
        "value": "FC Barcelona",
        "image": "assets/clubs/barcelona.png"
    },

    {
        "label": "ARGENTINA",
        "type": "nationality",
        "value": "Argentina",
        "image": "assets/flags/argentina.png"
    },

    {
        "label": "REAL MADRID",
        "type": "club",
        "value": "Real Madrid",
        "image": "assets/clubs/real_madrid.png"
    },

    {
        "label": "PORTUGAL",
        "type": "nationality",
        "value": "Portugal",
        "image": "assets/flags/portugal.png"
    },

    {
        "label": "MAN UNITED",
        "type": "club",
        "value": "Manchester United",
        "image": "assets/clubs/man_united.png"
    },

    {
        "label": "JUVENTUS",
        "type": "club",
        "value": "Juventus",
        "image": "assets/clubs/juventus.png"
    },

    {
        "label": "BAYERN",
        "type": "club",
        "value": "Bayern Munich",
        "image": "assets/clubs/bayern.png"
    },

    {
        "label": "GERMANY",
        "type": "nationality",
        "value": "Germany",
        "image": "assets/flags/germany.png"
    },

    {
        "label": "MAN CITY",
        "type": "club",
        "value": "Manchester City",
        "image": "assets/clubs/man_city.png"
    },

    {
        "label": "BRAZIL",
        "type": "nationality",
        "value": "Brazil",
        "image": "assets/flags/brazil.png"
    },

    {
        "label": "PSG",
        "type": "club",
        "value": "Paris Saint-Germain",
        "image": None
    },

    {
        "label": "FRANCE",
        "type": "nationality",
        "value": "France",
        "image": "assets/flags/france.png"
    },

    {
        "label": "LIVERPOOL",
        "type": "club",
        "value": "Liverpool",
        "image": "assets/clubs/liverpool.png"
    },

    {
        "label": "NETHERLANDS",
        "type": "nationality",
        "value": "Netherlands",
        "image": "assets/flags/netherlands.png"
    },

    {
        "label": "AJAX",
        "type": "club",
        "value": "Ajax",
        "image": "assets/clubs/ajax.png"
    },

    {
        "label": "CHELSEA",
        "type": "club",
        "value": "Chelsea",
        "image": "assets/clubs/chelsea.png"
    },

    {
        "label": "SPAIN",
        "type": "nationality",
        "value": "Spain",
        "image": "assets/flags/spain.png"
    },

    {
        "label": "ARSENAL",
        "type": "club",
        "value": "Arsenal",
        "image": "assets/clubs/arsenal.png"
    }

]


# ==================================================
# BOARD
# ==================================================

rows = [

    [0, 1, 2],

    [3, 4, 5, 6],

    [7, 8, "score", 9, 10],

    [11, 12, 13, 14],

    [15, 16, 17]

]


# ==================================================
# KOMŞULUK
# ==================================================

neighbors = {

    0: {1, 3, 4},
    1: {0, 2, 4, 5},
    2: {1, 5, 6},

    3: {0, 4, 7},
    4: {0, 1, 3, 5, 7, 8},
    5: {1, 2, 4, 6, 8},
    6: {2, 5, 10},

    7: {3, 4, 8, 11, 12},
    8: {4, 5, 7, 12, 13},

    9: {6, 10, 13, 14},
    10: {6, 9, 14},

    11: {7, 12, 15},
    12: {7, 8, 11, 13, 15, 16},
    13: {8, 9, 12, 14, 16},
    14: {9, 10, 13, 17},

    15: {11, 12, 16},
    16: {12, 13, 15, 17},
    17: {14, 16}

}


# ==================================================
# SESSION
# ==================================================

if "selected" not in st.session_state:
    st.session_state.selected = None

if "score" not in st.session_state:
    st.session_state.score = 0

if "solved" not in st.session_state:
    st.session_state.solved = {}

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ==================================================
# CSS
# ==================================================

st.markdown(
    """
<style>

.stApp {

    background:
        radial-gradient(
            circle at center,
            #35204f 0%,
            #1b0e2d 58%,
            #09040f 100%
        );

}


.block-container {

    max-width: 1050px;

    padding-top: 15px;

    padding-bottom: 50px;

}


/* ============================================== */
/* BAŞLIK                                         */
/* ============================================== */

.game-title {

    text-align: center;

    color: white;

    font-size: 44px;

    font-weight: 900;

    margin-bottom: 0px;

}


.game-subtitle {

    text-align: center;

    color: #bdb4c8;

    font-size: 15px;

    margin-bottom: 20px;

}


/* ============================================== */
/* BOARD SATIRLARI                                */
/* ============================================== */

div[data-testid="stHorizontalBlock"] {

    gap: 0px !important;

}


/* ============================================== */
/* PETEK KOLONU                                   */
/* ============================================== */

div[data-testid="column"] {

    position: relative;

}


/* ============================================== */
/* LOGO / BAYRAK                                  */
/* ============================================== */

div[data-testid="stImage"] {

    position: absolute;

    top: 25px;

    left: 50%;

    transform: translateX(-50%);

    z-index: 10;

    pointer-events: none;

    width: 68px;

}


div[data-testid="stImage"] img {

    width: 68px !important;

    height: 68px !important;

    object-fit: contain !important;

}


/* ============================================== */
/* PETEK BUTONU                                   */
/* ============================================== */

div[data-testid="stButton"] {

    display: flex;

    justify-content: center;

}


div[data-testid="stButton"] button {

    width: 162px;

    height: 185px;

    min-height: 185px;

    border: 0 !important;

    border-radius: 0 !important;

    clip-path: polygon(
        50% 0%,
        93% 25%,
        93% 75%,
        50% 100%,
        7% 75%,
        7% 25%
    );

    background:
        linear-gradient(
            145deg,
            #f8fafc,
            #dce2eb
        ) !important;

    color: #111827 !important;

    font-size: 13px !important;

    line-height: 1.05 !important;

    font-weight: 900 !important;

    white-space: pre-line !important;

    padding:
        100px
        12px
        17px
        12px !important;

    box-shadow:
        inset 0 0 0 2px
        rgba(
            35,
            22,
            54,
            0.15
        );

    transition:
        transform 0.12s ease,
        filter 0.12s ease;

}


div[data-testid="stButton"] button:hover {

    transform: scale(1.035);

    filter: brightness(1.05);

}


/* ============================================== */
/* SCORE                                          */
/* ============================================== */

.score-hex {

    width: 162px;

    height: 185px;

    margin: auto;

    display: flex;

    flex-direction: column;

    align-items: center;

    justify-content: center;

    clip-path: polygon(
        50% 0%,
        93% 25%,
        93% 75%,
        50% 100%,
        7% 75%,
        7% 25%
    );

    background:
        linear-gradient(
            145deg,
            #4b2b70,
            #180b29
        );

}


.score-title {

    color: #ddd4e8;

    font-size: 16px;

    font-weight: 800;

}


.score-number {

    color: white;

    font-size: 58px;

    line-height: 1;

    font-weight: 900;

}


/* ============================================== */
/* BOARD SATIRLARINI YAKLAŞTIR                    */
/* ============================================== */

.hex-row-gap {

    height: 1px;

    margin-top: -43px;

}


/* ============================================== */
/* CEVAP                                          */
/* ============================================== */

.selected-title {

    text-align: center;

    color: white;

    font-size: 21px;

    font-weight: 900;

    margin-top: 25px;

    margin-bottom: 10px;

}


div[data-testid="stTextInput"] {

    max-width: 580px;

    margin-left: auto;

    margin-right: auto;

}


div[data-testid="stTextInput"] input {

    height: 54px;

    text-align: center;

    font-size: 20px;

}


/* ============================================== */
/* NORMAL ALT BUTONLAR                            */
/* ============================================== */

.action-zone div[data-testid="stButton"] button {

    width: 580px;

    height: 52px;

    min-height: 52px;

    clip-path: none;

    padding: 0 !important;

    border-radius: 12px !important;

    background: white !important;

    font-size: 16px !important;

}


/* ============================================== */
/* MOBİL                                          */
/* ============================================== */

@media (max-width: 800px) {

    div[data-testid="stButton"] button {

        width: 105px;

        height: 120px;

        min-height: 120px;

        font-size: 9px !important;

        padding:
            63px
            5px
            8px
            5px !important;

    }


    div[data-testid="stImage"] {

        top: 17px;

        width: 43px;

    }


    div[data-testid="stImage"] img {

        width: 43px !important;

        height: 43px !important;

    }


    .score-hex {

        width: 105px;

        height: 120px;

    }


    .score-number {

        font-size: 38px;

    }

}

</style>
""",
    unsafe_allow_html=True
)


# ==================================================
# BAŞLIK
# ==================================================

st.markdown(
    """
    <div class="game-title">
        ⚽ FOOTBALL HEX
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown(
    """
    <div class="game-subtitle">
        Bir peteğe tıkla ve uygun futbolcuyu yaz
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# PETEK ÇİZ
# ==================================================

def render_hex(index):

    condition = conditions[
        index
    ]

    image_path = condition.get(
        "image"
    )


    if (
        image_path
        and os.path.exists(
            image_path
        )
    ):

        st.image(
            image_path,
            width=68
        )


    label = condition[
        "label"
    ]


    if index in st.session_state.solved:

        player_name = st.session_state.solved[
            index
        ]

        text = (
            "✅\n"
            + label
            + "\n"
            + player_name
        )


    elif (
        st.session_state.selected
        == index
    ):

        text = (
            "🟡\n"
            + label
        )


    else:

        text = label


    if st.button(
        text,
        key=f"hex_{index}"
    ):

        if index in st.session_state.solved:

            st.session_state.last_result = (
                "Bu petek zaten çözüldü."
            )

        else:

            st.session_state.selected = index

            st.session_state.last_result = None

        st.rerun()


# ==================================================
# BOARD
# ==================================================

for row_number, row in enumerate(
    rows
):


    # ==============================================
    # SATIRLAR ARASINI KAPAT
    # ==============================================

    if row_number > 0:

        st.markdown(
            '<div class="hex-row-gap"></div>',
            unsafe_allow_html=True
        )


    count = len(row)


    # ==============================================
    # 3 PETEK
    # ==============================================

    if count == 3:

        spacer1, c1, c2, c3, spacer2 = st.columns(
            [
                0.9,
                1,
                1,
                1,
                0.9
            ],
            gap="small"
        )

        columns = [
            c1,
            c2,
            c3
        ]


    # ==============================================
    # 4 PETEK
    # ==============================================

    elif count == 4:

        spacer1, c1, c2, c3, c4, spacer2 = st.columns(
            [
                0.42,
                1,
                1,
                1,
                1,
                0.42
            ],
            gap="small"
        )

        columns = [
            c1,
            c2,
            c3,
            c4
        ]


    # ==============================================
    # 5 PETEK
    # ==============================================

    else:

        columns = st.columns(
            5,
            gap="small"
        )


    for column, item in zip(
        columns,
        row
    ):

        with column:


            if item == "score":

                st.markdown(
                    f"""
                    <div class="score-hex">

                        <div class="score-title">
                            SCORE
                        </div>

                        <div class="score-number">
                            {st.session_state.score}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


            else:

                render_hex(
                    item
                )


# ==================================================
# CEVAP
# ==================================================

selected = st.session_state.selected


if selected is None:

    st.markdown(
        """
        <div class="selected-title">
            👆 Cevaplamak istediğin peteğe tıkla
        </div>
        """,
        unsafe_allow_html=True
    )


else:

    condition = conditions[
        selected
    ]


    st.markdown(
        f"""
        <div class="selected-title">
            🟡 {condition["label"]}
        </div>
        """,
        unsafe_allow_html=True
    )


    answer = st.text_input(
        "Futbolcu",
        placeholder="Oyuncunun adını yaz...",
        key=f"answer_{selected}",
        label_visibility="collapsed"
    )


    st.markdown(
        '<div class="action-zone">',
        unsafe_allow_html=True
    )


    check_clicked = st.button(
        "⚽ CEVABI KONTROL ET",
        key="check_answer"
    )


    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


    if check_clicked:


        if not answer:

            st.warning(
                "Bir futbolcu adı yaz."
            )


        else:

            player = find_player(
                answer
            )


            # ==========================================
            # OYUNCU YOK
            # ==========================================

            if not player:

                st.error(
                    "❌ Oyuncu veritabanında bulunamadı."
                )


            # ==========================================
            # PETEK YANLIŞ
            # ==========================================

            elif not matches_condition(
                player,
                condition
            ):

                st.error(
                    f"❌ {player['name']} "
                    f"{condition['label']} "
                    f"şartını karşılamıyor."
                )


            # ==========================================
            # DOĞRU
            # ==========================================

            else:

                newly_solved = []


                # ANA PETEK

                if (
                    selected
                    not in st.session_state.solved
                ):

                    st.session_state.solved[
                        selected
                    ] = player[
                        "name"
                    ]

                    newly_solved.append(
                        selected
                    )


                # KOMŞU PETEKLER

                for neighbor in neighbors.get(
                    selected,
                    set()
                ):

                    if (
                        neighbor
                        in st.session_state.solved
                    ):

                        continue


                    neighbor_condition = conditions[
                        neighbor
                    ]


                    if matches_condition(
                        player,
                        neighbor_condition
                    ):

                        st.session_state.solved[
                            neighbor
                        ] = player[
                            "name"
                        ]

                        newly_solved.append(
                            neighbor
                        )


                # SKOR

                st.session_state.score += len(
                    newly_solved
                )


                automatic = [

                    index

                    for index in newly_solved

                    if index != selected

                ]


                if automatic:

                    automatic_names = [

                        conditions[index][
                            "label"
                        ]

                        for index in automatic

                    ]


                    st.session_state.last_result = (

                        "🔥 "
                        + player["name"]
                        + " doğru! Ayrıca "
                        + ", ".join(
                            automatic_names
                        )
                        + " otomatik çözüldü."

                    )


                else:

                    st.session_state.last_result = (

                        "✅ "
                        + player["name"]
                        + " doğru!"

                    )


                st.session_state.selected = None

                st.rerun()


# ==================================================
# SONUÇ
# ==================================================

if st.session_state.last_result:

    st.success(
        st.session_state.last_result
    )


# ==================================================
# İLERLEME
# ==================================================

solved_count = len(
    st.session_state.solved
)


st.write("")


st.progress(
    solved_count
    / len(conditions)
)


st.markdown(
    f"""
    <div style="
        text-align:center;
        color:white;
        font-weight:800;
        margin-top:7px;
        margin-bottom:18px;
    ">
        🏆 {solved_count} / {len(conditions)} petek
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# RESET
# ==================================================

st.markdown(
    '<div class="action-zone">',
    unsafe_allow_html=True
)


reset_clicked = st.button(
    "🔄 OYUNU SIFIRLA",
    key="reset"
)


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


if reset_clicked:

    st.session_state.selected = None

    st.session_state.score = 0

    st.session_state.solved = {}

    st.session_state.last_result = None

    st.rerun()