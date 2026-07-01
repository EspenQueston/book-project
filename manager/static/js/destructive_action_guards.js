(function (global) {
    'use strict';

    if (global.__destructiveGuardsInit) return;
    global.__destructiveGuardsInit = true;

    var DESTRUCTIVE_ACTIONS = ['delete', 'clear_read', 'clear_all', 'remove'];
    var _gConfirmCb = null;

    function patchGConfirmApi() {
        var modal = document.getElementById('gConfirmModal');
        if (!modal) return;
        var okBtn = document.getElementById('gConfirmOk');
        if (!okBtn) return;

        global.gConfirm = function (msg, callback, opts) {
            opts = opts || {};
            var i18n = global._G_I18N || {};
            var iconEl = document.getElementById('gConfirmIcon');
            var titleEl = document.getElementById('gConfirmTitle');
            var textEl = document.getElementById('gConfirmText');
            if (titleEl) titleEl.textContent = opts.title || i18n.confirmTitle || 'Confirm';
            if (textEl) textEl.textContent = msg;
            if (iconEl) {
                iconEl.className = 'g-modal-icon ' + (opts.danger ? 'danger-icon' : 'confirm-icon');
                iconEl.innerHTML = '<i class="fas ' + (opts.danger ? 'fa-exclamation-triangle' : 'fa-question') + '"></i>';
            }
            okBtn.className = 'g-modal-btn ' + (opts.danger ? 'g-modal-btn-danger' : 'g-modal-btn-confirm');
            okBtn.textContent = opts.okText || i18n.confirmOk || 'OK';
            _gConfirmCb = callback;
            okBtn.onclick = function () {
                var cb = _gConfirmCb;
                global.gModalClose();
                if (cb) cb();
            };
            modal.classList.add('show');
        };

        global.gModalClose = function () {
            modal.classList.remove('show');
            _gConfirmCb = null;
        };
    }

    function ensurePopupUi() {
        if (document.getElementById('gConfirmModal')) {
            patchGConfirmApi();
            return;
        }

        var css = document.createElement('style');
        css.textContent = [
            '.g-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(6px);z-index:100001;display:none;align-items:center;justify-content:center;opacity:0;transition:opacity .25s}',
            '.g-modal-overlay.show{display:flex;opacity:1}',
            '.g-modal-card{background:#fff;border-radius:20px;padding:40px 36px 32px;max-width:420px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.15);transform:scale(.9);transition:transform .3s cubic-bezier(.21,1.02,.73,1)}',
            '.g-modal-overlay.show .g-modal-card{transform:scale(1)}',
            '.g-modal-icon{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:1.6rem}',
            '.g-modal-icon.confirm-icon{background:linear-gradient(135deg,rgba(102,126,234,.12),rgba(118,75,162,.12));color:#667eea}',
            '.g-modal-icon.danger-icon{background:rgba(239,68,68,.1);color:#ef4444}',
            '.g-modal-title{font-size:1.2rem;font-weight:700;color:#1a1a2e;margin-bottom:8px}',
            '.g-modal-text{color:#6b7280;font-size:.95rem;line-height:1.6;margin-bottom:28px}',
            '.g-modal-actions{display:flex;gap:12px;justify-content:center}',
            '.g-modal-btn{padding:10px 28px;border:none;border-radius:10px;font-weight:600;font-size:.92rem;cursor:pointer;transition:all .2s}',
            '.g-modal-btn-cancel{background:#f3f4f6;color:#4b5563}',
            '.g-modal-btn-cancel:hover{background:#e5e7eb}',
            '.g-modal-btn-confirm{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff}',
            '.g-modal-btn-danger{background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff}',
        ].join('');
        document.head.appendChild(css);

        var wrap = document.createElement('div');
        wrap.innerHTML = [
            '<span id="gI18nConfirmTitle" class="visually-hidden">Confirm</span>',
            '<span id="gI18nConfirmOk" class="visually-hidden">OK</span>',
            '<span id="gI18nLogoutTitle" class="visually-hidden">Sign out</span>',
            '<span id="gI18nLogoutMessage" class="visually-hidden">Are you sure you want to sign out?</span>',
            '<span id="gI18nDeleteTitle" class="visually-hidden">Confirm deletion</span>',
            '<span id="gI18nDeleteMessage" class="visually-hidden">Are you sure you want to delete this item?</span>',
            '<div id="gConfirmModal" class="g-modal-overlay">',
            '  <div class="g-modal-card">',
            '    <div id="gConfirmIcon" class="g-modal-icon confirm-icon"><i class="fas fa-question"></i></div>',
            '    <h5 id="gConfirmTitle" class="g-modal-title"></h5>',
            '    <p id="gConfirmText" class="g-modal-text"></p>',
            '    <div class="g-modal-actions">',
            '      <button type="button" class="g-modal-btn g-modal-btn-cancel" id="gConfirmCancel">Cancel</button>',
            '      <button type="button" id="gConfirmOk" class="g-modal-btn g-modal-btn-confirm">OK</button>',
            '    </div>',
            '  </div>',
            '</div>',
        ].join('');
        document.body.appendChild(wrap);

        var modal = document.getElementById('gConfirmModal');
        modal.addEventListener('click', function (e) {
            if (e.target === modal) global.gModalClose();
        });
        document.getElementById('gConfirmCancel').addEventListener('click', function () {
            global.gModalClose();
        });

        if (!global._G_I18N) {
            global._G_I18N = {
                confirmTitle: document.getElementById('gI18nConfirmTitle').textContent,
                confirmOk: document.getElementById('gI18nConfirmOk').textContent,
                logoutTitle: document.getElementById('gI18nLogoutTitle').textContent,
                logoutMessage: document.getElementById('gI18nLogoutMessage').textContent,
                deleteTitle: document.getElementById('gI18nDeleteTitle').textContent,
                deleteMessage: document.getElementById('gI18nDeleteMessage').textContent,
            };
        }

        patchGConfirmApi();
    }

    function pathOf(url) {
        try {
            return new URL(url, global.location.href).pathname;
        } catch (e) {
            return '';
        }
    }

    function isLogoutHref(href) {
        var path = pathOf(href);
        return /\/logout\/?$/.test(path);
    }

    function isDeleteForm(form) {
        if (!form || form.dataset.noConfirm !== undefined) return false;
        if (form.dataset.confirmMessage || form.dataset.confirm) return true;
        var action = (form.getAttribute('action') || '').toLowerCase();
        if (/\/delete\/|delete_|remove_|\/clear/.test(action)) return true;
        var actionInput = form.querySelector('[name="action"]');
        if (actionInput && DESTRUCTIVE_ACTIONS.indexOf(actionInput.value) >= 0) return true;
        if (form.querySelector('button.btn-danger[type="submit"], button.btn-outline-danger[type="submit"]')) {
            return !!(actionInput || /delete|remove|clear/.test(action));
        }
        return false;
    }

    function getDeleteMessage(form) {
        return form.dataset.confirmMessage || form.dataset.confirm ||
            (global._G_I18N && global._G_I18N.deleteMessage) ||
            'Are you sure you want to delete this item?';
    }

    function getLogoutMessage() {
        return (global._G_I18N && global._G_I18N.logoutMessage) ||
            'Are you sure you want to sign out?';
    }

    function confirmAction(msg, callback, opts) {
        ensurePopupUi();
        if (typeof global.gConfirm === 'function') {
            global.gConfirm(msg, callback, opts || { danger: true });
            return;
        }
        if (global.confirm(msg)) callback();
    }

    global.gConfirmAction = confirmAction;

    global.vendorMobileJumpChange = function (select) {
        var val = select.value;
        if (!val) return;
        var previous = select.dataset.lastValue || '';
        select.value = previous;
        if (isLogoutHref(val)) {
            confirmAction(getLogoutMessage(), function () {
                global.location.href = val;
            }, {
                danger: true,
                title: (global._G_I18N && global._G_I18N.logoutTitle) || 'Sign out',
            });
            return;
        }
        select.dataset.lastValue = val;
        global.location.href = val;
    };

    function initDestructiveActionGuards() {
        ensurePopupUi();

        document.addEventListener('click', function (e) {
            var link = e.target.closest('a[href]');
            if (!link || link.dataset.noConfirm !== undefined) return;
            var href = link.getAttribute('href');
            if (!href || href === '#' || href.indexOf('javascript:') === 0) return;
            if (!isLogoutHref(href)) return;
            e.preventDefault();
            e.stopImmediatePropagation();
            confirmAction(getLogoutMessage(), function () {
                global.location.href = link.href;
            }, {
                danger: true,
                title: (global._G_I18N && global._G_I18N.logoutTitle) || 'Sign out',
            });
        }, true);

        document.addEventListener('submit', function (e) {
            var form = e.target;
            if (!(form instanceof HTMLFormElement)) return;
            if (form.dataset.confirmed === '1') {
                delete form.dataset.confirmed;
                return;
            }
            if (!isDeleteForm(form)) return;
            e.preventDefault();
            e.stopPropagation();
            confirmAction(getDeleteMessage(form), function () {
                form.dataset.confirmed = '1';
                if (typeof form.requestSubmit === 'function') form.requestSubmit();
                else form.submit();
            }, {
                danger: true,
                title: (global._G_I18N && global._G_I18N.deleteTitle) || 'Confirm deletion',
            });
        }, true);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDestructiveActionGuards);
    } else {
        initDestructiveActionGuards();
    }
})(window);
