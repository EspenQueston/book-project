"""Append new translation entries to .po files and compile to .mo"""

import os
import struct
import array

# New translations: (msgid, english, french)
NEW_ENTRIES = [
    # base.html additions
    ("博客", "Blog", "Blog"),
    ("更多", "More", "Plus"),
    ("关于我们", "About Us", "À Propos"),
    ("我们的服务", "Our Services", "Nos Services"),
    ("微信", "WeChat", "WeChat"),

    # about.html
    ("致力于推广阅读文化", "Dedicated to Promoting Reading Culture", "Dédiés à la Promotion de la Culture de Lecture"),
    ("我们是一个充满激情的团队，致力于通过技术创新让每个人都能享受到阅读的乐趣。我们的使命是建设一个智能、便捷的图书管理平台。",
     "We are a passionate team dedicated to making reading accessible to everyone through technological innovation. Our mission is to build an intelligent, convenient book management platform.",
     "Nous sommes une équipe passionnée dédiée à rendre la lecture accessible à tous grâce à l'innovation technologique. Notre mission est de construire une plateforme de gestion de livres intelligente et pratique."),
    ("成立年份", "Founded", "Année de Fondation"),
    ("我们的故事", "Our Story", "Notre Histoire"),
    ("从一个想法到一个平台", "From an Idea to a Platform", "D'une Idée à une Plateforme"),
    ("我们的图书管理系统诞生于对知识传播的热爱。从最初的构想到如今功能完善的平台，我们始终坚持以用户为中心，不断优化产品体验。",
     "Our book management system was born from a love of knowledge sharing. From the initial concept to today's fully-featured platform, we have always stayed user-centered, continuously optimizing the experience.",
     "Notre système de gestion de livres est né d'un amour du partage des connaissances. Du concept initial à la plateforme complète d'aujourd'hui, nous restons centrés sur l'utilisateur, optimisant continuellement l'expérience."),
    ("我们相信，每一本书都承载着智慧与力量。通过我们的平台，读者可以轻松发现、购买和管理他们喜爱的书籍。",
     "We believe every book carries wisdom and power. Through our platform, readers can easily discover, purchase, and manage their favorite books.",
     "Nous croyons que chaque livre porte sagesse et puissance. Grâce à notre plateforme, les lecteurs peuvent facilement découvrir, acheter et gérer leurs livres préférés."),
    ("我们的价值观", "Our Values", "Nos Valeurs"),
    ("驱动我们前行的核心理念", "Core Principles That Drive Us Forward", "Principes Fondamentaux Qui Nous Font Avancer"),
    ("创新", "Innovation", "Innovation"),
    ("我们不断探索新技术和新方法，为用户提供最前沿的图书管理体验。",
     "We constantly explore new technologies and methods to provide users with cutting-edge book management experiences.",
     "Nous explorons constamment de nouvelles technologies et méthodes pour offrir aux utilisateurs des expériences de gestion de livres à la pointe."),
    ("热情", "Passion", "Passion"),
    ("对阅读的热爱驱动着我们，我们希望将这份热情传递给每一位用户。",
     "Our love for reading drives us, and we hope to pass this passion on to every user.",
     "Notre amour de la lecture nous motive, et nous espérons transmettre cette passion à chaque utilisateur."),
    ("可靠", "Reliable", "Fiable"),
    ("我们承诺提供稳定、安全的服务，让用户可以放心地使用我们的平台。",
     "We promise to provide stable, secure services so users can use our platform with confidence.",
     "Nous promettons de fournir des services stables et sécurisés pour que les utilisateurs puissent utiliser notre plateforme en toute confiance."),
    ("以用户为中心", "User-Centered", "Centré sur l'Utilisateur"),
    ("用户的需求和体验始终是我们决策的核心，我们倾听每一个声音。",
     "User needs and experience are always at the core of our decisions. We listen to every voice.",
     "Les besoins et l'expérience des utilisateurs sont toujours au cœur de nos décisions. Nous écoutons chaque voix."),
    ("图书数量", "Total Books", "Nombre de Livres"),
    ("作者数量", "Total Authors", "Nombre d'Auteurs"),
    ("我们的团队", "Our Team", "Notre Équipe"),
    ("专业的团队，卓越的服务", "Professional Team, Excellent Service", "Équipe Professionnelle, Service Excellent"),
    ("创始人", "Founder", "Fondateur"),
    ("产品设计", "Product Design", "Conception Produit"),
    ("技术团队", "Tech Team", "Équipe Technique"),
    ("全栈开发", "Full-Stack Development", "Développement Full-Stack"),
    ("客服团队", "Support Team", "Équipe Support"),
    ("客户支持", "Customer Support", "Support Client"),
    ("准备好开始了吗？", "Ready to Get Started?", "Prêt à Commencer ?"),
    ("浏览我们的图书目录，发现您的下一本好书。", "Browse our book catalog and discover your next great read.", "Parcourez notre catalogue de livres et découvrez votre prochaine lecture."),

    # services.html
    ("全方位的图书服务", "Comprehensive Book Services", "Services Complets de Livres"),
    ("从图书搜索到订单管理，我们提供一站式的智能图书服务，让您的阅读体验更加便捷和愉悦。",
     "From book search to order management, we provide one-stop intelligent book services to make your reading experience more convenient and enjoyable.",
     "De la recherche de livres à la gestion des commandes, nous offrons des services intelligents tout-en-un pour rendre votre expérience de lecture plus pratique et agréable."),
    ("核心服务", "Core Services", "Services Principaux"),
    ("我们为您提供什么", "What We Offer", "Ce Que Nous Offrons"),
    ("智能图书搜索", "Smart Book Search", "Recherche Intelligente de Livres"),
    ("通过关键字、作者或出版社快速搜索您需要的图书，智能排序让您更快找到心仪的书籍。",
     "Quickly search for books by keyword, author, or publisher. Smart sorting helps you find your desired books faster.",
     "Recherchez rapidement des livres par mot-clé, auteur ou éditeur. Le tri intelligent vous aide à trouver vos livres plus rapidement."),
    ("多维度搜索", "Multi-Dimensional Search", "Recherche Multi-Dimensionnelle"),
    ("智能排序", "Smart Sorting", "Tri Intelligent"),
    ("实时结果", "Real-Time Results", "Résultats en Temps Réel"),
    ("在线购书", "Online Book Shopping", "Achat de Livres en Ligne"),
    ("便捷的购物车系统，支持多种支付方式，让您轻松完成图书购买。",
     "Convenient shopping cart system supporting multiple payment methods for easy book purchases.",
     "Système de panier pratique supportant plusieurs méthodes de paiement pour des achats de livres faciles."),
    ("安全支付", "Secure Payment", "Paiement Sécurisé"),
    ("购物车管理", "Cart Management", "Gestion du Panier"),
    ("电子书下载", "E-Book Download", "Téléchargement d'E-Books"),
    ("购买后即可下载电子版本，随时随地享受阅读的乐趣。",
     "Download digital versions after purchase and enjoy reading anytime, anywhere.",
     "Téléchargez les versions numériques après l'achat et profitez de la lecture partout et à tout moment."),
    ("即时下载", "Instant Download", "Téléchargement Instantané"),
    ("多格式支持", "Multi-Format Support", "Support Multi-Format"),
    ("永久访问", "Permanent Access", "Accès Permanent"),
    ("图书管理", "Book Management", "Gestion des Livres"),
    ("强大的后台管理系统，帮助管理员高效管理图书、作者和出版社信息。",
     "Powerful backend management system helping administrators efficiently manage books, authors, and publisher information.",
     "Système de gestion backend puissant aidant les administrateurs à gérer efficacement les livres, auteurs et éditeurs."),
    ("库存管理", "Inventory Management", "Gestion des Stocks"),
    ("数据分析", "Data Analysis", "Analyse de Données"),
    ("报表导出", "Report Export", "Export de Rapports"),
    ("多语言支持", "Multilingual Support", "Support Multilingue"),
    ("支持中文、英文和法文，为全球用户提供无障碍的浏览体验。",
     "Supporting Chinese, English, and French for a barrier-free browsing experience for users worldwide.",
     "Prise en charge du chinois, de l'anglais et du français pour une expérience de navigation sans obstacle pour les utilisateurs du monde entier."),
    ("三语切换", "Trilingual Switching", "Commutation Trilingue"),
    ("实时翻译", "Real-Time Translation", "Traduction en Temps Réel"),
    ("本地化体验", "Localized Experience", "Expérience Localisée"),
    ("专业的客服团队随时为您解答问题，确保您获得最佳的服务体验。",
     "Professional customer service team ready to answer your questions and ensure the best service experience.",
     "Équipe de service client professionnelle prête à répondre à vos questions et assurer la meilleure expérience de service."),
    ("在线客服", "Online Service", "Service en Ligne"),
    ("邮件支持", "Email Support", "Support par Email"),
    ("常见问题", "FAQ", "FAQ"),
    ("购书流程", "Purchase Process", "Processus d'Achat"),
    ("简单四步，轻松购书", "Four Simple Steps to Easy Book Shopping", "Quatre Étapes Simples pour Acheter des Livres"),
    ("在我们的图书目录中搜索和浏览您感兴趣的书籍。",
     "Search and browse books you're interested in from our catalog.",
     "Recherchez et parcourez les livres qui vous intéressent dans notre catalogue."),
    ("将喜欢的图书加入购物车，随时调整数量。",
     "Add your favorite books to the cart and adjust quantities anytime.",
     "Ajoutez vos livres préférés au panier et ajustez les quantités à tout moment."),
    ("安全结算", "Secure Checkout", "Paiement Sécurisé"),
    ("选择支付方式，完成安全的在线结算。",
     "Choose your payment method and complete a secure online checkout.",
     "Choisissez votre méthode de paiement et effectuez un paiement en ligne sécurisé."),
    ("享受阅读", "Enjoy Reading", "Profitez de la Lecture"),
    ("收到图书后，开始您的阅读之旅！",
     "After receiving your books, start your reading journey!",
     "Après avoir reçu vos livres, commencez votre voyage de lecture !"),
    ("立即开始您的阅读之旅", "Start Your Reading Journey Now", "Commencez Votre Voyage de Lecture Maintenant"),
    ("探索我们的图书目录，找到您的下一本好书。",
     "Explore our book catalog and find your next great read.",
     "Explorez notre catalogue de livres et trouvez votre prochaine lecture."),

    # contact.html
    ("与我们取得联系", "Get in Touch", "Contactez-Nous"),
    ("如果您有任何问题、建议或合作意向，请随时与我们联系。我们的团队将尽快回复您。",
     "If you have any questions, suggestions, or collaboration interests, please feel free to contact us. Our team will respond as soon as possible.",
     "Si vous avez des questions, des suggestions ou des intérêts de collaboration, n'hésitez pas à nous contacter. Notre équipe vous répondra dans les plus brefs délais."),
    ("发送消息", "Send Message", "Envoyer le Message"),
    ("给我们留言", "Leave Us a Message", "Laissez-Nous un Message"),
    ("感谢您的留言！我们会尽快回复您。", "Thank you for your message! We will reply as soon as possible.", "Merci pour votre message ! Nous vous répondrons dans les plus brefs délais."),
    ("您的姓名", "Your Name", "Votre Nom"),
    ("您的邮箱", "Your Email", "Votre Email"),
    ("主题", "Subject", "Sujet"),
    ("您的留言", "Your Message", "Votre Message"),
    ("其他联系方式", "Other Contact Methods", "Autres Moyens de Contact"),
    ("关注我们", "Follow Us", "Suivez-Nous"),

    # blog.html
    ("最新文章与资讯", "Latest Articles & News", "Derniers Articles et Actualités"),
    ("探索我们的博客，获取图书推荐、阅读技巧、行业动态等精彩内容。",
     "Explore our blog for book recommendations, reading tips, industry news, and more.",
     "Explorez notre blog pour des recommandations de livres, des astuces de lecture, des actualités du secteur, et plus encore."),
    ("搜索文章...", "Search articles...", "Rechercher des articles..."),
    ("精选推荐", "Featured", "Sélection"),
    ("精选文章", "Featured Articles", "Articles en Vedette"),
    ("精选", "Featured", "En Vedette"),
    ("搜索结果", "Search Results", "Résultats de Recherche"),
    ("篇文章", "articles", "articles"),
    ("阅读更多", "Read More", "Lire la Suite"),
    ("暂无文章", "No Articles", "Aucun Article"),
    ("敬请期待更多精彩内容", "Stay tuned for more exciting content", "Restez à l'écoute pour plus de contenu passionnant"),
    ("文章分类", "Categories", "Catégories"),
    ("全部文章", "All Articles", "Tous les Articles"),
    ("关于博客", "About Blog", "À Propos du Blog"),
    ("在这里，我们分享关于图书、阅读和技术的最新资讯。关注我们，获取更多精彩内容。",
     "Here, we share the latest information about books, reading, and technology. Follow us for more exciting content.",
     "Ici, nous partageons les dernières informations sur les livres, la lecture et la technologie. Suivez-nous pour plus de contenu passionnant."),

    # blog_detail.html
    ("次浏览", "views", "vues"),
    ("分钟阅读", "min read", "min de lecture"),
    ("文章作者", "Article Author", "Auteur de l'Article"),
    ("分享文章", "Share Article", "Partager l'Article"),
    ("返回博客列表", "Back to Blog", "Retour au Blog"),
    ("相关文章", "Related Articles", "Articles Associés"),
    ("您可能还感兴趣", "You May Also Be Interested In", "Vous Pourriez Aussi Être Intéressé Par"),
]


