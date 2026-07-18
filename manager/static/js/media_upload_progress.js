/*
 * Reusable image/video upload widget for vendor & admin product/supermarket
 * forms: shows real read progress (via FileReader on the local file) while
 * the browser loads the selected file, then swaps in a preview thumbnail
 * (image) or inline player (video) plus a success message once ready.
 *
 * The file itself is NOT sent to the server until the surrounding <form>
 * is submitted — this widget only gives feedback for the local read/attach
 * step, which is what a vendor actually watches happen when picking a file.
 *
 * Markup contract (see product_form.html / supermarket_form.html):
 *   <div data-media-slot data-kind="image|video">
 *     <div data-preview>...(existing thumbnail or empty state)...</div>
 *     <input type="file" class="media-slot-input" name="...">
 *     <div class="media-slot-progress"><div class="media-slot-progress-bar"></div></div>
 *     <div class="media-slot-status"></div>
 *   </div>
 */
(function () {
    var MAX_IMAGE_BYTES = 8 * 1024 * 1024;   // 8 MB
    var MAX_VIDEO_BYTES = 50 * 1024 * 1024;  // 50 MB

    function initSlot(slot) {
        var input = slot.querySelector('.media-slot-input');
        var preview = slot.querySelector('[data-preview]');
        var progressWrap = slot.querySelector('.media-slot-progress');
        var bar = slot.querySelector('.media-slot-progress-bar');
        var status = slot.querySelector('.media-slot-status');
        if (!input) return;
        var isVideo = slot.getAttribute('data-kind') === 'video';

        input.addEventListener('change', function () {
            var file = input.files && input.files[0];
            status.textContent = '';
            status.className = 'media-slot-status';
            if (!file) return;

            var maxBytes = isVideo ? MAX_VIDEO_BYTES : MAX_IMAGE_BYTES;
            if (file.size > maxBytes) {
                status.textContent = isVideo
                    ? 'Vidéo trop volumineuse (max 50 Mo).'
                    : 'Image trop volumineuse (max 8 Mo).';
                status.classList.add('media-slot-status-error');
                input.value = '';
                return;
            }

            progressWrap.style.display = 'block';
            bar.style.width = '0%';

            var reader = new FileReader();
            reader.onprogress = function (e) {
                if (e.lengthComputable) {
                    bar.style.width = Math.round((e.loaded / e.total) * 100) + '%';
                }
            };
            reader.onload = function () {
                bar.style.width = '100%';
                var objectUrl = URL.createObjectURL(file);
                setTimeout(function () {
                    preview.innerHTML = isVideo
                        ? '<video src="' + objectUrl + '" class="media-slot-media" controls muted></video>'
                        : '<img src="' + objectUrl + '" class="media-slot-media" alt="">';
                    status.textContent = isVideo
                        ? '✓ Vidéo chargée avec succès'
                        : '✓ Image chargée avec succès';
                    status.classList.add('media-slot-status-ok');
                    progressWrap.style.display = 'none';
                }, 200);
            };
            reader.onerror = function () {
                status.textContent = 'Erreur de lecture du fichier.';
                status.classList.add('media-slot-status-error');
                progressWrap.style.display = 'none';
            };
            reader.readAsArrayBuffer(file);
        });
    }

    document.querySelectorAll('[data-media-slot]').forEach(initSlot);
})();
