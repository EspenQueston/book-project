/*
 * Hover-to-zoom + click-to-enlarge for product/supermarket gallery images.
 * Wrap any <img> in a `.zoom-hover-wrap` element and this auto-binds:
 *   - mousemove tracks the cursor to set the zoom's transform-origin, so
 *     hovering behaves like a magnifying glass rather than a flat scale-up.
 *   - click opens a fullscreen lightbox with the same image at full size.
 * Re-run initZoomImages() after swapping a gallery's main image (e.g. when
 * a thumbnail click changes <img id="mainImage">'s src) to keep it bound.
 */
(function () {
    function ensureLightbox() {
        var lb = document.getElementById('imgZoomLightbox');
        if (lb) return lb;
        lb = document.createElement('div');
        lb.id = 'imgZoomLightbox';
        lb.className = 'img-zoom-lightbox';
        lb.innerHTML = '<button type="button" class="img-zoom-lightbox-close" aria-label="Close">&times;</button><img alt="">';
        document.body.appendChild(lb);

        function close() {
            lb.classList.remove('in');
            setTimeout(function () { lb.classList.remove('show'); }, 200);
        }
        lb.querySelector('.img-zoom-lightbox-close').addEventListener('click', close);
        lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && lb.classList.contains('show')) close();
        });
        lb.__close = close;
        return lb;
    }

    function openLightbox(src) {
        var lb = ensureLightbox();
        lb.querySelector('img').src = src;
        lb.classList.add('show');
        requestAnimationFrame(function () { lb.classList.add('in'); });
    }

    window.initZoomImages = function (root) {
        (root || document).querySelectorAll('.zoom-hover-wrap').forEach(function (wrap) {
            if (wrap.__zoomBound) return;
            wrap.__zoomBound = true;
            var img = wrap.querySelector('img');
            if (!img) return;
            wrap.addEventListener('mousemove', function (e) {
                var rect = wrap.getBoundingClientRect();
                var x = ((e.clientX - rect.left) / rect.width) * 100;
                var y = ((e.clientY - rect.top) / rect.height) * 100;
                var current = wrap.querySelector('img');
                if (current) current.style.transformOrigin = x + '% ' + y + '%';
            });
            wrap.addEventListener('mouseleave', function () {
                var current = wrap.querySelector('img');
                if (current) current.style.transformOrigin = '50% 50%';
            });
            wrap.addEventListener('click', function () {
                var current = wrap.querySelector('img');
                if (current) openLightbox(current.src);
            });
        });
    };

    document.addEventListener('DOMContentLoaded', function () { window.initZoomImages(); });
})();
