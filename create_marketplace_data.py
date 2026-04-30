"""Create sample marketplace data for demonstration."""
import os
os.environ['DEBUG'] = 'True'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')

import django
django.setup()

from marketplace.models import Category, Product, Course, SupermarketItem
from decimal import Decimal

DB = 'marketplace'

# Clear existing data
MarketplaceOrderItem = __import__('marketplace.models', fromlist=['MarketplaceOrderItem']).MarketplaceOrderItem
MarketplaceOrder = __import__('marketplace.models', fromlist=['MarketplaceOrder']).MarketplaceOrder
MarketplaceOrderItem.objects.using(DB).all().delete()
MarketplaceOrder.objects.using(DB).all().delete()
SupermarketItem.objects.using(DB).all().delete()
Course.objects.using(DB).all().delete()
Product.objects.using(DB).all().delete()
Category.objects.using(DB).all().delete()

print("Creating categories...")

# Product categories
cat_electronics = Category.objects.using(DB).create(
    name='电子产品', name_en='Electronics', slug='electronics',
    description='Latest electronics and gadgets', section='products', display_order=1
)
cat_accessories = Category.objects.using(DB).create(
    name='配件', name_en='Accessories', slug='accessories',
    description='Phone and computer accessories', section='products', display_order=2
)
cat_stationery = Category.objects.using(DB).create(
    name='文具', name_en='Stationery', slug='stationery',
    description='Office and school supplies', section='products', display_order=3
)

# Course categories
cat_programming = Category.objects.using(DB).create(
    name='编程开发', name_en='Programming', slug='programming',
    description='Learn to code', section='courses', display_order=1
)
cat_design = Category.objects.using(DB).create(
    name='设计创意', name_en='Design', slug='design',
    description='Creative design courses', section='courses', display_order=2
)
cat_business = Category.objects.using(DB).create(
    name='商业管理', name_en='Business', slug='business',
    description='Business and management courses', section='courses', display_order=3
)
cat_language = Category.objects.using(DB).create(
    name='语言学习', name_en='Languages', slug='languages',
    description='Language learning courses', section='courses', display_order=4
)

# Supermarket categories
cat_fruits = Category.objects.using(DB).create(
    name='水果', name_en='Fruits', slug='fruits',
    description='Fresh fruits', section='supermarket', display_order=1
)
cat_beverages = Category.objects.using(DB).create(
    name='饮品', name_en='Beverages', slug='beverages',
    description='Drinks and beverages', section='supermarket', display_order=2
)
cat_snacks = Category.objects.using(DB).create(
    name='零食', name_en='Snacks', slug='snacks',
    description='Snacks and treats', section='supermarket', display_order=3
)
cat_dairy = Category.objects.using(DB).create(
    name='乳制品', name_en='Dairy', slug='dairy',
    description='Milk and dairy products', section='supermarket', display_order=4
)

print(f"Created {Category.objects.using(DB).count()} categories")

# ---- PRODUCTS ----
print("Creating products...")

