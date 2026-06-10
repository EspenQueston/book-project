(function (global) {
    'use strict';

    if (global.__listingFollowInit) return;
    global.__listingFollowInit = true;

    function getCsrf() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    function notify(msg, type) {
        if (typeof global.gToast === 'function') {
            global.gToast(msg, type || 'success');
            return;
        }
        if (typeof global.showToast === 'function') {
            global.showToast(msg, type || 'success');
            return;
        }
    }

    function updateFollowButton(btn, following) {
        if (!btn) return;
        btn.dataset.following = following ? '1' : '0';
        btn.classList.toggle('is-following', !!following);
        btn.setAttribute('aria-pressed', following ? 'true' : 'false');
        var label = btn.querySelector('.follow-btn-label');
        var icon = btn.querySelector('i');
        if (label) {
            label.textContent = following ? label.dataset.following : label.dataset.follow;
        }
        if (icon) {
            icon.className = 'fas ' + (following ? 'fa-check' : 'fa-plus');
        }
    }

    function toggleFollow(url, btn) {
        var fd = new FormData();
        fd.append('csrfmiddlewaretoken', getCsrf());
        fetch(url, { method: 'POST', body: fd })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d.login_required) {
                    var loginUrl = btn && btn.dataset.loginUrl;
                    global.location.href = loginUrl || '/manager/public/user/login/';
                    return;
                }
                if (d.success) {
                    updateFollowButton(btn, d.following);
                }
                notify(d.message || 'OK', d.success ? 'success' : 'error');
            })
            .catch(function () {
                notify((global._G_I18N && global._G_I18N.networkError) || '网络错误', 'error');
            });
    }

    global.updateFollowButton = updateFollowButton;

    global.toggleVendorFollow = function (vendorId, btn) {
        var target = btn;
        if (!target || !target.classList || !target.classList.contains('vendor-follow-btn')) {
            target = document.querySelector('.vendor-follow-btn[data-vendor-id="' + vendorId + '"]');
        }
        toggleFollow('/manager/vendor/' + vendorId + '/follow/', target);
    };

    global.togglePublisherFollow = function (publisherId, btn) {
        var target = btn;
        if (!target || !target.classList || !target.classList.contains('publisher-follow-btn')) {
            target = document.querySelector('.publisher-follow-btn[data-publisher-id="' + publisherId + '"]');
        }
        toggleFollow('/manager/publisher/' + publisherId + '/follow/', target);
    };

    document.addEventListener('click', function (e) {
        var vendorBtn = e.target.closest('.vendor-follow-btn');
        if (vendorBtn) {
            e.preventDefault();
            toggleVendorFollow(vendorBtn.dataset.vendorId, vendorBtn);
            return;
        }
        var publisherBtn = e.target.closest('.publisher-follow-btn');
        if (publisherBtn) {
            e.preventDefault();
            togglePublisherFollow(publisherBtn.dataset.publisherId, publisherBtn);
        }
    });
})(window);
