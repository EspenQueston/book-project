/**

 * Shared helpers for signup + dual email/SMS verification.

 */

(function (global) {

    'use strict';



    function normalizePhoneE164(raw) {

        var compact = (raw || '').trim().replace(/[\s\-().]/g, '');

        if (!compact) return '';

        if (compact.charAt(0) === '+') {

            return '+' + compact.slice(1).replace(/\D/g, '');

        }

        var digits = compact.replace(/\D/g, '');

        return digits ? '+' + digits : '';

    }



    function validatePhoneE164(raw) {

        var phone = normalizePhoneE164(raw);

        if (!phone || phone.charAt(0) !== '+') {

            return {

                ok: false,

                phone: phone,

                message: 'Invalid number. Use international format, e.g. +242061234567.',

            };

        }

        var digits = phone.slice(1);

        if (!/^\d{8,15}$/.test(digits)) {

            return {

                ok: false,

                phone: phone,

                message: 'Invalid number. Check the country code and number.',

            };

        }

        return { ok: true, phone: phone, message: '' };

    }



    function distributePin(inputs, hidden, digits, onUpdate) {

        digits = (digits || '').replace(/\D/g, '').slice(0, inputs.length);

        for (var i = 0; i < inputs.length; i++) {

            inputs[i].value = digits.charAt(i) || '';

            inputs[i].classList.toggle('filled', inputs[i].value.length > 0);

        }

        if (hidden) hidden.value = digits;

        if (onUpdate) onUpdate();

        return digits;

    }



    function initPinGroup(selector, hiddenId, onUpdate) {

        var inputs = document.querySelectorAll(selector);

        var hidden = document.getElementById(hiddenId);

        if (!inputs.length || !hidden) return;



        var container = inputs[0].closest('.pin-inputs');

        var group = container && container.closest('.pin-group');

        var pasteField = group ? group.querySelector('.pin-paste-field') : null;



        function applyDigits(raw) {

            var digits = distributePin(inputs, hidden, raw, onUpdate);

            if (pasteField && pasteField.value !== digits) {

                pasteField.value = digits;

            }

            return digits;

        }



        if (container) {

            container.addEventListener('paste', function (e) {

                e.preventDefault();

                var text = (e.clipboardData || global.clipboardData).getData('text');

                applyDigits(text);

                if (pasteField) pasteField.focus();

            });

        }



        if (pasteField) {

            pasteField.addEventListener('input', function () {

                applyDigits(pasteField.value);

            });

            pasteField.addEventListener('paste', function () {

                setTimeout(function () { applyDigits(pasteField.value); }, 0);

            });

            if (!pasteField.value && hidden.value) {

                pasteField.value = hidden.value;

                applyDigits(hidden.value);

            }

        }



        inputs.forEach(function (input, idx) {

            input.addEventListener('input', function () {

                var val = this.value.replace(/[^0-9]/g, '');

                if (val.length > 1) {

                    applyDigits(val);

                    if (pasteField) pasteField.focus();

                    return;

                }

                this.value = val;

                if (this.value && idx < inputs.length - 1) inputs[idx + 1].focus();

                applyDigits(getPin());

            });

            input.addEventListener('keydown', function (e) {

                if (e.key === 'Backspace' && !this.value && idx > 0) {

                    inputs[idx - 1].focus();

                    inputs[idx - 1].value = '';

                    applyDigits(getPin());

                }

            });

            input.addEventListener('paste', function (e) {

                e.preventDefault();

                applyDigits((e.clipboardData || global.clipboardData).getData('text'));

            });

        });



        function getPin() {

            var pin = '';

            inputs.forEach(function (i) { pin += i.value; });

            return pin;

        }



        applyDigits(getPin());

    }



    function startResendCooldown(linkId, countdownId, numId, seconds, onDone) {

        var link = document.getElementById(linkId);

        var countdown = document.getElementById(countdownId);

        var countNum = document.getElementById(numId);

        if (!link || !countdown || !countNum) return null;

        link.style.display = 'none';

        countdown.style.display = 'inline';

        var sec = seconds || 60;

        countNum.textContent = sec;

        var timer = setInterval(function () {

            sec--;

            countNum.textContent = sec;

            if (sec <= 0) {

                clearInterval(timer);

                link.style.display = 'inline';

                countdown.style.display = 'none';

                if (onDone) onDone();

            }

        }, 1000);

        return timer;

    }



    function shakeEl(selector) {

        var el = document.querySelector(selector);

        if (!el) return;

        el.style.animation = 'signupShake 0.4s ease';

        setTimeout(function () { el.style.animation = ''; }, 500);

    }



    global.SignupAuth = {

        normalizePhoneE164: normalizePhoneE164,

        validatePhoneE164: validatePhoneE164,

        initPinGroup: initPinGroup,

        startResendCooldown: startResendCooldown,

        shakeEl: shakeEl,

    };

})(window);