products_data = [
    {
        'name': '无线蓝牙耳机', 'name_en': 'Wireless Bluetooth Earbuds',
        'slug': 'wireless-bluetooth-earbuds',
        'description': '高品质无线蓝牙耳机，支持降噪功能，续航长达8小时。舒适佩戴设计，适合运动和日常使用。',
        'price': Decimal('199.00'), 'original_price': Decimal('299.00'),
        'category': cat_electronics, 'stock': 150, 'brand': 'SoundPro',
        'condition': 'new', 'is_featured': True, 'sales_count': 328, 'views_count': 2156
    },
    {
        'name': '智能手表', 'name_en': 'Smart Watch Pro',
        'slug': 'smart-watch-pro',
        'description': '多功能智能手表，支持心率监测、运动追踪、来电提醒。防水防尘，电池续航7天。',
        'price': Decimal('599.00'), 'original_price': Decimal('899.00'),
        'category': cat_electronics, 'stock': 80, 'brand': 'TechWear',
        'condition': 'new', 'is_featured': True, 'sales_count': 156, 'views_count': 1843
    },
    {
        'name': '便携式充电宝', 'name_en': 'Portable Power Bank 20000mAh',
        'slug': 'portable-power-bank-20000',
        'description': '20000mAh大容量便携充电宝，支持快充协议，双USB输出端口，轻薄便携设计。',
        'price': Decimal('129.00'), 'original_price': Decimal('199.00'),
        'category': cat_electronics, 'stock': 200, 'brand': 'PowerMax',
        'condition': 'new', 'is_featured': False, 'sales_count': 512, 'views_count': 3201
    },
    {
        'name': '手机壳 - 防摔保护套', 'name_en': 'Phone Case - Shockproof',
        'slug': 'phone-case-shockproof',
        'description': '军事级防摔手机壳，TPU+PC双层保护，精准开孔，支持无线充电。多种颜色可选。',
        'price': Decimal('39.00'), 'original_price': Decimal('69.00'),
        'category': cat_accessories, 'stock': 500, 'brand': 'ArmorCase',
        'condition': 'new', 'is_featured': False, 'sales_count': 890, 'views_count': 4520
    },
    {
        'name': '机械键盘', 'name_en': 'Mechanical Keyboard RGB',
        'slug': 'mechanical-keyboard-rgb',
        'description': '87键紧凑布局机械键盘，Cherry MX轴体，RGB背光，PBT键帽。适合办公和游戏。',
        'price': Decimal('349.00'), 'original_price': Decimal('499.00'),
        'category': cat_electronics, 'stock': 60, 'brand': 'KeyMaster',
        'condition': 'new', 'is_featured': True, 'sales_count': 234, 'views_count': 1567
    },
    {
        'name': '高级钢笔套装', 'name_en': 'Premium Fountain Pen Set',
        'slug': 'premium-fountain-pen-set',
        'description': '精美钢笔礼盒套装，含钢笔、墨水和替换笔尖。适合书法练习和商务签字。',
        'price': Decimal('168.00'), 'original_price': Decimal('238.00'),
        'category': cat_stationery, 'stock': 45, 'brand': 'PenCraft',
        'condition': 'new', 'is_featured': True, 'sales_count': 78, 'views_count': 890
    },
    {
        'name': 'USB-C 扩展坞', 'name_en': 'USB-C Docking Station',
        'slug': 'usb-c-docking-station',
        'description': '12合1 USB-C扩展坞，支持4K HDMI、千兆以太网、SD读卡器、多USB端口。',
        'price': Decimal('259.00'), 'original_price': Decimal('399.00'),
        'category': cat_accessories, 'stock': 120, 'brand': 'ConnectPro',
        'condition': 'new', 'is_featured': False, 'sales_count': 167, 'views_count': 1234
    },
    {
        'name': '笔记本支架', 'name_en': 'Laptop Stand Adjustable',
        'slug': 'laptop-stand-adjustable',
        'description': '铝合金笔记本支架，多角度可调，折叠便携，散热设计，兼容各种尺寸笔记本。',
        'price': Decimal('89.00'), 'original_price': Decimal('149.00'),
        'category': cat_accessories, 'stock': 180, 'brand': 'DeskPro',
        'condition': 'new', 'is_featured': False, 'sales_count': 345, 'views_count': 2100
    },
]

for data in products_data:
    Product.objects.using(DB).create(**data)

print(f"Created {Product.objects.using(DB).count()} products")

# ---- COURSES ----
print("Creating courses...")

