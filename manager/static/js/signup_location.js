/**
 * Cascading Congo department → city selects.
 */
(function (global) {
    'use strict';

    var _data = null;

    function getData() {
        if (_data) return _data;
        var el = document.getElementById('congoLocationsData');
        if (!el) return [];
        try {
            _data = JSON.parse(el.textContent);
        } catch (e) {
            _data = [];
        }
        return _data;
    }

    function findDept(code) {
        var depts = getData();
        for (var i = 0; i < depts.length; i++) {
            if (depts[i].code === code) return depts[i];
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

    function fillDepartments(deptSelect, placeholder) {
        clearSelect(deptSelect, placeholder);
        var depts = getData();
        depts.forEach(function (d) {
            var opt = document.createElement('option');
            opt.value = d.code;
            opt.textContent = d.name;
            deptSelect.appendChild(opt);
        });
    }

    function fillCities(citySelect, deptCode, placeholder, selectedCity) {
        var dept = findDept(deptCode);
        clearSelect(citySelect, placeholder);
        if (!dept) {
            citySelect.disabled = true;
            citySelect.required = false;
            return;
        }
        dept.cities.forEach(function (city) {
            var opt = document.createElement('option');
            opt.value = city;
            opt.textContent = city;
            if (selectedCity && selectedCity === city) opt.selected = true;
            citySelect.appendChild(opt);
        });
        citySelect.disabled = false;
        citySelect.required = true;
        if (selectedCity && dept.cities.indexOf(selectedCity) === -1) {
            citySelect.selectedIndex = 0;
        }
    }

    function initRoot(root) {
        if (!root || root.dataset.locationInit === '1') return;
        var deptSelect = root.querySelector('.signup-dept-select');
        var citySelect = root.querySelector('.signup-city-select');
        if (!deptSelect || !citySelect) return;

        var deptPh = deptSelect.getAttribute('data-placeholder') || '';
        var cityPh = citySelect.getAttribute('data-placeholder') || '';
        var selectedDept = deptSelect.getAttribute('data-selected') || '';
        var selectedCity = citySelect.getAttribute('data-selected') || '';

        fillDepartments(deptSelect, deptPh);
        if (selectedDept) {
            deptSelect.value = selectedDept;
            fillCities(citySelect, selectedDept, cityPh, selectedCity);
        } else {
            fillCities(citySelect, '', cityPh, '');
        }

        deptSelect.addEventListener('change', function () {
            fillCities(citySelect, deptSelect.value, cityPh, '');
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
