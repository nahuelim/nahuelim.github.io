"""mapa.py — única fuente del mapa de las fichas (auto_ficha.py y generate.py).

Geocodifica calle + altura (sin barrio comercial), valida que Google devolvió la
MISMA calle y número, y embebe por coordenadas. Si algo no cuadra: ficha sin mapa
y un aviso (un mapa ausente es mejor que un mapa equivocado).

Verificación real (usa la API key):  python3 mapa.py "Pumacahua 200" "Caballito Sur"
Self-check offline (sin red):        python3 mapa.py
"""
import difflib
import json
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

KEY_FILE = Path.home() / "Documents" / "2. Inmobiliaria" / ".maps_api_key"
URL = "https://maps.googleapis.com/maps/api/geocode/json"
BBOX = (-34.705, -34.526, -58.532, -58.335)  # lat_min, lat_max, lng_min, lng_max de CABA
PRECISOS = {"ROOFTOP", "RANGE_INTERPOLATED"}  # APPROXIMATE / GEOMETRIC_CENTER no sirven para un pin
ABREV = {"gral": "general", "cnel": "coronel", "dr": "doctor", "dra": "doctora", "pte": "presidente",
         "pres": "presidente", "tte": "teniente", "cap": "capitan", "ing": "ingeniero",
         "mtro": "maestro", "alte": "almirante", "gdor": "gobernador", "sgto": "sargento"}
BARRIOS_CABA = set((  # 48 oficiales + nombres comerciales de uso común (sin acentos)
    "agronomia,almagro,balvanera,barracas,belgrano,boedo,caballito,chacarita,coghlan,colegiales,constitucion,"
    "flores,floresta,la boca,la paternal,liniers,mataderos,monte castro,montserrat,nueva pompeya,nunez,palermo,"
    "parque avellaneda,parque chacabuco,parque chas,parque patricios,puerto madero,recoleta,retiro,saavedra,"
    "san cristobal,san nicolas,san telmo,velez sarsfield,versalles,villa crespo,villa del parque,villa devoto,"
    "villa general mitre,villa lugano,villa luro,villa ortuzar,villa pueyrredon,villa real,villa riachuelo,"
    "villa santa rita,villa soldati,villa urquiza,barrio norte,las canitas,abasto,once,microcentro,catalinas,"
    "tribunales,congreso,caba,capital federal,ciudad autonoma de buenos aires").split(","))
IGNORAR = {"av", "avenida", "calle", "pasaje", "pje", "de", "del", "la", "las", "los", "y", "el"}


def _clave():
    return KEY_FILE.read_text().strip()


def _fetch(direccion_q, key, caba=True):
    p = {"address": direccion_q, "components": "country:AR", "region": "ar", "language": "es", "key": key}
    if caba:
        p["bounds"] = f"{BBOX[0]},{BBOX[2]}|{BBOX[1]},{BBOX[3]}"
    try:
        import requests
        return requests.get(URL, params=p, timeout=10).json()
    except ImportError:  # generate.py vía publicar.sh puede correr sin requests
        from urllib.parse import urlencode
        from urllib.request import urlopen
        return json.load(urlopen(f"{URL}?{urlencode(p)}", timeout=10))


