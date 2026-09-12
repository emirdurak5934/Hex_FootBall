"""Historical top-flight club names used by league criteria.

Only senior men's first teams belong here. Membership means that the club has
played in the named top division at some point; player-season overlap is not
available in players.json and is therefore intentionally not inferred.
"""


def _clubs(names):
    return {name: [] for name in names}


LEAGUE_CLUB_ALIASES = {
    "Premier League": _clubs([
        "Arsenal", "Aston Villa", "Barnsley", "Birmingham City", "Blackburn Rovers",
        "Blackpool", "Bolton Wanderers", "AFC Bournemouth", "Bradford City", "Brentford",
        "Brighton & Hove Albion", "Burnley", "Cardiff City", "Charlton Athletic", "Chelsea",
        "Coventry City", "Crystal Palace", "Derby County", "Everton", "Fulham",
        "Huddersfield Town", "Hull City", "Ipswich Town", "Leeds United", "Leicester City",
        "Liverpool", "Luton Town", "Manchester City", "Manchester United", "Middlesbrough",
        "Newcastle United", "Norwich City", "Nottingham Forest", "Oldham Athletic",
        "Portsmouth", "Queens Park Rangers", "Reading", "Sheffield United",
        "Sheffield Wednesday", "Southampton", "Stoke City", "Sunderland", "Swansea City",
        "Swindon Town", "Tottenham Hotspur", "Watford", "West Bromwich Albion",
        "West Ham United", "Wigan Athletic", "Wimbledon", "Wolverhampton Wanderers",
    ]),
    "La Liga": _clubs([
        "Athletic Bilbao", "Atletico Madrid", "Barcelona", "Real Madrid", "Sevilla",
        "Valencia", "Villarreal", "Real Sociedad", "Real Betis", "Espanyol", "Celta Vigo",
        "Deportivo La Coruna", "Real Zaragoza", "Real Valladolid", "Osasuna", "Getafe",
        "Mallorca", "Las Palmas", "Rayo Vallecano", "Granada", "Levante", "Alaves",
        "Girona", "Leganes", "Elche", "Cadiz", "Eibar", "Almeria", "Malaga",
        "Racing Santander", "Sporting Gijon", "Real Oviedo", "Tenerife", "Recreativo Huelva",
        "Hercules", "Cordoba", "Numancia", "Albacete", "Burgos", "Sabadell",
        "Castellon", "Logrones", "Salamanca", "Compostela", "Extremadura", "Merida",
        "Pontevedra", "Real Murcia", "Gimnastic Tarragona", "Xerez", "Huesca",
    ]),
    "Serie A": _clubs([
        "AC Milan", "Inter Milan", "Juventus", "AS Roma", "Napoli", "Atalanta", "Lazio",
        "Fiorentina", "Bologna", "Torino", "Genoa", "Sampdoria", "Udinese", "Parma",
        "Cagliari", "Hellas Verona", "Chievo Verona", "Palermo", "Bari", "Brescia",
        "Empoli", "Lecce", "Sassuolo", "Monza", "Como", "Venezia", "Spezia", "Cremonese",
        "Frosinone", "Salernitana", "Benevento", "Crotone", "Carpi", "Cesena", "Pescara",
        "Siena", "Livorno", "Reggina", "Perugia", "Piacenza", "Vicenza", "Modena",
        "Mantova", "SPAL", "Triestina", "Novara", "Pro Vercelli", "Padova", "Pisa",
        "Catanzaro", "Avellino", "Ascoli", "Ancona", "Messina", "Treviso",
    ]),
    "Bundesliga": _clubs([
        "Bayern Munich", "Borussia Dortmund", "VfB Stuttgart", "Schalke 04",
        "TSG 1899 Hoffenheim", "Bayer 04 Leverkusen", "RB Leipzig", "VfL Wolfsburg",
        "Eintracht Frankfurt", "Borussia Monchengladbach", "Werder Bremen", "Hamburger SV",
        "Hertha BSC", "1. FC Koln", "1. FSV Mainz 05", "SC Freiburg", "FC Augsburg",
        "1. FC Union Berlin", "VfL Bochum", "1. FC Nurnberg", "Hannover 96",
        "Fortuna Dusseldorf", "Arminia Bielefeld", "1. FC Kaiserslautern", "Karlsruher SC",
        "MSV Duisburg", "SpVgg Greuther Furth", "SV Darmstadt 98", "FC St. Pauli",
        "Holstein Kiel", "1. FC Heidenheim", "SC Paderborn 07", "FC Ingolstadt 04",
        "Eintracht Braunschweig", "TSV 1860 Munich", "Hansa Rostock", "Energie Cottbus",
        "SpVgg Unterhaching", "SV Waldhof Mannheim", "Dynamo Dresden", "Alemannia Aachen",
        "KFC Uerdingen 05", "Kickers Offenbach", "Rot-Weiss Essen", "Rot-Weiss Oberhausen",
        "SG Wattenscheid 09", "1. FC Saarbrucken", "Preussen Munster", "Wuppertaler SV",
        "Fortuna Koln", "Tennis Borussia Berlin", "Blau-Weiss 90 Berlin", "Tasmania Berlin",
    ]),
    "Süper Lig": _clubs([
        "Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor", "Adana Demirspor",
        "Adanaspor", "Alanyaspor", "Altay", "Altinordu", "Ankaragucu", "Antalyaspor",
        "Balikesirspor", "Basaksehir", "Boluspor", "Bursaspor", "Caykur Rizespor",
        "Denizlispor", "Diyarbakirspor", "Elazigspor", "Erzurumspor", "Eskisehirspor",
        "Eyupspor", "Fatih Karagumruk", "Gaziantep FK", "Gaziantepspor", "Genclerbirligi",
        "Giresunspor", "Goztepe", "Hatayspor", "Istanbulspor", "Karabukspor", "Kasimpasa",
        "Kayserispor", "Kocaelispor", "Konyaspor", "Malatyaspor", "Manisaspor", "Mersin Idman Yurdu",
        "Orduspor", "Osmanlispor", "Pendikspor", "Sakaryaspor", "Samsunspor", "Sanliurfaspor",
        "Sariyer", "Sebatspor", "Sivasspor", "Yeni Malatyaspor", "Zeytinburnuspor",
    ]),
}


