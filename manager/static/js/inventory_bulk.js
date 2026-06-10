(function () {
    var bar = document.getElementById('invBulkBar');
    var form = document.getElementById('invBulkForm');
    var countEl = document.getElementById('invBulkCount');
    var selectAll = document.getElementById('invSelectAll');
    var actionSelect = document.getElementById('invBulkAction');
    var deltaWrap = document.getElementById('invBulkDeltaWrap');
    var setWrap = document.getElementById('invBulkSetWrap');
    if (!bar || !form) return;

    function visiblePanel() {
        return document.querySelector('.inv-panel.active');
    }

    function rowCheckboxes() {
        var panel = visiblePanel();
        if (!panel) return [];
        return Array.prototype.slice.call(panel.querySelectorAll('.inv-select'));
    }

    function selectedCheckboxes() {
        return rowCheckboxes().filter(function (cb) { return cb.checked; });
    }

    function updateBar() {
        var selected = selectedCheckboxes();
        var count = selected.length;
        bar.hidden = count === 0;
        if (countEl) {
            countEl.textContent = count + (count === 1 ? ' item selected' : ' items selected');
        }
        if (selectAll) {
            var boxes = rowCheckboxes();
            selectAll.checked = boxes.length > 0 && boxes.every(function (cb) { return cb.checked; });
            selectAll.indeterminate = count > 0 && count < boxes.length;
        }
        toggleActionFields();
    }

    function toggleActionFields() {
        var action = actionSelect ? actionSelect.value : 'add';
        if (deltaWrap) deltaWrap.hidden = action === 'set';
        if (setWrap) setWrap.hidden = action !== 'set';
    }

    document.addEventListener('change', function (e) {
        if (e.target.classList && e.target.classList.contains('inv-select')) {
            updateBar();
        }
    });

    if (selectAll) {
        selectAll.addEventListener('change', function () {
            rowCheckboxes().forEach(function (cb) {
                var row = cb.closest('.inv-row');
                if (row && row.style.display !== 'none') {
                    cb.checked = selectAll.checked;
                }
            });
            updateBar();
        });
    }

    if (actionSelect) {
        actionSelect.addEventListener('change', toggleActionFields);
        toggleActionFields();
    }

    form.addEventListener('submit', function (e) {
        var selected = selectedCheckboxes();
        if (!selected.length) {
            e.preventDefault();
            return;
        }
        form.querySelectorAll('input[name="selected_items"]').forEach(function (el) { el.remove(); });
        selected.forEach(function (cb) {
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'selected_items';
            input.value = cb.value;
            form.appendChild(input);
        });
        var action = actionSelect ? actionSelect.value : 'add';
        if (action === 'set') {
            var manual = form.querySelector('[name="manual_value"]');
            if (!manual || manual.value === '') {
                e.preventDefault();
                manual && manual.focus();
            }
        } else if (action === 'subtract' || action === 'add') {
            var delta = form.querySelector('[name="delta"]');
            if (!delta || parseInt(delta.value, 10) === 0) {
                e.preventDefault();
                delta && delta.focus();
            }
        }
    });

    window.invBulkRefresh = updateBar;
    updateBar();
})();
