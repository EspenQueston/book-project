"""Major cities per checkout country (max 7 each). Keys match checkout <option value>."""

CHECKOUT_CITIES_BY_COUNTRY = {
    # West Africa — KKiaPay
    'Benin': ['Cotonou', 'Porto-Novo', 'Parakou', 'Abomey-Calavi', 'Djougou', 'Bohicon', 'Natitingou'],
    'Burkina Faso': ['Ouagadougou', 'Bobo-Dioulasso', 'Koudougou', 'Banfora', 'Ouahigouya', 'Kaya', 'Dédougou'],
    "Côte d'Ivoire": ['Abidjan', 'Bouaké', 'Daloa', 'Korhogo', 'San-Pédro', 'Yamoussoukro', 'Man'],
    'Guinea': ['Conakry', 'Nzérékoré', 'Kankan', 'Kindia', 'Labé', 'Mamou', 'Boké'],
    'Mali': ['Bamako', 'Sikasso', 'Mopti', 'Koutiala', 'Ségou', 'Kayes', 'Gao'],
    'Niger': ['Niamey', 'Zinder', 'Maradi', 'Agadez', 'Tahoua', 'Dosso', 'Diffa'],
    'Senegal': ['Dakar', 'Touba', 'Thiès', 'Rufisque', 'Kaolack', 'Saint-Louis', 'Ziguinchor'],
    'Togo': ['Lomé', 'Sokodé', 'Kara', 'Kpalimé', 'Atakpamé', 'Dapaong', 'Tsévié'],
    # Central Africa — PawaPay
    'Angola': ['Luanda', 'Huambo', 'Lobito', 'Benguela', 'Lubango', 'Malanje', 'Namibe'],
    'Cameroon': ['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda', 'Maroua', 'Ngaoundéré'],
    'Central African Republic': ['Bangui', 'Bimbo', 'Berbérati', 'Carnot', 'Bambari', 'Bouar', 'Bossangoa'],
    'Chad': ["N'Djamena", 'Moundou', 'Sarh', 'Abéché', 'Kelo', 'Koumra', 'Pala'],
    'Congo': ['Brazzaville', 'Pointe-Noire', 'Dolisie', 'Nkayi', 'Owando', 'Ouesso', 'Loandjili'],
    'Democratic Republic of the Congo': ['Kinshasa', 'Lubumbashi', 'Mbuji-Mayi', 'Kananga', 'Kisangani', 'Goma', 'Bukavu'],
    'Equatorial Guinea': ['Malabo', 'Bata', 'Ebebiyín', 'Aconibe', 'Añisoc', 'Evinayong', 'Mongomo'],
    'Gabon': ['Libreville', 'Port-Gentil', 'Franceville', 'Oyem', 'Moanda', 'Mouila', 'Lambaréné'],
    'São Tomé and Príncipe': ['São Tomé', 'Trindade', 'Santana', 'Neves', 'Guadalupe', 'Santo António', 'Ribeira Afonso'],
    # Asia
    'China': ['北京', '上海', '广州', '深圳', '成都', '杭州', '武汉'],
    'Hong Kong': ['Central', 'Kowloon', 'Tsuen Wan', 'Sha Tin', 'Tuen Mun', 'Yuen Long', 'Tseung Kwan O'],
    'Taiwan': ['台北', '高雄', '台中', '台南', '新北', '桃园', '新竹'],
    'Japan': ['东京', '大阪', '横滨', '名古屋', '札幌', '福冈', '京都'],
}


def get_checkout_cities_by_country():
    """Return country → cities mapping (each list capped at 7)."""
    return {
        country: cities[:7]
        for country, cities in CHECKOUT_CITIES_BY_COUNTRY.items()
    }


def is_valid_checkout_city(country, city):
    """True if city is in the known list for the given checkout country."""
    if not country or not city:
        return False
    return city in CHECKOUT_CITIES_BY_COUNTRY.get(country, [])
