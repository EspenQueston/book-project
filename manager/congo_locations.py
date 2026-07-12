"""Republic of Congo departments and cities for user/vendor location."""

DEFAULT_CONGO_LOCATION = 'Brazzaville'
DEFAULT_CONGO_CITY = 'Makélékélé'

CONGO_DEPARTMENTS = [
    {'code': 'Brazzaville', 'name': 'Brazzaville', 'chef_lieu': 'Makélékélé', 'cities': [
        'Makélékélé', 'Bacongo', 'Poto-Poto', 'Moungali', 'Ouenzé',
        'Talangaï', 'Mfilou', 'Madibou', 'Djiri',
    ]},
    {'code': 'Pointe-Noire', 'name': 'Pointe-Noire', 'chef_lieu': 'Lumumba', 'cities': [
        'Lumumba', 'Mvou-Mvou', 'Tié-Tié', 'Loandjili', 'Mongo-Mpoukou', 'Ngoyo',
    ]},
    {'code': 'Bouenza', 'name': 'Bouenza', 'chef_lieu': 'Madingou', 'cities': ['Madingou', 'Nkayi', 'Loudima', 'Mouyondzi']},
    {'code': 'Niari', 'name': 'Niari', 'chef_lieu': 'Dolisie', 'cities': ['Dolisie', 'Mossendjo', 'Kimongo']},
    {'code': 'Pool', 'name': 'Pool', 'chef_lieu': 'Kinkala', 'cities': ['Kinkala', 'Kindamba', 'Mindouli']},
    {'code': 'Plateaux', 'name': 'Plateaux', 'chef_lieu': 'Djambala', 'cities': ['Djambala', 'Gamboma', 'Lekana']},
    {'code': 'Cuvette', 'name': 'Cuvette', 'chef_lieu': 'Owando', 'cities': ['Owando', 'Makoua', 'Mossaka']},
    {'code': 'Cuvette-Ouest', 'name': 'Cuvette-Ouest', 'chef_lieu': 'Ewo', 'cities': ['Ewo', 'Kéllé', 'Etoumbi']},
    {'code': 'Sangha', 'name': 'Sangha', 'chef_lieu': 'Ouésso', 'cities': ['Ouésso', 'Sembé', 'Souanké']},
    {'code': 'Likouala', 'name': 'Likouala', 'chef_lieu': 'Impfondo', 'cities': ['Impfondo', 'Epéna', 'Dongou']},
    {'code': 'Kouilou', 'name': 'Kouilou', 'chef_lieu': 'Loango', 'cities': ['Loango', 'Hinda', 'Kakamoeka']},
    {'code': 'Lékoumou', 'name': 'Lékoumou', 'chef_lieu': 'Sibiti', 'cities': ['Sibiti', 'Komono', 'Zanaga']},
    {'code': 'Congo-Oubangui', 'name': 'Congo-Oubangui', 'chef_lieu': 'Mossaka', 'cities': ['Mossaka', 'Loukolela']},
    {'code': 'Nkéni-Alima', 'name': 'Nkéni-Alima', 'chef_lieu': 'Gamboma', 'cities': ['Gamboma', 'Abala']},
    {'code': 'Djoué-Léfini', 'name': 'Djoué-Léfini', 'chef_lieu': 'Odziba', 'cities': ['Odziba', 'Mayama']},
]

CONGO_DEPARTMENT_CHOICES = [(d['code'], d['name']) for d in CONGO_DEPARTMENTS]

_DEPT_BY_CODE = {d['code']: d for d in CONGO_DEPARTMENTS}


def get_departments_for_js():
    return [{'code': d['code'], 'name': d['name'], 'cities': d['cities']} for d in CONGO_DEPARTMENTS]


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