def _tokens(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return {w for w in (ABREV.get(w, w) for w in re.findall(r"[a-z0-9]+", s)) if w not in IGNORAR}


def _es_caba(barrio):
    """CABA por defecto: barrio vacío o reconocido. Cualquier otro lugar (Olivos, Lomas, La Plata) = fuera de CABA."""
    n = " ".join(re.findall(r"[a-z0-9]+", "".join(
        c for c in unicodedata.normalize("NFD", barrio.lower()) if unicodedata.category(c) != "Mn")))
    return not n or any(f" {b} " in f" {n} " for b in BARRIOS_CABA)


def _coincide(pedida, devuelta):
    """Cada palabra de la calle pedida está (casi) en la devuelta; tolera typos tipo Puyrredon/Pueyrredón."""
    td = _tokens(devuelta)
    ini = {w[0] for w in td}  # "J. B. Alberdi" == "Juan Bautista Alberdi"
    return all(w in td or (len(w) == 1 and w in ini) or difflib.get_close_matches(w, td, 1, 0.85)
               for w in _tokens(pedida))


def _parse(direccion):
    """'Pumacahua al 200' -> ('Pumacahua', 200). 'al' se ignora. (None, None) si no hay calle+altura."""
    d = re.split(r"\s+-\s+|,", direccion)[0]
    d = re.sub(r"\bal\s+(\d+)", r"\1", d, flags=re.I).strip(" .")
    m = re.match(r"^(.+?)\s+(\d{1,5})$", d)
    return (m.group(1).strip(" ."), int(m.group(2))) if m else (None, None)


_RECHAZADOS = {}  # ponytail: (direccion, barrio) -> coords que Google dio pero no pasaron la validación; para que el usuario decida


@lru_cache(maxsize=256)
def geocodificar(direccion, barrio=""):
    """-> ((lat, lng) | None, aviso). Sin coordenadas = no hay mapa. aviso != '' = algo para revisar."""
    calle, num = _parse(direccion)
    if not calle:
        return None, f"No pude leer calle y altura de «{direccion}»."
    try:
        key = _clave()
    except OSError:
        return None, f"No encontré la API key en {KEY_FILE}."
    try:
        caba = _es_caba(barrio)
        lugar = "Ciudad Autónoma de Buenos Aires" if caba else barrio
        r = _fetch(f"{calle} {num}, {lugar}, Argentina", key, caba)
    except Exception as e:
        return None, f"No pude consultar Google ({e.__class__.__name__})."
    if r.get("status") != "OK":
        return None, f"Google respondió {r.get('status')}: {r.get('error_message', '')}".strip()

    x = r["results"][0]
    comp = {t: c["long_name"] for c in x["address_components"] for t in c["types"]}
    loc = x["geometry"]["location"]
    mal = []
    if x.get("partial_match"):
        mal.append("coincidencia parcial")
    if not _coincide(calle, comp.get("route", "")):
        mal.append(f"calle distinta a «{calle}»")
    if comp.get("street_number") != str(num):
        mal.append(f"altura distinta a {num}")
    if x["geometry"]["location_type"] not in PRECISOS:
        mal.append(f"ubicación imprecisa ({x['geometry']['location_type']})")
    if caba and not (BBOX[0] <= loc["lat"] <= BBOX[1] and BBOX[2] <= loc["lng"] <= BBOX[3]):
        mal.append("fuera de CABA")
    if mal:
        _RECHAZADOS[(direccion, barrio)] = (loc["lat"], loc["lng"])
        return None, f"Sin mapa: Google devolvió «{x['formatted_address']}» ({', '.join(mal)})."

    # ponytail: solo advertencia; el barrio comercial (Caballito Sur, Barrio Norte) no es oficial, no puede bloquear
    barrio_g = comp.get("neighborhood") or comp.get("sublocality_level_1") or comp.get("sublocality") or ""
    if barrio and barrio_g and not (_tokens(barrio) & _tokens(barrio_g)):
        return (loc["lat"], loc["lng"]), f"El mapa cae en {barrio_g} y la ficha dice {barrio}. Revisá."
    return (loc["lat"], loc["lng"]), ""


def candidato(direccion, barrio=""):
    """Coords validadas, o las que Google dio y no pasaron la validación (hay que mostrarlas al usuario). None si no hay."""
    coords, _ = geocodificar(direccion, barrio)
    return coords or _RECHAZADOS.get((direccion, barrio))


def mapa_iframe(direccion, barrio="", forzar=False):
    """HTML del <iframe> del mapa, o '' si no se pudo validar. forzar=True: usa el candidato aunque no valide (el usuario lo aprobó)."""
    coords, aviso = geocodificar(direccion, barrio)
    if forzar and not coords:
        coords = candidato(direccion, barrio)
    if aviso:
        print(f"[mapa] {direccion}: {aviso}", flush=True)
    if not coords:
        return ""
    return (f'<iframe src="https://maps.google.com/maps?q={coords[0]:.6f},{coords[1]:.6f}&z=17&output=embed" '
            'allowfullscreen loading="lazy" title="Ubicación"></iframe>')


def _selfcheck():
    global _fetch, _clave
    real = (_fetch, _clave)
    _clave = lambda: "x"

    def google(route, num, lt="ROOFTOP", partial=False, lat=-34.62, lng=-58.43, barrio="Caballito"):
        comps = [{"long_name": route, "types": ["route"]}, {"long_name": str(num), "types": ["street_number"]},
                 {"long_name": barrio, "types": ["neighborhood", "political"]}]
        res = {"formatted_address": f"{route} {num}", "address_components": comps,
               "geometry": {"location": {"lat": lat, "lng": lng}, "location_type": lt}}
        if partial:
            res["partial_match"] = True
        return {"status": "OK", "results": [res]}

    vistas = []

    def caso(resp, direccion="Pumacahua al 200", barrio="Caballito Sur"):
        geocodificar.cache_clear()
        globals()["_fetch"] = lambda q, k, caba=True: (vistas.append((q, caba)), resp)[1]
        return geocodificar(direccion, barrio)

    try:
        assert _parse("Pumacahua al 200") == ("Pumacahua", 200)
        assert _parse("Guatemala 4551 - Torre Esmeralda - Palermo Soho") == ("Guatemala", 4551)
        assert _parse("CHARCAS 5100.") == ("CHARCAS", 5100)
        assert _parse("Curapaligüe  400") == ("Curapaligüe", 400)
        assert _parse("Av. 9 de Julio 1000") == ("Av. 9 de Julio", 1000)
        assert _parse("Rivadavia") == (None, None)
        assert _coincide("Honorio Puyrredon", "Avenida Honorio Pueyrredón")
        assert _coincide("Gral. Urquiza", "General Urquiza")
        assert not _coincide("Pumacahua", "Calasanz")
        assert _coincide("Av. J. B. Alberdi", "Avenida Juan Bautista Alberdi")
        assert not _coincide("Av. J. B. Alberdi", "Avenida Rivadavia")
        for b in ("", "Caballito Sur", "Palermo Soho", "Barrio Norte", "Villa Crespo", "Villa del Parque", "Flores Norte", "CABA"):
            assert _es_caba(b), b
        for b in ("Olivos", "Vicente López", "La Plata", "Villa Ballester", "San Isidro", "Lomas de Zamora"):
            assert not _es_caba(b), b

        c, a = caso(google("Avenida Pumacahua", 200))
        assert c and not a, (c, a)                                     # el caso feliz
        c, a = caso(google("Calasanz", 700, lat=-34.61, lng=-58.44))
        assert c is None and "calle distinta" in a, (c, a)             # EL bug: Pumacahua 200 -> Calasanz 700
        assert candidato("Pumacahua al 200", "Caballito Sur") == (-34.61, -58.44)  # el rechazado queda disponible para confirmar
        assert 'q=-34.610000,-58.440000' in mapa_iframe("Pumacahua al 200", "Caballito Sur", forzar=True)
        assert mapa_iframe("Pumacahua al 200", "Caballito Sur") == ""
        assert caso(google("Pumacahua", 700))[0] is None               # altura distinta
        assert caso(google("Pumacahua", 200, partial=True))[0] is None
        assert caso(google("Pumacahua", 200, lt="APPROXIMATE"))[0] is None
        assert caso(google("Pumacahua", 200, lat=-34.9, lng=-57.9))[0] is None  # La Plata
        c, a = caso({"status": "REQUEST_DENIED", "error_message": "referrer restriction"})
        assert c is None and "REQUEST_DENIED" in a, (c, a)
        c, a = caso(google("Pumacahua", 200, barrio="Flores"))
        assert c and "Revisá" in a, (c, a)                             # coords OK, barrio sospechoso
        c, a = caso(google("Pumacahua", 200))
        assert c and vistas[-1] == ("Pumacahua 200, Ciudad Autónoma de Buenos Aires, Argentina", True), vistas[-1]
        c, a = caso(google("Libertador", 1000, lat=-34.51, lng=-58.49, barrio="Olivos"), "Libertador 1000", "Olivos")
        assert c and vistas[-1] == ("Libertador 1000, Olivos, Argentina", False), (c, a, vistas[-1])  # fuera de CABA
        c, a = caso(google("Calle 50", 100, lat=-34.92, lng=-57.95, barrio="La Plata"), "Calle 50 al 100", "La Plata")
        assert c, (c, a)                                               # La Plata cae fuera del bbox y se acepta igual
        assert caso(google("Pumacahua", 200))[0] and mapa_iframe("Pumacahua al 200", "Caballito Sur") != ""
        assert mapa_iframe("Rivadavia") == ""
    finally:
        _fetch, _clave = real
        geocodificar.cache_clear()
    print("mapa.py: self-check OK")


if __name__ == "__main__":
    if len(sys.argv) > 1:  # verificación real contra Google
        coords, aviso = geocodificar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
        print("coords:", coords, "\naviso: ", aviso or "(ninguno)")
    else:
        _selfcheck()