courses_data = [
    {
        'title': 'Python 全栈开发', 'title_en': 'Python Full Stack Development',
        'slug': 'python-full-stack-development',
        'description': '从零开始学习Python全栈开发，涵盖Django、Flask、数据库设计、前端技术和部署。适合初学者和有一定基础的开发者。',
        'price': Decimal('299.00'), 'original_price': Decimal('599.00'),
        'category': cat_programming, 'instructor': '张明教授',
        'duration_hours': Decimal('48.5'), 'lessons_count': 120, 'level': 'beginner',
        'language': '中文', 'is_featured': True, 'enrollment_count': 2340, 'rating': Decimal('4.8')
    },
    {
        'title': 'React + Next.js 现代前端', 'title_en': 'Modern Frontend with React & Next.js',
        'slug': 'react-nextjs-modern-frontend',
        'description': '深入学习React和Next.js，掌握组件设计、状态管理、SSR/SSG、API路由等现代前端开发技术。',
        'price': Decimal('399.00'), 'original_price': Decimal('699.00'),
        'category': cat_programming, 'instructor': 'David Chen',
        'duration_hours': Decimal('36.0'), 'lessons_count': 85, 'level': 'intermediate',
        'language': '中文/English', 'is_featured': True, 'enrollment_count': 1560, 'rating': Decimal('4.7')
    },
    {
        'title': 'UI/UX 设计大师课', 'title_en': 'UI/UX Design Masterclass',
        'slug': 'ui-ux-design-masterclass',
        'description': '学习专业UI/UX设计流程，包括用户研究、线框图、原型设计、设计系统和可用性测试。使用Figma实战。',
        'price': Decimal('259.00'), 'original_price': Decimal('499.00'),
        'category': cat_design, 'instructor': '李雅琪',
        'duration_hours': Decimal('32.0'), 'lessons_count': 68, 'level': 'all',
        'language': '中文', 'is_featured': True, 'enrollment_count': 980, 'rating': Decimal('4.9')
    },
    {
        'title': '数字营销实战', 'title_en': 'Digital Marketing in Practice',
        'slug': 'digital-marketing-practice',
        'description': '全面掌握数字营销策略，包括SEO、SEM、社交媒体营销、内容营销和数据分析。',
        'price': Decimal('199.00'), 'original_price': Decimal('399.00'),
        'category': cat_business, 'instructor': '王晓明',
        'duration_hours': Decimal('24.0'), 'lessons_count': 52, 'level': 'beginner',
        'language': '中文', 'is_featured': False, 'enrollment_count': 750, 'rating': Decimal('4.5')
    },
    {
        'title': '商务英语精进', 'title_en': 'Business English Advanced',
        'slug': 'business-english-advanced',
        'description': '提升商务英语沟通能力，涵盖邮件写作、会议主持、演讲技巧和谈判用语。',
        'price': Decimal('179.00'), 'original_price': Decimal('349.00'),
        'category': cat_language, 'instructor': 'Sarah Williams',
        'duration_hours': Decimal('20.0'), 'lessons_count': 40, 'level': 'intermediate',
        'language': 'English/中文', 'is_featured': True, 'enrollment_count': 1230, 'rating': Decimal('4.6')
    },
    {
        'title': '数据科学与机器学习', 'title_en': 'Data Science & Machine Learning',
        'slug': 'data-science-machine-learning',
        'description': '使用Python进行数据分析和机器学习。涵盖NumPy、Pandas、Scikit-learn、TensorFlow。',
        'price': Decimal('499.00'), 'original_price': Decimal('899.00'),
        'category': cat_programming, 'instructor': '刘博士',
        'duration_hours': Decimal('56.0'), 'lessons_count': 140, 'level': 'advanced',
        'language': '中文', 'is_featured': False, 'enrollment_count': 890, 'rating': Decimal('4.7')
    },
]

for data in courses_data:
    Course.objects.using(DB).create(**data)

print(f"Created {Course.objects.using(DB).count()} courses")

# ---- SUPERMARKET ITEMS ----
print("Creating supermarket items...")

