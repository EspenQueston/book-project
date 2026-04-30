from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid


class Category(models.Model):
    """Marketplace category with section support."""
    SECTION_CHOICES = [
        ('products', '商品'),
        ('courses', '课程'),
        ('supermarket', '超市'),
    ]

    name = models.CharField(max_length=100, verbose_name='分类名称')
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, verbose_name='描述')
    image = models.ImageField(upload_to='marketplace/categories/', blank=True, null=True)
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, verbose_name='所属版块')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')
    display_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_category'
        verbose_name = '市场分类'
        verbose_name_plural = '市场分类'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def get_display_name(self):
        return self.name


class Product(models.Model):
    """Physical products for sale."""
    CONDITION_CHOICES = [
        ('new', '全新'),
        ('like_new', '几乎全新'),
        ('used', '二手'),
        ('refurbished', '翻新'),
    ]

    vendor = models.ForeignKey('manager.Vendor', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='products', verbose_name='卖家')
    name = models.CharField(max_length=200, verbose_name='商品名称')
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(verbose_name='商品描述')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='价格')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='原价')
    image = models.ImageField(upload_to='marketplace/products/', blank=True, null=True, verbose_name='主图')
    image_2 = models.ImageField(upload_to='marketplace/products/', blank=True, null=True, verbose_name='图片2')
    image_3 = models.ImageField(upload_to='marketplace/products/', blank=True, null=True, verbose_name='图片3')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    stock = models.PositiveIntegerField(default=0, verbose_name='库存')
    sku = models.CharField(max_length=50, unique=True, blank=True, verbose_name='SKU')
    brand = models.CharField(max_length=100, blank=True, verbose_name='品牌')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new', verbose_name='状况')
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='重量(kg)')
    is_featured = models.BooleanField(default=False, verbose_name='推荐商品')
    is_active = models.BooleanField(default=True, verbose_name='是否上架')
    sales_count = models.PositiveIntegerField(default=0, verbose_name='销量')
    views_count = models.PositiveIntegerField(default=0, verbose_name='浏览量')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_product'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/img/default_product.png'

    def get_discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

    def in_stock(self):
        return self.stock > 0

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f'PRD-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)


class Course(models.Model):
    """Online courses / digital learning products."""
    LEVEL_CHOICES = [
        ('beginner', '入门'),
        ('intermediate', '中级'),
        ('advanced', '高级'),
        ('all', '全部级别'),
    ]

    vendor = models.ForeignKey('manager.Vendor', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='courses', verbose_name='卖家')
    title = models.CharField(max_length=200, verbose_name='课程标题')
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(verbose_name='课程描述')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='价格')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='原价')
    image = models.ImageField(upload_to='marketplace/courses/', blank=True, null=True, verbose_name='封面')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    instructor = models.CharField(max_length=100, verbose_name='讲师')
    duration_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0, verbose_name='时长(小时)')
    lessons_count = models.PositiveIntegerField(default=0, verbose_name='课时数')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='all', verbose_name='难度级别')
    language = models.CharField(max_length=50, default='中文', verbose_name='教学语言')
    preview_url = models.URLField(blank=True, verbose_name='预览链接')
    is_featured = models.BooleanField(default=False, verbose_name='推荐课程')
    is_active = models.BooleanField(default=True, verbose_name='是否发布')
    enrollment_count = models.PositiveIntegerField(default=0, verbose_name='注册人数')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name='评分')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_course'
        verbose_name = '课程'
        verbose_name_plural = '课程'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/img/default_course.png'

    def get_discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0


