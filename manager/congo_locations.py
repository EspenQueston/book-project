"""Signup location data: Republic of Congo departments/districts, plus the
full set of countries offered at sign-up for users and vendors — every
country PawaPay operates in (per pawapay.io's own supported-country list,
a broader set than the handful this account's COUNTRY_CORRESPONDENTS/
COUNTRY_CURRENCY in manager/payments/pawapay.py currently has live payment
routing configured for), plus France, Turkey, and China for
diaspora/international sign-ups.

Congo keeps its richer department → district cascade (real administrative
divisions). Every other country uses a flat list of major cities, reusing
the exact same lists already trusted for checkout in
book_Project/checkout_cities.py, so the two stay consistent.

Note: sign-up accepting a country here does not by itself mean checkout
can process a payment from it — that's governed separately by
manager/payments/pawapay.py's COUNTRY_CORRESPONDENTS/COUNTRY_CURRENCY
(Central Africa only, as of this writing) and book_Project/payment_config.py
(KKiaPay's West Africa list). A user from, say, Kenya or Nigeria can sign
up today; enabling them to actually pay is a separate, follow-up change.
"""

DEFAULT_CONGO_LOCATION = 'Brazzaville'
DEFAULT_CONGO_CITY = 'Makélékélé'
DEFAULT_COUNTRY = 'Congo'

CONGO_DEPARTMENTS = [
    {'code': 'Brazzaville', 'name': 'Brazzaville', 'chef_lieu': 'Makélékélé', 'cities': [
        'Makélékélé', 'Bacongo', 'Poto-Poto', 'Moungali', 'Ouenzé',
        'Talangaï', 'Mfilou', 'Madibou', 'Djiri', 'Djiri-Kintélé',
    ]},
    {'code': 'Pointe-Noire', 'name': 'Pointe-Noire', 'chef_lieu': 'Lumumba', 'cities': [
        'Lumumba', 'Mvou-Mvou', 'Tié-Tié', 'Loandjili', 'Mongo-Mpoukou', 'Ngoyo',
    ]},
    {'code': 'Bouenza', 'name': 'Bouenza', 'chef_lieu': 'Madingou', 'cities': [
        'Madingou', 'Nkayi', 'Loudima', 'Mouyondzi', 'Boko-Songho', 'Kayes',
        'Bouansa', 'Kingoué', 'Mabombo', 'Mfouati', 'Tsiaki', 'Yamba',
    ]},
    {'code': 'Niari', 'name': 'Niari', 'chef_lieu': 'Dolisie', 'cities': [
        'Dolisie', 'Mossendjo', 'Kimongo', 'Banda', 'Divénié', 'Kibangou',
        'Londéla-Kayes', 'Louvakou', 'Mbinda', 'Makabana', 'Moungoundou Nord',
        'Moungoundou Sud', 'Moutamba', 'Mayoko', 'Nyanga', 'Yaya',
    ]},
    {'code': 'Pool', 'name': 'Pool', 'chef_lieu': 'Kinkala', 'cities': [
        'Kinkala', 'Kindamba', 'Mindouli', 'Boko', 'GomaTséTsé', 'Louingui',
        'Loumo', 'Mbandza-Ndounga',
    ]},
    {'code': 'Plateaux', 'name': 'Plateaux', 'chef_lieu': 'Djambala', 'cities': [
        'Djambala', 'Gamboma', 'Lekana', 'Mbon', 'Mpouya', 'Bouemba', 'Ngo',
    ]},
    {'code': 'Cuvette', 'name': 'Cuvette', 'chef_lieu': 'Owando', 'cities': [
        'Owando', 'Makoua', 'Mossaka', 'Boundji', 'Ngoko', 'Ntokou', 'Oyo', 'Tchikapika',
    ]},
    {'code': 'Cuvette-Ouest', 'name': 'Cuvette-Ouest', 'chef_lieu': 'Ewo', 'cities': [
        'Ewo', 'Kéllé', 'Etoumbi', 'Mbama', 'Mbomo', 'Okoyo',
    ]},
    {'code': 'Sangha', 'name': 'Sangha', 'chef_lieu': 'Ouésso', 'cities': [
        'Ouésso', 'Sembé', 'Souanké', 'Pokola', 'Mokéko', 'Ngbala', 'Pikounda',
    ]},
    {'code': 'Likouala', 'name': 'Likouala', 'chef_lieu': 'Impfondo', 'cities': [
        'Impfondo', 'Epéna', 'Dongou', 'Bétou', 'Bouanela', 'Enyellé',
    ]},
    {'code': 'Kouilou', 'name': 'Kouilou', 'chef_lieu': 'Loango', 'cities': [
        'Loango', 'Hinda', 'Kakamoéka', 'Madingo-Kayes', 'Mvouti', 'Nzambi',
    ]},
    {'code': 'Lékoumou', 'name': 'Lékoumou', 'chef_lieu': 'Sibiti', 'cities': [
        'Sibiti', 'Komono', 'Zanaga', 'Bambama', 'Mayéyé',
    ]},
    {'code': 'Congo-Oubangui', 'name': 'Congo-Oubangui', 'chef_lieu': 'Mossaka', 'cities': [
        'Mossaka', 'Loukoléla', 'Bokoma', 'Liranga',
    ]},
    {'code': 'Nkéni-Alima', 'name': 'Nkéni-Alima', 'chef_lieu': 'Gamboma', 'cities': [
        'Gamboma', 'Abala', 'Allembé', 'Makotipoko', 'Ollombo', 'Ongoni',
    ]},
    {'code': 'Djoué-Léfini', 'name': 'Djoué-Léfini', 'chef_lieu': 'Odziba', 'cities': [
        'Odziba', 'Mayama', 'Igné', 'Kimba', 'Ngabé', 'Vindza',
    ]},
    {'code': 'Internationale', 'name': 'Internationale', 'chef_lieu': 'Autres', 'cities': [
        'Chine', 'France', 'Grèce', 'Autres',
    ]},
]

