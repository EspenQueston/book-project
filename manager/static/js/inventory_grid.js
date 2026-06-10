(function () {
    'use strict';

    function getVisibleCards(grid) {
        return Array.from(grid.querySelectorAll('.inv-grid-card')).filter(function (card) {
            return !card.classList.contains('inv-hidden-by-search');
        });
    }

    function renderPagination(grid) {
        var pageSize = parseInt(grid.getAttribute('data-page-size') || '24', 10);
        var toolbar = grid.closest('.vp-card') || grid.parentElement;
        var pagination = toolbar.querySelector('.inv-grid-pages');
        var meta = toolbar.querySelector('.inv-grid-meta-line');
        if (!pagination) return;

        var cards = getVisibleCards(grid);
        var total = cards.length;
        var pages = Math.max(1, Math.ceil(total / pageSize));
        var current = parseInt(grid.getAttribute('data-current-page') || '1', 10);
        if (current > pages) current = pages;
        if (current < 1) current = 1;
        grid.setAttribute('data-current-page', String(current));

        cards.forEach(function (card, index) {
            var page = Math.floor(index / pageSize) + 1;
            card.classList.toggle('inv-grid-hidden', page !== current);
        });

        if (meta) {
            var start = total ? (current - 1) * pageSize + 1 : 0;
            var end = Math.min(current * pageSize, total);
            meta.textContent = total
                ? start + '–' + end + ' / ' + total
                : '0';
        }

        pagination.innerHTML = '';
        if (pages <= 1) return;

        function addBtn(label, page, disabled, active) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'inv-grid-page-btn' + (active ? ' active' : '');
            btn.textContent = label;
            btn.disabled = !!disabled;
            if (!disabled && !active) {
                btn.addEventListener('click', function () {
                    grid.setAttribute('data-current-page', String(page));
                    renderPagination(grid);
                    var scroll = grid.closest('.inv-grid-scroll');
                    if (scroll) scroll.scrollTop = 0;
                });
            }
            pagination.appendChild(btn);
        }

        addBtn('‹', current - 1, current === 1, false);

        var windowSize = 5;
        var startPage = Math.max(1, current - Math.floor(windowSize / 2));
        var endPage = Math.min(pages, startPage + windowSize - 1);
        startPage = Math.max(1, endPage - windowSize + 1);

        for (var p = startPage; p <= endPage; p++) {
            addBtn(String(p), p, false, p === current);
        }

        addBtn('›', current + 1, current === pages, false);
    }

    window.invGridRefresh = function (gridId) {
        var grid = document.getElementById(gridId || 'invGridAll');
        if (grid) renderPagination(grid);
    };

    window.invGridInit = function () {
        document.querySelectorAll('.inv-grid').forEach(function (grid) {
            grid.setAttribute('data-current-page', '1');
            renderPagination(grid);
        });
    };

    document.addEventListener('DOMContentLoaded', window.invGridInit);
})();
