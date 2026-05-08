"""Append missing translations to EN and FR .po files."""

en_entries = [
    ("卖家导航", "Seller navigation"),
    ("店铺前台", "Store front"),
    ("图书管理", "Books"),
    ("商品列表", "Product list"),
    ("课程列表", "Course list"),
    ("客户消息", "Customer messages"),
    ("总览", "Overview"),
    ("店铺设置", "Store settings"),
    ("数据概览", "Data overview"),
    ("卖家仪表板", "Vendor Dashboard"),
    ("近7天收入趋势", "Revenue Trend (Last 7 Days)"),
    ("商品分类分布", "Product Category Distribution"),
    ("收入构成", "Revenue Breakdown"),
    ("商品收入", "Product Revenue"),
    ("课程收入", "Course Revenue"),
    ("上架商品", "Active Products"),
    ("下架商品", "Inactive Products"),
    ("发布课程", "Published Courses"),
    ("课程注册", "Course Enrollments"),
    ("热销商品 TOP 5", "Top 5 Best Sellers"),
    ("暂无销量数据", "No sales data"),
    ("匿名", "Anonymous"),
    ("管理商品", "Manage Products"),
    ("管理课程", "Manage Courses"),
    ("已售", "sold"),
    ("暂无分类数据", "No category data"),
    ("数据概览 · 店铺与货架 · 订单与设置", "Overview · Store & Inventory · Orders & Settings"),
]

fr_entries = [
    ("卖家导航", "Navigation vendeur"),
    ("店铺前台", "Vitrine"),
    ("图书管理", "Livres"),
    ("商品列表", "Liste de produits"),
    ("课程列表", "Liste des cours"),
    ("客户消息", "Messages clients"),
    ("总览", "Vue d'ensemble"),
    ("店铺设置", "Paramètres de la boutique"),
    ("数据概览", "Aperçu des données"),
    ("卖家仪表板", "Tableau de bord"),
    ("近7天收入趋势", "Tendance des revenus (7 derniers jours)"),
    ("商品分类分布", "Répartition par catégorie"),
    ("收入构成", "Composition des revenus"),
    ("商品收入", "Revenus produits"),
    ("课程收入", "Revenus cours"),
    ("上架商品", "Produits actifs"),
    ("下架商品", "Produits inactifs"),
    ("发布课程", "Cours publiés"),
    ("课程注册", "Inscriptions aux cours"),
    ("热销商品 TOP 5", "Top 5 meilleures ventes"),
    ("暂无销量数据", "Aucune donnée de vente"),
    ("匿名", "Anonyme"),
    ("管理商品", "Gérer les produits"),
    ("管理课程", "Gérer les cours"),
    ("已售", "vendu(s)"),
    ("暂无分类数据", "Aucune donnée de catégorie"),
    ("数据概览 · 店铺与货架 · 订单与设置", "Aperçu · Boutique & Stock · Commandes & Paramètres"),
]


def append_missing(po_path, entries):
    with open(po_path, encoding='utf-8') as f:
        content = f.read()

    new_entries = []
    for msgid, msgstr in entries:
        pattern = f'msgid "{msgid}"\nmsgstr "'
        if pattern not in content:
            new_entries.append((msgid, msgstr))
            print(f"  Adding: [{msgid}] -> [{msgstr}]")
        else:
            print(f"  Already exists: [{msgid}]")

    if new_entries:
        addition = "\n"
        for msgid, msgstr in new_entries:
            addition += f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n'
        with open(po_path, 'a', encoding='utf-8') as f:
            f.write(addition)
        print(f"  -> Added {len(new_entries)} entries to {po_path}")
    else:
        print(f"  -> No new entries needed for {po_path}")


print("=== EN .po ===")
append_missing('locale/en/LC_MESSAGES/django.po', en_entries)

print("\n=== FR .po ===")
append_missing('locale/fr/LC_MESSAGES/django.po', fr_entries)

print("\nDone.")
