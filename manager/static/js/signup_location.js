/**
 * Cascading sign-up location selects: country -> (Congo: department -> city)
 * or (any other PawaPay-supported country: city only).
 */
(function (global) {
    'use strict';

    var _countries = null;

    var COUNTRY_FLAGS = {
        'Congo': '🇨🇬',
        'Democratic Republic of the Congo': '🇨🇩',
        'Cameroon': '🇨🇲',
        'Gabon': '🇬🇦',
        'Angola': '🇦🇴',
        'Chad': '🇹🇩',
        'Central African Republic': '🇨🇫',
        'Equatorial Guinea': '🇬🇶',
        'São Tomé and Príncipe': '🇸🇹',
    };

    // Example phone format per country — updates the phone field's
    // placeholder live as the country changes, so the hint always matches
    // the selected country's calling code and typical mobile number shape.
    var COUNTRY_PHONE_PLACEHOLDERS = {
        'Congo': '+242 06 123 4567',
        'Democratic Republic of the Congo': '+243 81 234 5678',
        'Cameroon': '+237 6 12 34 56 78',
        'Gabon': '+241 06 12 34 56',
        'Angola': '+244 923 456 789',
        'Chad': '+235 66 12 34 56',
        'Central African Republic': '+236 70 12 34 56',
        'Equatorial Guinea': '+240 222 123 456',
        'São Tomé and Príncipe': '+239 991 2345',
    };
    var DEFAULT_PHONE_PLACEHOLDER = 'Phone';

    function getCountries() {
        if (_countries) return _countries;
        var el = document.getElementById('signupCountriesData');
        if (!el) return [];
        try {
            _countries = JSON.parse(el.textContent);
        } catch (e) {
            _countries = [];
        }
        return _countries;
    }

    function findCountry(code) {
        var countries = getCountries();
        for (var i = 0; i < countries.length; i++) {
            if (countries[i].code === code) return countries[i];
        }
        return null;
    }

    function findDept(country, code) {
        if (!country || !country.departments) return null;
        for (var i = 0; i < country.departments.length; i++) {
            if (country.departments[i].code === code) return country.departments[i];
        }
        return null;
    }

    function clearSelect(select, placeholder) {
        select.innerHTML = '';
        var opt = document.createElement('option');
        opt.value = '';
        opt.textContent = placeholder || '';
        opt.disabled = true;
        opt.selected = true;
        select.appendChild(opt);
    }

    function fillCountries(countrySelect, placeholder) {
        clearSelect(countrySelect, placeholder);
        getCountries().forEach(function (c) {
            var opt = document.createElement('option');
            opt.value = c.code;
            var flag = COUNTRY_FLAGS[c.code];
            opt.textContent = flag ? (flag + '  ' + c.name) : c.name;
            countrySelect.appendChild(opt);
        });
    }

    function fillDepartments(deptSelect, country, placeholder) {
        clearSelect(deptSelect, placeholder);
        (country.departments || []).forEach(function (d) {
            var opt = document.createElement('option');
            opt.value = d.code;
            opt.textContent = d.name;
            deptSelect.appendChild(opt);
        });
    }

    function fillCitiesFlat(citySelect, cities, placeholder, selectedCity) {
        clearSelect(citySelect, placeholder);
        cities.forEach(function (city) {
            var opt = document.createElement('option');
            opt.value = city;
            opt.textContent = city;
            if (selectedCity && selectedCity === city) opt.selected = true;
            citySelect.appendChild(opt);
        });
        citySelect.disabled = false;
        citySelect.required = true;
    }

    function setDeptVisible(deptSelect, visible) {
        var wrap = deptSelect.closest('.signup-location-group');
        deptSelect.style.display = visible ? '' : 'none';
        if (wrap) wrap.classList.toggle('has-department', visible);
    }

    function findPhoneInput(countrySelect) {
        var form = countrySelect.closest('form');
        if (!form) return null;
        return form.querySelector('input[name="phone"]');
    }

    function updatePhonePlaceholder(countrySelect, countryCode) {
        var phoneInput = findPhoneInput(countrySelect);
        if (!phoneInput) return;
        var label = phoneInput.getAttribute('data-phone-label') || DEFAULT_PHONE_PLACEHOLDER;
        var example = COUNTRY_PHONE_PLACEHOLDERS[countryCode];
        phoneInput.placeholder = example ? (label + ' (' + example + ')') : label;
    }

    /** country changed (or initial load): rebuild department/city selects. */
    function onCountryChange(countrySelect, deptSelect, citySelect, deptPh, cityPh, selectedDept, selectedCity) {
        updatePhonePlaceholder(countrySelect, countrySelect.value);
        var country = findCountry(countrySelect.value);
        if (!country) {
            setDeptVisible(deptSelect, false);
            clearSelect(citySelect, cityPh);
            citySelect.disabled = true;
            citySelect.required = false;
            return;
        }

        if (country.departments) {
            setDeptVisible(deptSelect, true);
            fillDepartments(deptSelect, country, deptPh);
            deptSelect.disabled = false;
            deptSelect.required = true;
            if (selectedDept) {
                deptSelect.value = selectedDept;
                var dept = findDept(country, selectedDept);
                if (dept) {
                    fillCitiesFlat(citySelect, dept.cities, cityPh, selectedCity);
                } else {
                    clearSelect(citySelect, cityPh);
                    citySelect.disabled = true;
                }
            } else {
                clearSelect(citySelect, cityPh);
                citySelect.disabled = true;
                citySelect.required = false;
            }
            deptSelect.onchange = function () {
                var d = findDept(country, deptSelect.value);
                if (d) {
                    fillCitiesFlat(citySelect, d.cities, cityPh, '');
                } else {
                    clearSelect(citySelect, cityPh);
                    citySelect.disabled = true;
                }
            };
        } else {
            setDeptVisible(deptSelect, false);
            deptSelect.disabled = true;
            deptSelect.required = false;
            deptSelect.value = '';
            fillCitiesFlat(citySelect, country.cities || [], cityPh, selectedCity);
        }
    }

    function initRoot(root) {
        if (!root || root.dataset.locationInit === '1') return;
        var countrySelect = root.querySelector('.signup-country-select');
        var deptSelect = root.querySelector('.signup-dept-select');
        var citySelect = root.querySelector('.signup-city-select');
        if (!countrySelect || !deptSelect || !citySelect) return;

        var countryPh = countrySelect.getAttribute('data-placeholder') || '';
        var deptPh = deptSelect.getAttribute('data-placeholder') || '';
        var cityPh = citySelect.getAttribute('data-placeholder') || '';
        var selectedCountry = countrySelect.getAttribute('data-selected') || '';
        var selectedDept = deptSelect.getAttribute('data-selected') || '';
        var selectedCity = citySelect.getAttribute('data-selected') || '';

        fillCountries(countrySelect, countryPh);
        setDeptVisible(deptSelect, false);

        if (selectedCountry) {
            countrySelect.value = selectedCountry;
            onCountryChange(countrySelect, deptSelect, citySelect, deptPh, cityPh, selectedDept, selectedCity);
        } else {
            // Default to Congo so the richer department cascade is the
            // out-of-the-box experience for the platform's home market.
            countrySelect.value = 'Congo';
            onCountryChange(countrySelect, deptSelect, citySelect, deptPh, cityPh, '', '');
        }

        countrySelect.addEventListener('change', function () {
            onCountryChange(countrySelect, deptSelect, citySelect, deptPh, cityPh, '', '');
        });

        root.dataset.locationInit = '1';
    }

    function initAll() {
        document.querySelectorAll('[data-location-cascade]').forEach(initRoot);
    }

    global.SignupLocation = {
        initAll: initAll,
        initRoot: initRoot,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
})(window);