def append_to_po(filepath, entries, lang):
    """Append entries to a .po file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        existing = f.read()

    # Get existing msgids to avoid duplicates
    existing_msgids = set()
    for line in existing.split('\n'):
        if line.startswith('msgid "') and line != 'msgid ""':
            msgid = line[7:-1]  # Extract between quotes
            existing_msgids.add(msgid)

    new_lines = []
    added = 0
    skipped = 0

    for entry in entries:
        msgid = entry[0]
        if lang == 'en':
            msgstr = entry[1]
        else:
            msgstr = entry[2]

        if msgid in existing_msgids:
            skipped += 1
            continue

        new_lines.append('')
        new_lines.append(f'msgid "{msgid}"')
        new_lines.append(f'msgstr "{msgstr}"')
        existing_msgids.add(msgid)
        added += 1

    if new_lines:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write('\n')
            # Add section header
            f.write('\n# ============================================================')
            f.write('\n# New pages: About, Services, Contact, Blog')
            f.write('\n# ============================================================')
            f.write('\n'.join(new_lines))
            f.write('\n')

    print(f'{lang}: Added {added} entries, skipped {skipped} duplicates')


def unescape(s):
    """Unescape .po string."""
    s = s.replace('\\n', '\n')
    s = s.replace('\\t', '\t')
    s = s.replace('\\"', '"')
    s = s.replace('\\\\', '\\')
    return s


def compile_po_to_mo(po_path, mo_path):
    """Compile .po file to .mo binary format."""
    messages = []

    with open(po_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    msgid = None
    msgstr = None
    in_msgid = False
    in_msgstr = False

    for line in lines:
        line = line.strip()

        if line.startswith('msgid "'):
            if msgid is not None and msgstr is not None:
                messages.append((unescape(msgid), unescape(msgstr)))
            msgid = line[7:-1]
            in_msgid = True
            in_msgstr = False
        elif line.startswith('msgstr "'):
            msgstr = line[8:-1]
            in_msgid = False
            in_msgstr = True
        elif line.startswith('"') and line.endswith('"'):
            continuation = line[1:-1]
            if in_msgid:
                msgid += continuation
            elif in_msgstr:
                msgstr += continuation
        elif line == '' or line.startswith('#'):
            if msgid is not None and msgstr is not None:
                messages.append((unescape(msgid), unescape(msgstr)))
                msgid = None
                msgstr = None
            in_msgid = False
            in_msgstr = False

    # Don't forget the last entry
    if msgid is not None and msgstr is not None:
        messages.append((unescape(msgid), unescape(msgstr)))

    # Filter out empty msgid (header) but keep it separate
    header = ''
    real_messages = []
    for mid, mstr in messages:
        if mid == '':
            header = mstr
        else:
            if mstr:  # Only include entries with translations
                real_messages.append((mid, mstr))

    # Sort messages by msgid (required by .mo format)
    real_messages.sort(key=lambda x: x[0])

    # Build .mo file
    # Add header as empty string entry
    all_messages = [('', header)] + real_messages

    num_strings = len(all_messages)

    # .mo file format offsets
    keystart = 7 * 4
    valuestart = keystart + num_strings * 8

    koffsets = []
    voffsets = []
    keys = b''
    values = b''

    for msgid_str, msgstr_str in all_messages:
        msgid_bytes = msgid_str.encode('utf-8')
        msgstr_bytes = msgstr_str.encode('utf-8')

        koffsets.append((len(msgid_bytes), len(keys) + keystart + num_strings * 16))
        voffsets.append((len(msgstr_bytes), len(values) + valuestart + num_strings * 16))

        # Calculate actual data offset later
        keys += msgid_bytes + b'\x00'
        values += msgstr_bytes + b'\x00'

    # Recalculate offsets with actual data positions
    keys_offset = 7 * 4 + num_strings * 8 * 2
    values_offset = keys_offset + len(keys)

    koffsets2 = []
    voffsets2 = []
    kpos = keys_offset
    vpos = values_offset

    for msgid_str, msgstr_str in all_messages:
        msgid_bytes = msgid_str.encode('utf-8')
        msgstr_bytes = msgstr_str.encode('utf-8')
        koffsets2.append((len(msgid_bytes), kpos))
        voffsets2.append((len(msgstr_bytes), vpos))
        kpos += len(msgid_bytes) + 1
        vpos += len(msgstr_bytes) + 1

    output = b''
    # Magic number
    output += struct.pack('I', 0x950412de)
    # Version
    output += struct.pack('I', 0)
    # Number of strings
    output += struct.pack('I', num_strings)
    # Offset of original strings table
    output += struct.pack('I', 7 * 4)
    # Offset of translated strings table
    output += struct.pack('I', 7 * 4 + num_strings * 8)
    # Size of hashing table (0 = no hash table)
    output += struct.pack('I', 0)
    # Offset of hashing table
    output += struct.pack('I', 0)

    # Original strings table
    for length, offset in koffsets2:
        output += struct.pack('II', length, offset)

    # Translated strings table
    for length, offset in voffsets2:
        output += struct.pack('II', length, offset)

    # Keys data
    output += keys
    # Values data
    output += values

    os.makedirs(os.path.dirname(mo_path), exist_ok=True)
    with open(mo_path, 'wb') as f:
        f.write(output)

    print(f'Compiled {mo_path}: {num_strings} entries ({len(output)} bytes)')


if __name__ == '__main__':
    base = os.path.dirname(os.path.abspath(__file__))

    # Append new entries
    en_po = os.path.join(base, 'locale', 'en', 'LC_MESSAGES', 'django.po')
    fr_po = os.path.join(base, 'locale', 'fr', 'LC_MESSAGES', 'django.po')

    append_to_po(en_po, NEW_ENTRIES, 'en')
    append_to_po(fr_po, NEW_ENTRIES, 'fr')

    # Compile to .mo
    en_mo = os.path.join(base, 'locale', 'en', 'LC_MESSAGES', 'django.mo')
    fr_mo = os.path.join(base, 'locale', 'fr', 'LC_MESSAGES', 'django.mo')

    compile_po_to_mo(en_po, en_mo)
    compile_po_to_mo(fr_po, fr_mo)

    print('\nDone! All translations updated and compiled.')