supermarket_data = [
    {
        'name': '新鲜草莓', 'name_en': 'Fresh Strawberries',
        'slug': 'fresh-strawberries',
        'description': '当季新鲜草莓，甜度高，果肉饱满。产地直供，品质保证。',
        'price': Decimal('29.90'), 'original_price': Decimal('39.90'),
        'category': cat_fruits, 'stock': 300, 'unit': 'box',
        'brand': '果鲜生', 'origin': '云南', 'is_organic': True,
        'is_featured': True, 'sales_count': 1200
    },
    {
        'name': '进口车厘子', 'name_en': 'Imported Cherries',
        'slug': 'imported-cherries',
        'description': '智利进口车厘子，JJ级大果，皮薄多汁，口感脆甜。',
        'price': Decimal('89.00'), 'original_price': Decimal('129.00'),
        'category': cat_fruits, 'stock': 150, 'unit': 'kg',
        'brand': '', 'origin': '智利', 'is_organic': False,
        'is_featured': True, 'sales_count': 680
    },
    {
        'name': '有机纯牛奶', 'name_en': 'Organic Pure Milk',
        'slug': 'organic-pure-milk',
        'description': '有机牧场新鲜牛奶，无添加，高钙高蛋白。适合全家饮用。',
        'price': Decimal('68.00'), 'original_price': Decimal('88.00'),
        'category': cat_dairy, 'stock': 400, 'unit': 'box',
        'brand': '蒙牛', 'origin': '内蒙古', 'is_organic': True,
        'is_featured': True, 'sales_count': 2350
    },
    {
        'name': '精品咖啡豆', 'name_en': 'Premium Coffee Beans',
        'slug': 'premium-coffee-beans',
        'description': '阿拉比卡精品咖啡豆，中度烘焙，风味平衡。适合手冲和意式咖啡。',
        'price': Decimal('78.00'), 'original_price': Decimal('98.00'),
        'category': cat_beverages, 'stock': 200, 'unit': 'bag',
        'brand': 'BeanMaster', 'origin': '哥伦比亚', 'is_organic': False,
        'is_featured': False, 'sales_count': 560
    },
    {
        'name': '混合坚果', 'name_en': 'Mixed Nuts Premium',
        'slug': 'mixed-nuts-premium',
        'description': '精选6种坚果混合装：核桃、腰果、杏仁、夏威夷果、碧根果、榛子。',
        'price': Decimal('49.90'), 'original_price': Decimal('79.90'),
        'category': cat_snacks, 'stock': 350, 'unit': 'bag',
        'brand': '坚果大王', 'origin': '多国进口', 'is_organic': False,
        'is_featured': True, 'sales_count': 1890
    },
    {
        'name': '冷压果汁套装', 'name_en': 'Cold Pressed Juice Set',
        'slug': 'cold-pressed-juice-set',
        'description': '6瓶装冷压果汁，含橙汁、苹果汁、胡萝卜汁等。无添加剂，新鲜制作。',
        'price': Decimal('118.00'), 'original_price': Decimal('168.00'),
        'category': cat_beverages, 'stock': 100, 'unit': 'box',
        'brand': '鲜果坊', 'origin': '上海', 'is_organic': True,
        'is_featured': False, 'sales_count': 340
    },
    {
        'name': '希腊酸奶', 'name_en': 'Greek Yogurt Natural',
        'slug': 'greek-yogurt-natural',
        'description': '浓稠希腊式酸奶，高蛋白低脂肪。原味无糖，可搭配水果和蜂蜜。',
        'price': Decimal('35.00'), 'original_price': Decimal('45.00'),
        'category': cat_dairy, 'stock': 250, 'unit': 'box',
        'brand': 'YogurtPro', 'origin': '上海', 'is_organic': False,
        'is_featured': False, 'sales_count': 890
    },
    {
        'name': '有机苹果', 'name_en': 'Organic Apples',
        'slug': 'organic-apples',
        'description': '有机种植红富士苹果，脆甜多汁，无农药残留。产地直发，新鲜到家。',
        'price': Decimal('45.00'), 'original_price': Decimal('58.00'),
        'category': cat_fruits, 'stock': 200, 'unit': 'kg',
        'brand': '果然好', 'origin': '烟台', 'is_organic': True,
        'is_featured': False, 'sales_count': 760
    },
]

for data in supermarket_data:
    SupermarketItem.objects.using(DB).create(**data)

print(f"Created {SupermarketItem.objects.using(DB).count()} supermarket items")

print("\n=== Sample Data Summary ===")
print(f"Categories: {Category.objects.using(DB).count()}")
print(f"Products: {Product.objects.using(DB).count()}")
print(f"Courses: {Course.objects.using(DB).count()}")
print(f"Supermarket Items: {SupermarketItem.objects.using(DB).count()}")
print("Sample data created successfully!")
