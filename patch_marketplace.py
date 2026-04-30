import os
app_dir = r"c:\Users\Cluivert\CascadeProjects\book_Project\book_Project\marketplace\templates\marketplace"

css_to_add = """
    /* === PWA Task 1: Mobile Taobao Design === */
    @media (max-width: 768px) {
        .detail-hero, .desktop-layout { display: none !important; }
        .product-mobile-page { display: block !important; }
    }
    @media (min-width: 769px) {
        .product-mobile-page { display: none !important; }
    }
    .product-mobile-page {
        background: #f8fafc;
        padding-bottom: 85px;
    }
    .pmp-gallery {
        width: 100%;
        height: 380px;
        background: #fff;
        display: flex;
        overflow-x: auto;
        scroll-snap-type: x mandatory;
    }
    .pmp-gallery img { width: 100%; height: 100%; object-fit: contain; scroll-snap-align: center; flex: 0 0 100%; }
    .pmp-info { background: #fff; padding: 15px; margin-bottom: 12px; }
    .pmp-price { color: #ef4444; font-size: 1.8rem; font-weight: 800; }
    .pmp-title { font-size: 1.15rem; font-weight: 700; color: #1e293b; margin: 10px 0; }
    .pmp-bottom-bar {
        position: fixed; bottom: 0; left: 0; right: 0; background: #fff; height: 60px;
        display: flex; align-items: center; padding: 0 10px; box-shadow: 0 -2px 10px rgba(0,0,0,0.05); z-index: 1000;
    }
    .pmp-icon-btn { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 50px; color: #64748b; font-size: 0.70rem; text-decoration: none; }
    .pmp-icon-btn i { font-size: 1.25rem; margin-bottom: 2px; }
    .pmp-action-btn { flex: 1; height: 40px; border-radius: 20px; font-weight: 700; color: #fff; border: none; margin-left: 8px; }
    .pmp-cart { background: linear-gradient(135deg, #f59e0b, #f97316); }
    .pmp-buy { background: linear-gradient(135deg, #ef4444, #ec4899); }
"""

def patch_file(filename, prefix, item_var):
    filepath = os.path.join(app_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if '/* === PWA Task 1' in content: return

    if "    @media(max-width:768px)" in content:
        content = content.replace("    @media(max-width:768px) {", css_to_add + "\\n    @media(max-width:768px) {")
    elif "    @media(max-width:991px)" in content:
        content = content.replace("    @media(max-width:991px) {", css_to_add + "\\n    @media(max-width:991px) {")
    else:
        content = content.replace("</style>", css_to_add + "\\n</style>")

    # Prepare layout wrapping
    content = content.replace('<div class="breadcrumb-section">', '<div class="desktop-layout">\\n<div class="breadcrumb-section">')
    content = content.replace('{% endblock %}', '</div>\\n{% endblock %}')
    content = content.replace('</div>\\n</div>\\n{% endblock %}', '</div>\\n{% endblock %}')

    vendor_param = ""
    if filename == "product_detail.html":
        vendor_param = "?vendor={{ product.vendor.id|default:'' }}"
    elif filename == "course_detail.html":
        vendor_param = "?vendor={{ course.vendor.id|default:'' }}"

    mobile_html = f"""
<!-- ===== PWA T1 & T2: MOBILE ONLY ===== -->
<div class="product-mobile-page">
    <div class="pmp-gallery">
        <img src="{{{{ {item_var}.get_image_url }}}}" alt="{{{{ {item_var}.name|default:{item_var}.title }}}}">
    </div>
    <div class="pmp-info">
        <div class="pmp-price">¥{{{{ {item_var}.price }}}}</div>
        <h1 class="pmp-title">{{{{ {item_var}.name|default:{item_var}.title }}}}</h1>
    </div>
    
    <div class="pmp-bottom-bar">
        <a href="{{% url 'manager:public_home' %}}" class="pmp-icon-btn"><i class="fas fa-store"></i><span>店铺</span></a>
        <a href="{{% url 'manager:public_messages' %}}{vendor_param}" class="pmp-icon-btn"><i class="fas fa-comment-dots"></i><span>客服</span></a>
        
        <button class="pmp-action-btn pmp-cart" onclick="addToCart({{{{ {item_var}.id }}}})">加入购物车</button>
        <button class="pmp-action-btn pmp-buy" onclick="buyNow({{{{ {item_var}.id }}}})">立即购买</button>
    </div>
</div>
<script>
    function addToCart() {{
        if (typeof window.addToCart === 'function') window.addToCart();
    }}
    function buyNow() {{
        if (typeof window.buyNow === 'function') window.buyNow();
    }}
</script>
"""
    content = content.replace('<div class="desktop-layout">', mobile_html + '\\n<div class="desktop-layout">')

    # Remove extra wrapper div matching that could bleed into base endblock
    content = content.replace('</div>\\n</div>\\n{% endblock %}', '</div>\\n{% endblock %}')

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
patch_file("product_detail.html", "product", "product")
patch_file("course_detail.html", "course", "course")
patch_file("supermarket_detail.html", "item", "item")