# Conservative official/local/short variants. Generic city-only aliases are
# included only where they are unambiguous inside the supported league set.
ALIASES = {
    "Arsenal": ["Arsenal FC", "Arsenal F.C."], "Aston Villa": ["Aston Villa FC"],
    "Brighton & Hove Albion": ["Brighton and Hove Albion", "Brighton"],
    "Everton": ["Everton FC", "Everton F.C."], "Fulham": ["Fulham FC", "Fulham F.C."],
    "West Ham United": ["West Ham United FC", "West Ham United F.C."],
    "Liverpool": ["Liverpool FC", "Liverpool F.C."],
    "Manchester United": ["Manchester United FC", "Manchester United F.C."],
    "Manchester City": ["Manchester City FC", "Manchester City F.C."],
    "Tottenham Hotspur": ["Tottenham", "Tottenham Hotspur FC"],
    "Queens Park Rangers": ["Queens Park Rangers F.C.", "QPR"],
    "Wolverhampton Wanderers": ["Wolverhampton Wanderers FC", "Wolves"],
    "Atletico Madrid": ["Atlético Madrid", "Club Atlético de Madrid"],
    "Barcelona": ["FC Barcelona"], "Real Madrid": ["Real Madrid CF", "Real Madrid Club de Fútbol"],
    "Athletic Bilbao": ["Athletic Club"], "Espanyol": ["RCD Espanyol", "RCD Espanyol de Barcelona"],
    "Celta Vigo": ["RC Celta de Vigo"],
    "Valencia": ["Valencia CF"], "Sevilla": ["Sevilla FC", "Sevilla F.C."],
    "Deportivo La Coruna": ["Deportivo La Coruña", "Deportivo de A Coruña", "RC Deportivo"],
    "Real Betis": ["Real Betis Balompié"], "Mallorca": ["RCD Mallorca"],
    "AC Milan": ["A.C. Milan", "Milan"], "Inter Milan": ["Inter", "Internazionale", "FC Internazionale Milano"],
    "AS Roma": ["A.S. Roma", "Roma"], "Napoli": ["SSC Napoli"], "Juventus": ["Juventus FC"],
    "Fiorentina": ["ACF Fiorentina"], "Torino": ["Torino FC"],
    "Genoa": ["Genoa CFC"], "Sampdoria": ["UC Sampdoria", "U.C. Sampdoria"],
    "Lazio": ["SS Lazio", "S.S. Lazio"], "Atalanta": ["Atalanta BC", "Atalanta B.C."],
    "Udinese": ["Udinese Calcio"], "Cagliari": ["Cagliari Calcio"],
    "Bologna": ["Bologna FC 1909", "Bologna F.C. 1909"],
    "Pescara": ["Delfino Pescara 1936"], "Bari": ["SSC Bari", "S.S.C. Bari"],
    "Monza": ["AC Monza", "A.C. Monza"], "Lecce": ["US Lecce", "U.S. Lecce"],
    "Como": ["Como 1907"], "Perugia": ["AC Perugia Calcio", "A.C. Perugia Calcio"],
    "Siena": ["Siena FC", "AC Siena"], "Brescia": ["Brescia Calcio"],
    "Hellas Verona": ["Hellas Verona FC"], "Parma": ["Parma Calcio 1913", "Parma FC"],
    "Bayern Munich": ["FC Bayern Munich", "Bayern München", "FC Bayern München"],
    "Borussia Dortmund": ["BVB", "BV Borussia 09 Dortmund"], "VfB Stuttgart": ["Stuttgart"],
    "Schalke 04": ["FC Schalke 04", "Schalke"],
    "TSG 1899 Hoffenheim": ["TSG Hoffenheim", "Hoffenheim"],
    "Bayer 04 Leverkusen": ["Bayer Leverkusen"], "Werder Bremen": ["SV Werder Bremen"],
    "Borussia Monchengladbach": ["Borussia Mönchengladbach", "Borussia Moenchengladbach"],
    "1. FC Koln": ["1. FC Köln", "FC Köln", "FC Cologne"],
    "1. FC Nurnberg": ["1. FC Nürnberg", "FC Nürnberg"],
    "Fortuna Dusseldorf": ["Fortuna Düsseldorf"], "SpVgg Greuther Furth": ["SpVgg Greuther Fürth"],
    "1. FC Saarbrucken": ["1. FC Saarbrücken"], "Preussen Munster": ["Preußen Münster"],
    "Galatasaray": ["Galatasaray SK", "Galatasaray S.K."],
    "Fenerbahce": ["Fenerbahçe", "Fenerbahçe SK", "Fenerbahçe Istanbul"],
    "Besiktas": ["Beşiktaş", "Beşiktaş JK", "Beşiktaş J.K. (Football)"],
    "Trabzonspor": ["Trabzonspor Kulübü"], "Ankaragucu": ["MKE Ankaragücü"],
    "Caykur Rizespor": ["Çaykur Rizespor"], "Genclerbirligi": ["Gençlerbirliği", "Gençlerbirliği S.K."],
    "Goztepe": ["Göztepe", "Göztepe S.K."], "Basaksehir": ["İstanbul Başakşehir", "Istanbul Basaksehir FK"],
    "Kasimpasa": ["Kasımpaşa", "Kasımpaşa S.K."], "Konyaspor": ["Torku Konyaspor"],
    "Sanliurfaspor": ["Şanlıurfaspor"], "Sivasspor": ["Sivasspor Kulübü"],
}