class SupermarketItem(models.Model):
    """Supermarket / grocery items."""
    UNIT_CHOICES = [
        ('piece', '个'),
        ('kg', '公斤'),
        ('g', '克'),
        ('liter', '升'),
        ('ml', '毫升'),
        ('pack', '包'),
        ('box', '盒'),
        ('bottle', '瓶'),
        ('bag', '袋'),
    ]

    name = models.CharField(max_length=200, verbose_name='商品名称')
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True, verbose_name='商品描述')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='价格')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='原价')
    image = models.ImageField(upload_to='marketplace/supermarket/', blank=True, null=True, verbose_name='商品图片')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='supermarket_items')
    stock = models.PositiveIntegerField(default=0, verbose_name='库存')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece', verbose_name='单位')
    brand = models.CharField(max_length=100, blank=True, verbose_name='品牌')
    origin = models.CharField(max_length=100, blank=True, verbose_name='产地')
    is_organic = models.BooleanField(default=False, verbose_name='有机食品')
    is_featured = models.BooleanField(default=False, verbose_name='推荐商品')
    is_active = models.BooleanField(default=True, verbose_name='是否上架')
    sales_count = models.PositiveIntegerField(default=0, verbose_name='销量')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_supermarket_item'
        verbose_name = '超市商品'
        verbose_name_plural = '超市商品'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/img/default_product.png'

    def get_discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

    def in_stock(self):
        return self.stock > 0