CONGO_DEPARTMENT_CHOICES = [(d['code'], d['name']) for d in CONGO_DEPARTMENTS]

_DEPT_BY_CODE = {d['code']: d for d in CONGO_DEPARTMENTS}


# ---------------------------------------------------------------------------
# Countries offered at sign-up. Congo is first (the platform's home market)
# and uses the department cascade above instead of a flat city list. The
# rest reuse book_Project/checkout_cities.py's per-country city lists so
# signup and checkout never disagree about what "a city in Cameroon" means.
# ---------------------------------------------------------------------------
SIGNUP_COUNTRY_ORDER = [
    'Congo',
    # Central Africa
    'Democratic Republic of the Congo',
    'Cameroon',
    'Gabon',
    'Angola',
    'Chad',
    'Central African Republic',
    'Equatorial Guinea',
    'São Tomé and Príncipe',
    # West Africa
    'Benin',
    'Burkina Faso',
    "Côte d'Ivoire",
    'Ghana',
    'Nigeria',
    'Senegal',
    'Sierra Leone',
    # East / Southern Africa
    'Kenya',
    'Uganda',
    'Tanzania',
    'Rwanda',
    'Zambia',
    'Malawi',
    'Mozambique',
    'Lesotho',
    # International
    'France',
    'Turkey',
    'China',
]

COUNTRY_CHOICES = [(c, c) for c in SIGNUP_COUNTRY_ORDER]

_NON_CONGO_COUNTRIES = set(SIGNUP_COUNTRY_ORDER) - {'Congo'}


def _country_cities():
    from book_Project.checkout_cities import CHECKOUT_CITIES_BY_COUNTRY
    return {
        country: CHECKOUT_CITIES_BY_COUNTRY.get(country, [])
        for country in _NON_CONGO_COUNTRIES
    }


def get_departments_for_js():
    return [{'code': d['code'], 'name': d['name'], 'cities': d['cities']} for d in CONGO_DEPARTMENTS]


def get_signup_countries_for_js():
    """Unified data for the sign-up location cascade: Congo carries its
    department list (cascading select), every other country carries a
    flat city list (single select)."""
    country_cities = _country_cities()
    result = []
    for country in SIGNUP_COUNTRY_ORDER:
        if country == 'Congo':
            result.append({'code': 'Congo', 'name': 'Congo', 'departments': get_departments_for_js()})
        else:
            result.append({'code': country, 'name': country, 'cities': country_cities.get(country, [])})
    return result


def is_valid_congo_location(value: str) -> bool:
    return (value or '').strip() in _DEPT_BY_CODE


def normalize_congo_location(value: str) -> str:
    loc = (value or '').strip()
    return loc if is_valid_congo_location(loc) else ''


def is_valid_city_for_department(department_code: str, city: str) -> bool:
    dept = _DEPT_BY_CODE.get((department_code or '').strip())
    if not dept or not city:
        return False
    city = city.strip()
    return city in dept['cities']


def normalize_congo_city(department_code: str, city: str) -> str:
    city = (city or '').strip()
    if is_valid_city_for_department(department_code, city):
        return city
    return ''


def get_department(code: str) -> dict | None:
    return _DEPT_BY_CODE.get((code or '').strip())


def default_city_for_department(department_code: str) -> str:
    dept = get_department(department_code)
    if not dept:
        return DEFAULT_CONGO_CITY
    return dept['chef_lieu']


def is_valid_country(value: str) -> bool:
    return (value or '').strip() in SIGNUP_COUNTRY_ORDER


def normalize_country(value: str) -> str:
    country = (value or '').strip()
    return country if is_valid_country(country) else ''


def is_valid_city_for_country(country: str, city: str) -> bool:
    """For non-Congo countries only — Congo uses is_valid_city_for_department."""
    city = (city or '').strip()
    if not city or country not in _NON_CONGO_COUNTRIES:
        return False
    return city in _country_cities().get(country, [])


def normalize_country_city(country: str, city: str) -> str:
    city = (city or '').strip()
    if is_valid_city_for_country(country, city):
        return city
    return ''