for league_clubs in LEAGUE_CLUB_ALIASES.values():
    for canonical in league_clubs:
        league_clubs[canonical].extend(ALIASES.get(canonical, []))

# Exact official suffix variants are safe: they never strip reserve, academy,
# age-group or women's markers and therefore cannot promote those teams.
for canonical, aliases in LEAGUE_CLUB_ALIASES["Premier League"].items():
    aliases.extend([f"{canonical} FC", f"{canonical} F.C."])
for canonical, aliases in LEAGUE_CLUB_ALIASES["La Liga"].items():
    aliases.extend([f"{canonical} CF", f"{canonical} C.F."])
for canonical, aliases in LEAGUE_CLUB_ALIASES["Süper Lig"].items():
    aliases.extend([f"{canonical} SK", f"{canonical} S.K."])

LEAGUE_CLUB_ALIASES["Premier League"]["Sunderland"].extend(["Sunderland AFC", "Sunderland A.F.C."])
LEAGUE_CLUB_ALIASES["Premier League"]["AFC Bournemouth"].append("A.F.C. Bournemouth")


LEGACY_LEAGUE_CLUBS = {
    "Premier League": ["Arsenal", "Liverpool", "Manchester United", "Manchester City", "Tottenham Hotspur", "Newcastle United", "Chelsea"],
    "La Liga": ["Sevilla", "Atletico Madrid", "Barcelona", "Real Madrid"],
    "Serie A": ["AC Milan", "Inter Milan", "AS Roma", "Napoli", "Juventus"],
    "Bundesliga": ["Bayern Munich", "Borussia Dortmund"],
    "Süper Lig": ["Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor"],
}