class ProductAttribute(models.Model):
    """Dynamic attributes for products (e.g. size, color, material)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attributes')
    name = models.CharField(max_length=100, verbose_name='属性名称')
    value = models.CharField(max_length=255, verbose_name='属性值')

    class Meta:
        db_table = 'marketplace_product_attribute'
        verbose_name = '商品属性'
        verbose_name_plural = '商品属性'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}: {self.value}'


class SupermarketItemAttribute(models.Model):
    """Dynamic attributes for supermarket items (e.g. weight, shelf life)."""
    item = models.ForeignKey(SupermarketItem, on_delete=models.CASCADE, related_name='attributes')
    name = models.CharField(max_length=100, verbose_name='属性名称')
    value = models.CharField(max_length=255, verbose_name='属性值')

    class Meta:
        db_table = 'marketplace_supermarket_item_attribute'
        verbose_name = '超市商品属性'
        verbose_name_plural = '超市商品属性'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}: {self.value}'


class MarketplaceOrder(models.Model):
    """Orders placed in the marketplace — mirrors book Order flow."""
    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('payment_pending', '等待付款'),
        ('paid', '已付款'),
        ('processing', '处理中'),
        ('shipped', '已发货'),
        ('delivered', '已送达'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('wechat_pay', '微信支付'),
        ('alipay', '支付宝'),
        ('mtn_money', 'MTN Money'),
        ('orange_money', 'Orange Money'),
        ('airtel_money', 'Airtel Money'),
        ('paypal', 'PayPal'),
        ('credit_card', '信用卡'),
        ('bank_transfer', '银行转账'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', '待支付'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('refunded', '已退款'),
        ('cancelled', '已取消'),
    ]

    order_number = models.CharField(max_length=32, unique=True, verbose_name='订单号')
    user_id = models.IntegerField(null=True, blank=True, verbose_name='用户ID')
    user_email = models.EmailField(verbose_name='用户邮箱')
    user_name = models.CharField(max_length=100, blank=True, verbose_name='用户名')
    customer_phone = models.CharField(max_length=20, blank=True, default='', verbose_name='微信/电话号码')
    country = models.CharField(max_length=50, default='China', verbose_name='国家')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='wechat_pay', verbose_name='支付方式')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='订单状态')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='总金额')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='支付状态')
    payment_transaction_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='支付交易号')
    payment_completed_at = models.DateTimeField(blank=True, null=True, verbose_name='支付完成时间')
    shipping_address = models.TextField(blank=True, verbose_name='收货地址')
    notes = models.TextField(blank=True, verbose_name='备注')
    customer_notes = models.TextField(blank=True, verbose_name='客户备注')
    admin_notes = models.TextField(blank=True, verbose_name='管理员备注')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_order'
        verbose_name = '市场订单'
        verbose_name_plural = '市场订单'
        ordering = ['-created_at']

    def __str__(self):
        return f'MKT-{self.order_number}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f'MKT{timezone.now().strftime("%Y%m%d")}{uuid.uuid4().hex[:6].upper()}'
        super().save(*args, **kwargs)

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def mark_as_paid(self, transaction_id=''):
        self.status = 'paid'
        self.payment_status = 'completed'
        self.payment_transaction_id = transaction_id
        self.payment_completed_at = timezone.now()
        self.save()

    def is_payment_window_expired(self):
        if self.payment_status == 'completed':
            return False
        from datetime import timedelta
        window = timedelta(minutes=30)
        return timezone.now() > (self.created_at + window)

    def get_payment_time_remaining(self):
        if self.payment_status == 'completed':
            return None
        from datetime import timedelta
        window = timedelta(minutes=30)
        expiry_time = self.created_at + window
        remaining = expiry_time - timezone.now()
        if remaining.total_seconds() <= 0:
            return None
        return remaining

    def auto_cancel_if_expired(self):
        if self.status in ['pending', 'payment_pending'] and self.is_payment_window_expired():
            self.status = 'cancelled'
            self.payment_status = 'cancelled'
            self.save()
            return True
        return False

    def get_status_color(self):
        colors = {
            'pending': '#f59e0b',
            'payment_pending': '#f59e0b',
            'paid': '#10b981',
            'processing': '#06b6d4',
            'shipped': '#3b82f6',
            'delivered': '#10b981',
            'cancelled': '#ef4444',
            'refunded': '#8b5cf6',
        }
        return colors.get(self.status, '#6b7280')

    def get_payment_status_color(self):
        colors = {
            'pending': '#f59e0b',
            'processing': '#06b6d4',
            'completed': '#10b981',
            'failed': '#ef4444',
            'refunded': '#8b5cf6',
            'cancelled': '#ef4444',
        }
        return colors.get(self.payment_status, '#6b7280')


class MarketplaceOrderItem(models.Model):
    """Line items in a marketplace order."""
    ITEM_TYPE_CHOICES = [
        ('product', '商品'),
        ('course', '课程'),
        ('supermarket', '超市商品'),
    ]

    order = models.ForeignKey(MarketplaceOrder, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='商品类型')
    item_id = models.PositiveIntegerField(verbose_name='商品ID')
    item_name = models.CharField(max_length=200, verbose_name='商品名称')
    item_image = models.CharField(max_length=500, blank=True, verbose_name='商品图片URL')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='单价')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='小计')
    selected_attributes = models.JSONField(default=dict, blank=True, verbose_name='已选属性')

    class Meta:
        db_table = 'marketplace_order_item'
        verbose_name = '订单商品'
        verbose_name_plural = '订单商品'

    def __str__(self):
        return f'{self.item_name} x{self.quantity}'

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class MarketplaceCartItem(models.Model):
    """Session-based shopping cart for marketplace."""
    ITEM_TYPE_CHOICES = [
        ('product', '商品'),
        ('course', '课程'),
        ('supermarket', '超市商品'),
    ]

    session_key = models.CharField(max_length=40, verbose_name='会话密钥')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='商品类型')
    item_id = models.PositiveIntegerField(verbose_name='商品ID')
    quantity = models.PositiveIntegerField(default=1, verbose_name='数量')
    selected_attributes = models.JSONField(default=dict, blank=True, verbose_name='已选属性')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_cart_item'
        verbose_name = '购物车项目'
        verbose_name_plural = '购物车项目'

    def get_item(self):
        """Return the actual product/course/supermarket item."""
        if self.item_type == 'product':
            return Product.objects.filter(pk=self.item_id).first()
        elif self.item_type == 'course':
            return Course.objects.filter(pk=self.item_id).first()
        elif self.item_type == 'supermarket':
            return SupermarketItem.objects.filter(pk=self.item_id).first()
        return None

    def get_item_name(self):
        item = self.get_item()
        if not item:
            return '商品已下架'
        return item.title if self.item_type == 'course' else item.name

    def get_item_price(self):
        item = self.get_item()
        return item.price if item else Decimal('0')

    def get_item_image_url(self):
        item = self.get_item()
        return item.get_image_url() if item else '/static/img/default_product.png'

    def get_total_price(self):
        return self.get_item_price() * self.quantity

    def get_selected_attributes_display(self):
        return [
            {'name': key, 'value': value}
            for key, value in (self.selected_attributes or {}).items()
        ]

    def __str__(self):
        return f'{self.get_item_name()} x{self.quantity}'


class FlashSale(models.Model):
    """Time-limited flash sale for marketplace products."""
    ITEM_TYPE_CHOICES = [
        ('product', '商品'),
        ('course', '课程'),
        ('supermarket', '超市商品'),
    ]

    title = models.CharField(max_length=200, verbose_name='活动标题')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='product', verbose_name='商品类型')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='flash_sales', verbose_name='商品')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='flash_sales', verbose_name='课程')
    supermarket_item = models.ForeignKey(SupermarketItem, on_delete=models.CASCADE, null=True, blank=True,
                                          related_name='flash_sales', verbose_name='超市商品')
    flash_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='秒杀价')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    stock_limit = models.PositiveIntegerField(default=100, verbose_name='限量数量')
    sold_count = models.PositiveIntegerField(default=0, verbose_name='已售数量')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_flash_sale'
        verbose_name = '秒杀活动'
        verbose_name_plural = '秒杀活动'
        ordering = ['end_time']

    def __str__(self):
        return self.title

    def is_ongoing(self):
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    def get_item(self):
        if self.item_type == 'product' and self.product:
            return self.product
        elif self.item_type == 'course' and self.course:
            return self.course
        elif self.item_type == 'supermarket' and self.supermarket_item:
            return self.supermarket_item
        return None

    def get_item_name(self):
        item = self.get_item()
        if not item:
            return self.title
        return item.title if self.item_type == 'course' else item.name

    def get_item_image_url(self):
        item = self.get_item()
        return item.get_image_url() if item else '/static/img/default_product.png'

    def get_original_price(self):
        item = self.get_item()
        if not item:
            return self.flash_price
        return item.original_price or item.price

    def get_discount_percent(self):
        orig = self.get_original_price()
        if orig and orig > self.flash_price:
            return int(((orig - self.flash_price) / orig) * 100)
        return 0

    def get_item_url(self):
        item = self.get_item()
        if not item:
            return '#'
        if self.item_type == 'product':
            return f'/marketplace/products/{item.slug}/'
        elif self.item_type == 'course':
            return f'/marketplace/courses/{item.slug}/'
        elif self.item_type == 'supermarket':
            return f'/marketplace/supermarket/{item.slug}/'
        return '#'

    def remaining_stock(self):
        return max(0, self.stock_limit - self.sold_count)


class CourseSection(models.Model):
    """A section/chapter within a course."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200, verbose_name='章节标题')
    title_en = models.CharField(max_length=200, blank=True, verbose_name='English Title')
    order = models.PositiveIntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_course_section'
        ordering = ['order']
        verbose_name = '课程章节'
        verbose_name_plural = '课程章节'

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class CourseLesson(models.Model):
    """A single lesson/video within a course section."""
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200, verbose_name='课时标题')
    title_en = models.CharField(max_length=200, blank=True, verbose_name='English Title')
    description = models.TextField(blank=True, verbose_name='课时描述')
    video_url = models.URLField(blank=True, verbose_name='视频链接(外部)')
    video_file = models.FileField(upload_to='marketplace/course_videos/', blank=True, null=True, verbose_name='视频文件')
    duration_minutes = models.PositiveIntegerField(default=0, verbose_name='时长(分钟)')
    order = models.PositiveIntegerField(default=0, verbose_name='排序')
    is_free = models.BooleanField(default=False, verbose_name='免费试看')
    pdf_file = models.FileField(upload_to='marketplace/course_pdfs/', blank=True, null=True, verbose_name='PDF文件')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_course_lesson'
        ordering = ['order']
        verbose_name = '课时'
        verbose_name_plural = '课时'

    def __str__(self):
        return self.title

    def get_video_source(self):
        """Return video URL or file URL, preferring uploaded file."""
        if self.video_file:
            return {'type': 'file', 'url': self.video_file.url}
        elif self.video_url:
            return {'type': 'url', 'url': self.video_url}
        return None


class CourseProgress(models.Model):
    """Track user progress through course lessons."""
    session_key = models.CharField(max_length=40, verbose_name='会话密钥')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress_records')
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='progress_records')
    completed = models.BooleanField(default=False, verbose_name='已完成')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_course_progress'
        unique_together = ('session_key', 'lesson')
        verbose_name = '学习进度'
        verbose_name_plural = '学习进度'

    def __str__(self):
        return f'{self.lesson.title} - {"✓" if self.completed else "○"}'
