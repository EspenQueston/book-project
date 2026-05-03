from django.db import models
from django.utils import timezone
from decimal import Decimal
import os
import uuid


# 创建数据库对象模型
# 管理员登录类
class Manager(models.Model):
    id = models.AutoField(primary_key=True)
    number = models.CharField(max_length=32, verbose_name="账号")
    # max_length=128 to hold Django PBKDF2 hashes
    password = models.CharField(max_length=128, verbose_name="密码")
    name = models.CharField(max_length=32, verbose_name="名字")
    # Flag used by AdminDebugMiddleware – only real admins see stack traces
    is_admin = models.BooleanField(default=True, verbose_name="管理员权限")

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    # 指定数据表名称（未指定即为默认类名）
    class Meta:
        db_table = "manager"


# 出版社类
class Publisher(models.Model):
    # 出版社名称
    publisher_name = models.CharField(max_length=128, verbose_name="出版社名称")
    # 出版社地址
    publisher_address = models.CharField(max_length=128, verbose_name="出版社地址")

    # 指定数据表名称（未指定即为默认类名）
    class Meta:
        db_table = "publisher"


class BookCategory(models.Model):
    """Book category shared by mobile and desktop book filters."""
    name = models.CharField(max_length=100, verbose_name='分类名称')
    name_en = models.CharField(max_length=100, blank=True, default='', verbose_name='英文名称')
    name_fr = models.CharField(max_length=100, blank=True, default='', verbose_name='法文名称')
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, verbose_name='描述')
    icon = models.CharField(max_length=50, default='fas fa-book', verbose_name='图标CSS类')
    color = models.CharField(max_length=7, default='#667eea', verbose_name='颜色(hex)')
    display_order = models.IntegerField(default=0, verbose_name='排序权重')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='父分类')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'book_category'
        ordering = ['display_order', 'name']
        verbose_name = '图书分类'
        verbose_name_plural = '图书分类'

    def __str__(self):
        return self.name

    def get_display_name(self):
        return self.name


# 图书类
class Book(models.Model):
    # 图书id
    id = models.AutoField(primary_key=True)
    # 图书名称
    name = models.CharField(max_length=255)
    # 图书描述
    description = models.TextField(verbose_name='图书描述', blank=True, null=True, help_text='图书详细描述信息')
    # 图书封面
    cover_image = models.ImageField(
        upload_to='book_covers/', 
        verbose_name='图书封面', 
        blank=True, 
        null=True,
        help_text='上传图书封面图片'
    )
    # 图书文件/下载链接
    book_file = models.FileField(
        upload_to='book_files/',
        verbose_name='图书文件',
        blank=True,
        null=True,
        help_text='上传图书PDF、EPUB等文件，或者留空使用下载链接'
    )
    download_link = models.URLField(
        max_length=500,
        verbose_name='下载链接',
        blank=True,
        null=True,
        help_text='外部下载链接（Google Drive、OneDrive等）'
    )
    # 图书价格 最多5位，小数保留2位
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # 库存
    inventory = models.IntegerField(verbose_name='库存数')
    # 销量
    sale_num = models.IntegerField(verbose_name='卖出数')
    # 出版社（一对一 外键）
    publisher = models.ForeignKey(to='Publisher', on_delete=models.CASCADE)
    category = models.ForeignKey(BookCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='books', verbose_name='分类')
    is_active = models.BooleanField(default=True, verbose_name='是否上架')

    class Meta:
        db_table = "book"
    
    def get_cover_url(self):
        """获取封面图片URL，如果没有封面则返回默认图片"""
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        return '/static/images/default_book_cover.jpg'
    
    def get_short_description(self, max_length=100):
        """获取简短描述"""
        if self.description:
            if len(self.description) > max_length:
                return self.description[:max_length] + '...'
            return self.description
        return '暂无描述'
    
    def get_medium_description(self):
        """获取中等长度描述(150字符)"""
        return self.get_short_description(150)
    
    def get_brief_description(self):
        """获取简要描述(100字符)"""
        return self.get_short_description(100)
    
    def get_long_description(self):
        """获取较长描述(300字符)"""
        return self.get_short_description(300)
    
    def has_download(self):
        """检查是否有下载文件或链接"""
        return bool(self.book_file) or bool(self.download_link)
    
    def get_download_url(self):
        """获取下载URL，优先返回文件URL，其次是下载链接"""
        if self.book_file and hasattr(self.book_file, 'url'):
            return self.book_file.url
        elif self.download_link:
            return self.download_link
        return None
    
    def get_download_type(self):
        """获取下载类型：file（文件）或 link（链接）"""
        if self.book_file:
            return 'file'
        elif self.download_link:
            return 'link'
        return None


# 作者类
class Author(models.Model):
    # 作者id
    id = models.AutoField(primary_key=True)
    # 作者名字
    name = models.CharField(max_length=32)
    # 所创图书（多对多）
    book = models.ManyToManyField(to='Book')

    # 指定数据表名称（未指定即为默认类名）
    class Meta:
        db_table = "author"


# E-commerce Models for Shopping Cart and Orders

PAYMENT_METHOD_CHOICES = [
    ('mtn_money', 'MTN Money'),
    ('orange_money', 'Orange Money'),
    ('airtel_money', 'Airtel Money'),
    ('wechat_pay', '微信支付'),
    ('alipay', '支付宝'),
    ('paypal', 'PayPal'),
    ('credit_card', 'Visa / Mastercard'),
    ('bank_transfer', '银行转账'),
]

ORDER_STATUS_CHOICES = [
    ('pending', '待处理'),
    ('payment_pending', '待付款'),
    ('paid', '已付款'),
    ('confirmed', '已确认'),
    ('processing', '处理中'),
    ('shipped', '已发货'),
    ('delivered', '已送达'),
    ('cancelled', '已取消'),
    ('refunded', '已退款'),
]

PAYMENT_STATUS_CHOICES = [
    ('pending', '待支付'),
    ('processing', '支付处理中'),
    ('completed', '支付完成'),
    ('failed', '支付失败'),
    ('refunded', '已退款'),
    ('cancelled', '已取消'),
]


# 客户订单模型
class Order(models.Model):
    """Order model for customer purchases - Digital Products Only"""
    order_number = models.CharField(max_length=32, unique=True, verbose_name="订单号")
    customer_name = models.CharField(max_length=100, verbose_name="客户姓名")
    customer_email = models.EmailField(db_index=True, verbose_name="客户邮箱")
    customer_phone = models.CharField(max_length=20, verbose_name="微信/电话号码")
    
    # 国家信息 (仅用于数字产品)
    country = models.CharField(max_length=50, default='China', verbose_name="国家")
    shipping_address = models.TextField(blank=True, default='', verbose_name="收货地址")
      # 订单详情
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES, 
        verbose_name="支付方式"
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="总金额")
    status = models.CharField(
        max_length=20, 
        choices=ORDER_STATUS_CHOICES, 
        default='pending', 
        verbose_name="订单状态"
    )
    
    # 支付信息
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name="支付状态"
    )
    payment_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="支付交易号"
    )
    payment_completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="支付完成时间"
    )
    
    customer_notes = models.TextField(blank=True, verbose_name="客户备注")
    admin_notes = models.TextField(blank=True, verbose_name="管理员备注")
      # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = "order"
        ordering = ['-created_at']
        verbose_name = "订单"
        verbose_name_plural = "订单"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import datetime
        now = datetime.datetime.now()
        return f"ORD{now.strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"
    
    def get_total_items(self):
        """Get total number of items in this order"""
        return sum(item.quantity for item in self.orderitem_set.all())
    
    def mark_as_paid(self, transaction_id=None):
        """Mark order as paid and update payment status"""
        self.payment_status = 'completed'
        self.status = 'paid'
        self.payment_completed_at = timezone.now()
        if transaction_id:
            self.payment_transaction_id = transaction_id
        self.save()
    
    def get_status_color(self):
        """Get bootstrap color class for order status"""
        status_colors = {
            'pending': 'warning',
            'payment_pending': 'info',
            'paid': 'success',
            'confirmed': 'primary',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
            'refunded': 'secondary',
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_payment_status_color(self):
        """Get bootstrap color class for payment status"""
        payment_colors = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'secondary',
            'cancelled': 'dark',
        }
        return payment_colors.get(self.payment_status, 'secondary')
    
    UNPAID_CANCEL_HOURS = 24
    PAID_AUTO_COMPLETE_DAYS = 14

    def is_payment_window_expired(self):
        """True when unpaid order passed the payment deadline (24 hours)."""
        from datetime import timedelta
        if self.payment_status == 'completed':
            return False
        if self.status in ('cancelled', 'refunded', 'delivered'):
            return False
        expiration_time = self.created_at + timedelta(hours=self.UNPAID_CANCEL_HOURS)
        return timezone.now() > expiration_time

    def get_payment_time_remaining(self):
        """Seconds remaining to pay for unpaid orders (24-hour window)."""
        from datetime import timedelta
        if self.payment_status == 'completed':
            return 0
        if self.status in ('cancelled', 'refunded', 'delivered'):
            return 0
        expiration_time = self.created_at + timedelta(hours=self.UNPAID_CANCEL_HOURS)
        remaining = expiration_time - timezone.now()
        return max(0, int(remaining.total_seconds()))

    def apply_ttl_rules(self):
        """Platform TTL: unpaid → cancelled after 24h; paid → auto-delivered after 14 days if not terminal."""
        from datetime import timedelta
        now = timezone.now()
        terminal = {'cancelled', 'refunded', 'delivered'}
        changed_fields = []

        if self.payment_status != 'completed':
            if self.status not in terminal:
                if now > self.created_at + timedelta(hours=self.UNPAID_CANCEL_HOURS):
                    self.status = 'cancelled'
                    self.payment_status = 'cancelled'
                    changed_fields.extend(['status', 'payment_status'])
        else:
            ref = self.payment_completed_at or self.created_at
            if self.status not in terminal and ref:
                if now > ref + timedelta(days=self.PAID_AUTO_COMPLETE_DAYS):
                    self.status = 'delivered'
                    changed_fields.append('status')

        if changed_fields:
            self.save(update_fields=list(dict.fromkeys(changed_fields)) + ['updated_at'])
            return True
        return False

    def auto_cancel_if_expired(self):
        """Backward-compatible hook — applies full TTL rules."""
        return self.apply_ttl_rules()
    
    def __str__(self):
        return f"订单 {self.order_number} - {self.customer_name}"

# 订单项模型（一个订单包含多本图书）
class OrderItem(models.Model):
    """Individual items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="订单")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="图书")
    quantity = models.PositiveIntegerField(verbose_name="数量")
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="单价")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="小计")
    
    class Meta:
        db_table = "order_item"
        verbose_name = "订单项目"
        verbose_name_plural = "订单项目"
    
    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.order.order_number} - {self.book.name} x {self.quantity}"


# 购物车模型（用于多本图书选择）
class CartItem(models.Model):
    """Shopping cart item model"""
    session_key = models.CharField(max_length=40, db_index=True, verbose_name="会话密钥")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="图书")
    quantity = models.PositiveIntegerField(default=1, verbose_name="数量")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = "cart_item"
        unique_together = ('session_key', 'book')
        verbose_name = "购物车项目"
        verbose_name_plural = "购物车项目"
    
    def get_total_price(self):
        """Calculate total price for this cart item"""
        return self.book.price * self.quantity
    
    def __str__(self):
        return f"{self.book.name} x {self.quantity}"

# 订单通知模型（用于跟踪支付状态变化）
class OrderNotification(models.Model):
    """Order notification model for tracking payment status changes"""
    NOTIFICATION_TYPES = [
        ('payment_status_change', '支付状态变更'),
        ('order_status_change', '订单状态变更'),
        ('order_created', '订单创建'),
        ('order_cancelled', '订单取消'),
        ('refund_processed', '退款处理'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="订单", related_name="notifications")
    notification_type = models.CharField(
        max_length=50, 
        choices=NOTIFICATION_TYPES, 
        verbose_name="通知类型"
    )
    message = models.TextField(verbose_name="通知消息")
    details = models.JSONField(blank=True, null=True, verbose_name="详细信息")
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        db_table = "order_notification"
        ordering = ['-created_at']
        verbose_name = "订单通知"
        verbose_name_plural = "订单通知"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save()
    
    def __str__(self):
        return f"{self.order.order_number} - {self.get_notification_type_display()}"


class BlogCategory(models.Model):
    """Blog category model"""
    name = models.CharField(max_length=100, verbose_name="分类名称")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL标识")
    description = models.TextField(blank=True, verbose_name="分类描述")
    icon = models.CharField(max_length=50, default='fas fa-folder', verbose_name="图标CSS类")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "blog_category"
        ordering = ['name']
        verbose_name = "博客分类"
        verbose_name_plural = "博客分类"

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    """Blog post model"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]

    title = models.CharField(max_length=200, verbose_name="标题")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL标识")
    category = models.ForeignKey(
        BlogCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='posts',
        verbose_name="分类"
    )
    cover_image = models.ImageField(
        upload_to='blog_covers/', verbose_name="封面图片",
        blank=True, null=True
    )
    excerpt = models.TextField(max_length=500, blank=True, verbose_name="摘要")
    content = models.TextField(verbose_name="内容")
    author_name = models.CharField(max_length=100, default='Admin', verbose_name="作者")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='draft', verbose_name="状态"
    )
    is_featured = models.BooleanField(default=False, verbose_name="精选文章")
    views_count = models.PositiveIntegerField(default=0, verbose_name="浏览次数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="发布时间")

    class Meta:
        db_table = "blog_post"
        ordering = ['-published_at', '-created_at']
        verbose_name = "博客文章"
        verbose_name_plural = "博客文章"

    def __str__(self):
        return self.title

    def get_cover_url(self):
        if self.cover_image:
            return self.cover_image.url
        return None

    def get_excerpt(self, length=150):
        if self.excerpt:
            return self.excerpt[:length] + '...' if len(self.excerpt) > length else self.excerpt
        return self.content[:length] + '...' if len(self.content) > length else self.content

    def get_reading_time(self):
        word_count = len(self.content)
        return max(1, word_count // 500)


class ContactMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name='姓名')
    email = models.EmailField(verbose_name='邮箱')
    subject = models.CharField(max_length=200, blank=True, default='', verbose_name='主题')
    message = models.TextField(verbose_name='留言内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    is_read = models.BooleanField(default=False, verbose_name='已读')
    email_sent = models.BooleanField(default=False, verbose_name='邮件已发送')
    labels = models.ManyToManyField('EmailLabel', blank=True, related_name='contact_messages', verbose_name='标签')
    replied = models.BooleanField(default=False, verbose_name='已回复')
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name='回复时间')
    admin_reply = models.TextField(blank=True, default='', verbose_name='管理员回复')
    session_key = models.CharField(max_length=64, blank=True, default='', verbose_name='会话标识')

    class Meta:
        db_table = 'contact_message'
        ordering = ['-created_at']
        verbose_name = '联系留言'
        verbose_name_plural = '联系留言'

    def __str__(self):
        return f'{self.name} - {self.subject or "No Subject"} ({self.created_at.strftime("%Y-%m-%d")})'


# ==========================================
# Email Management System Models
# ==========================================

class EmailAccount(models.Model):
    """Email account configuration for sending/receiving"""
    name = models.CharField(max_length=100, verbose_name='账户名称')
    email_address = models.EmailField(unique=True, verbose_name='邮箱地址')

    # IMAP settings
    imap_host = models.CharField(max_length=200, default='imap.gmail.com', verbose_name='IMAP服务器')
    imap_port = models.IntegerField(default=993, verbose_name='IMAP端口')
    imap_use_ssl = models.BooleanField(default=True, verbose_name='IMAP SSL')

    # SMTP settings
    smtp_host = models.CharField(max_length=200, default='smtp.gmail.com', verbose_name='SMTP服务器')
    smtp_port = models.IntegerField(default=587, verbose_name='SMTP端口')
    smtp_use_tls = models.BooleanField(default=True, verbose_name='SMTP TLS')

    # Auth
    username = models.CharField(max_length=200, verbose_name='用户名')
    password = models.CharField(max_length=500, verbose_name='密码/应用密码')

    is_active = models.BooleanField(default=True, verbose_name='启用')
    is_default = models.BooleanField(default=False, verbose_name='默认账户')

    last_sync = models.DateTimeField(null=True, blank=True, verbose_name='最后同步')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'email_account'
        verbose_name = '邮箱账户'
        verbose_name_plural = '邮箱账户'

    def __str__(self):
        return f'{self.name} <{self.email_address}>'


class EmailLabel(models.Model):
    """Email labels for classification"""
    name = models.CharField(max_length=100, verbose_name='标签名称')
    color = models.CharField(max_length=7, default='#667eea', verbose_name='颜色')
    icon = models.CharField(max_length=50, default='fa-tag', verbose_name='图标')

    class Meta:
        db_table = 'email_label'
        verbose_name = '邮件标签'
        verbose_name_plural = '邮件标签'

    def __str__(self):
        return self.name


class EmailMessage(models.Model):
    """Email message storage"""
    FOLDER_CHOICES = [
        ('inbox', '收件箱'),
        ('sent', '已发送'),
        ('draft', '草稿'),
        ('trash', '已删除'),
        ('archive', '归档'),
    ]

    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='emails', verbose_name='邮箱账户')
    message_uid = models.CharField(max_length=500, blank=True, default='', verbose_name='邮件UID')

    sender_name = models.CharField(max_length=300, blank=True, default='', verbose_name='发件人名称')
    sender_email = models.EmailField(blank=True, default='', verbose_name='发件人邮箱')
    recipients = models.TextField(default='', verbose_name='收件人')
    cc = models.TextField(default='', blank=True, verbose_name='抄送')
    bcc = models.TextField(default='', blank=True, verbose_name='密送')

    subject = models.CharField(max_length=1000, default='(无主题)', verbose_name='主题')
    body_text = models.TextField(default='', blank=True, verbose_name='纯文本内容')
    body_html = models.TextField(default='', blank=True, verbose_name='HTML内容')

    folder = models.CharField(max_length=20, choices=FOLDER_CHOICES, default='inbox', verbose_name='文件夹')
    is_read = models.BooleanField(default=False, verbose_name='已读')
    is_starred = models.BooleanField(default=False, verbose_name='星标')

    labels = models.ManyToManyField(EmailLabel, blank=True, related_name='emails', verbose_name='标签')

    received_at = models.DateTimeField(null=True, blank=True, verbose_name='接收时间')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    in_reply_to = models.CharField(max_length=500, blank=True, default='', verbose_name='回复ID')

    class Meta:
        db_table = 'email_message'
        ordering = ['-received_at', '-created_at']
        verbose_name = '邮件'
        verbose_name_plural = '邮件'

    def __str__(self):
        return f'{self.subject} - {self.sender_email}'


class EmailAttachment(models.Model):
    """Email attachment storage"""
    email = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name='attachments', verbose_name='邮件')
    filename = models.CharField(max_length=500, verbose_name='文件名')
    content_type = models.CharField(max_length=200, blank=True, default='', verbose_name='文件类型')
    file = models.FileField(upload_to='email_attachments/%Y/%m/', verbose_name='文件')
    size = models.IntegerField(default=0, verbose_name='文件大小')

    class Meta:
        db_table = 'email_attachment'
        verbose_name = '邮件附件'
        verbose_name_plural = '邮件附件'

    def __str__(self):
        return self.filename


class EmailAutoRule(models.Model):
    """Automatic email processing rules"""
    ACTION_CHOICES = [
        ('label', '添加标签'),
        ('star', '添加星标'),
        ('archive', '归档'),
        ('delete', '删除'),
        ('auto_reply', '自动回复'),
        ('forward', '转发'),
        ('mark_read', '标记已读'),
    ]

    MATCH_FIELD_CHOICES = [
        ('from', '发件人'),
        ('to', '收件人'),
        ('subject', '主题'),
        ('body', '正文'),
        ('any', '任意字段'),
    ]

    name = models.CharField(max_length=200, verbose_name='规则名称')
    is_active = models.BooleanField(default=True, verbose_name='启用')

    match_field = models.CharField(max_length=20, choices=MATCH_FIELD_CHOICES, default='any', verbose_name='匹配字段')
    match_pattern = models.CharField(max_length=500, verbose_name='匹配关键词')

    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='label', verbose_name='执行操作')
    action_label = models.ForeignKey(EmailLabel, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='目标标签')
    action_forward_to = models.EmailField(blank=True, default='', verbose_name='转发地址')
    auto_reply_subject = models.CharField(max_length=500, blank=True, default='', verbose_name='自动回复主题')
    auto_reply_body = models.TextField(blank=True, default='', verbose_name='自动回复内容')

    apply_to_account = models.ForeignKey(EmailAccount, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='应用到账户')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'email_auto_rule'
        ordering = ['-priority', 'name']
        verbose_name = '邮件规则'
        verbose_name_plural = '邮件规则'

    def __str__(self):
        return f'{self.name} ({self.get_action_display()})'


# ==========================================
# Site User Authentication System
# ==========================================

class SiteUser(models.Model):
    """Public site user model for optional user accounts"""
    email = models.EmailField(unique=True, verbose_name='邮箱')
    password = models.CharField(max_length=128, verbose_name='密码')
    name = models.CharField(max_length=100, verbose_name='姓名')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='电话')
    avatar = models.ImageField(upload_to='user_avatars/', blank=True, null=True, verbose_name='头像')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'site_user'
        ordering = ['-created_at']
        verbose_name = '站点用户'
        verbose_name_plural = '站点用户'

    def __str__(self):
        return f'{self.name} <{self.email}>'

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return None


VERIFICATION_TYPE_CHOICES = [
    ('user', '用户注册'),
    ('vendor', '卖家注册'),
    ('password_reset', '密码重置'),
]


class EmailVerification(models.Model):
    """PIN code verification for new user/vendor registration"""
    email = models.EmailField(verbose_name='邮箱')
    pin_code = models.CharField(max_length=6, verbose_name='验证码')
    name = models.CharField(max_length=100, verbose_name='姓名')
    password = models.CharField(max_length=128, verbose_name='密码(已加密)')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='电话')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPE_CHOICES, default='user', verbose_name='验证类型')
    company_name = models.CharField(max_length=200, blank=True, default='', verbose_name='公司名称')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    is_verified = models.BooleanField(default=False, verbose_name='已验证')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    expires_at = models.DateTimeField(verbose_name='过期时间')

    class Meta:
        db_table = 'email_verification'
        ordering = ['-created_at']
        verbose_name = '邮箱验证'
        verbose_name_plural = '邮箱验证'

    def __str__(self):
        return f'{self.email} - {self.pin_code}'

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class Wishlist(models.Model):
    """User wishlist / favorites - supports books and marketplace items"""
    ITEM_TYPE_CHOICES = [
        ('book', '图书'),
        ('product', '商品'),
        ('course', '课程'),
        ('supermarket', '超市商品'),
    ]

    user = models.ForeignKey(SiteUser, on_delete=models.CASCADE, related_name='wishlists', verbose_name='用户')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True, verbose_name='图书')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='book', verbose_name='商品类型')
    item_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='商品ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')

    class Meta:
        db_table = 'wishlist'
        ordering = ['-created_at']
        verbose_name = '收藏'
        verbose_name_plural = '收藏'

    def __str__(self):
        if self.item_type == 'book' and self.book:
            return f'{self.user.name} - {self.book.name}'
        return f'{self.user.name} - {self.get_item_type_display()} #{self.item_id}'

    def get_item(self):
        """Get the actual item object (for marketplace items)"""
        if self.item_type == 'book':
            return self.book
        try:
            from marketplace.models import Product, Course, SupermarketItem
            if self.item_type == 'product':
                return Product.objects.filter(pk=self.item_id).first()
            elif self.item_type == 'course':
                return Course.objects.filter(pk=self.item_id).first()
            elif self.item_type == 'supermarket':
                return SupermarketItem.objects.filter(pk=self.item_id).first()
        except Exception:
            pass
        return None

    def get_item_name(self):
        item = self.get_item()
        if not item:
            return '商品已下架'
        if self.item_type == 'course':
            return item.title
        return getattr(item, 'name', str(item))

    def get_item_price(self):
        item = self.get_item()
        if item:
            return item.price
        return None

    def get_item_image_url(self):
        item = self.get_item()
        if item and hasattr(item, 'get_image_url'):
            return item.get_image_url()
        if item and hasattr(item, 'get_cover_url'):
            return item.get_cover_url()
        return '/static/img/default_product.png'


# ==========================================
# Vendor / Seller System
# ==========================================

VENDOR_STATUS_CHOICES = [
    ('pending', '待审核'),
    ('approved', '已批准'),
    ('rejected', '已拒绝'),
    ('suspended', '已暂停'),
]


class Vendor(models.Model):
    """Vendor / Seller model for marketplace"""
    user = models.OneToOneField(SiteUser, on_delete=models.CASCADE, null=True, blank=True, related_name='vendor_profile', verbose_name='关联用户')
    company_name = models.CharField(max_length=200, verbose_name='公司/店铺名称')
    contact_name = models.CharField(max_length=100, verbose_name='联系人')
    email = models.EmailField(verbose_name='邮箱')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='电话')
    password = models.CharField(max_length=128, verbose_name='密码')
    description = models.TextField(blank=True, default='', verbose_name='店铺描述')
    logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True, verbose_name='Logo')
    status = models.CharField(max_length=20, choices=VENDOR_STATUS_CHOICES, default='pending', verbose_name='状态')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name='佣金比例(%)')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'vendor'
        ordering = ['-created_at']
        verbose_name = '卖家'
        verbose_name_plural = '卖家'

    def __str__(self):
        return self.company_name

    def get_logo_url(self):
        if self.logo and hasattr(self.logo, 'url'):
            return self.logo.url
        return None

    def get_total_books(self):
        return self.vendorbook_set.count()

    def get_total_sales(self):
        return sum(vb.book.sale_num for vb in self.vendorbook_set.select_related('book').all())


class VendorBook(models.Model):
    """Books listed by a vendor"""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, verbose_name='卖家')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='图书')
    vendor_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='卖家定价')
    is_active = models.BooleanField(default=True, verbose_name='上架')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='上架时间')

    class Meta:
        db_table = 'vendor_book'
        unique_together = ('vendor', 'book')
        verbose_name = '卖家图书'
        verbose_name_plural = '卖家图书'

    def __str__(self):
        return f'{self.vendor.company_name} - {self.book.name}'


# ==========================================
# Admin Notification System
# ==========================================

NOTIFICATION_TYPE_CHOICES = [
    ('new_order', '新订单'),
    ('new_user', '新用户注册'),
    ('abandoned_cart', '待下单提醒'),
    ('incomplete_registration', '未完成注册'),
    ('order_paid', '订单已付款'),
    ('vendor_registered', '新卖家注册'),
    ('low_stock', '库存不足'),
    ('contact_message', '联系消息'),
    ('cs_chat', '客服聊天'),
]


class AdminNotification(models.Model):
    """Notification system for admin panel"""
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, verbose_name='类型')
    title = models.CharField(max_length=200, verbose_name='标题')
    message = models.TextField(verbose_name='内容')
    icon = models.CharField(max_length=50, default='fas fa-bell', verbose_name='图标')
    color = models.CharField(max_length=20, default='#667eea', verbose_name='颜色')
    link = models.CharField(max_length=500, blank=True, default='', verbose_name='链接')
    is_read = models.BooleanField(default=False, verbose_name='已读')
    is_dismissed = models.BooleanField(default=False, verbose_name='已清除')
    related_id = models.IntegerField(null=True, blank=True, verbose_name='关联ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'admin_notification'
        ordering = ['-created_at']
        verbose_name = '管理员通知'
        verbose_name_plural = '管理员通知'

    def __str__(self):
        return f'[{self.get_notification_type_display()}] {self.title}'


# ==========================================
# Vendor Notification System
# ==========================================

VENDOR_NOTIFICATION_TYPE_CHOICES = [
    ('new_order', '新订单'),
    ('new_message', '新消息'),
    ('order_paid', '订单已付款'),
    ('order_shipped', '订单已发货'),
    ('low_stock', '库存不足'),
    ('new_review', '新评价'),
    ('system', '系统通知'),
]


class VendorNotification(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='notifications', verbose_name='卖家')
    notification_type = models.CharField(max_length=30, choices=VENDOR_NOTIFICATION_TYPE_CHOICES, verbose_name='类型')
    title = models.CharField(max_length=200, verbose_name='标题')
    message = models.TextField(verbose_name='内容')
    icon = models.CharField(max_length=50, default='fas fa-bell', verbose_name='图标')
    color = models.CharField(max_length=20, default='#10b981', verbose_name='颜色')
    link = models.CharField(max_length=500, blank=True, default='', verbose_name='链接')
    is_read = models.BooleanField(default=False, verbose_name='已读')
    related_id = models.IntegerField(null=True, blank=True, verbose_name='关联ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'vendor_notification'
        ordering = ['-created_at']
        verbose_name = '卖家通知'
        verbose_name_plural = '卖家通知'

    def __str__(self):
        return f'[{self.vendor.company_name}] {self.title}'


# ==========================================
# AI Chatbot System
# ==========================================

AI_PROVIDER_CHOICES = [
    ('openai', 'OpenAI (ChatGPT)'),
    ('anthropic', 'Anthropic (Claude)'),
    ('google', 'Google (Gemini)'),
    ('qwen', 'Alibaba (Qwen/通义千问)'),
    ('deepseek', 'DeepSeek'),
    ('openrouter', 'OpenRouter'),
    ('custom', 'Custom / Local'),
]

CHAT_ROLE_CHOICES = [
    ('user', 'User'),
    ('assistant', 'Assistant'),
    ('system', 'System'),
]


class ChatbotConfig(models.Model):
    """Global chatbot configuration — one active config at a time."""
    name = models.CharField(max_length=100, default='Default Config', verbose_name='配置名称')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    provider = models.CharField(max_length=20, choices=AI_PROVIDER_CHOICES, default='openai', verbose_name='AI 提供商')
    api_key = models.CharField(max_length=500, blank=True, default='', verbose_name='API Key')
    model_name = models.CharField(max_length=100, blank=True, default='', verbose_name='模型名称',
                                  help_text='e.g. gpt-4o, claude-3-5-sonnet-20241022, gemini-1.5-pro, qwen-plus')
    api_endpoint = models.CharField(max_length=500, blank=True, default='', verbose_name='自定义 API 地址',
                                    help_text='Leave blank to use provider default')
    system_prompt = models.TextField(
        default='你是DUNO 360平台的友好、专业助手。你帮助用户了解图书、作者、出版社、在线课程、市场商品和生鲜超市信息，并回答关于购物、订单等问题。请用简洁、友好的语言回答。',
        verbose_name='系统提示词 (System Prompt)'
    )
    max_tokens = models.IntegerField(default=1000, verbose_name='最大 Token 数')
    temperature = models.FloatField(default=0.7, verbose_name='温度 (0.0 - 2.0)')
    # Widget appearance
    widget_title = models.CharField(max_length=100, default='AI 助手', verbose_name='聊天窗口标题')
    widget_subtitle = models.CharField(max_length=200, default='有什么可以帮助你的？', verbose_name='副标题')
    welcome_message = models.TextField(
        default='你好！我是 AI 助手，有什么可以帮助你的吗？',
        verbose_name='欢迎消息'
    )
    # Scope: show on public pages, admin pages, or both
    show_on_public = models.BooleanField(default=True, verbose_name='在前端显示')
    show_on_admin = models.BooleanField(default=True, verbose_name='在管理后台显示')
    # Rate limiting
    max_messages_per_session = models.IntegerField(default=50, verbose_name='每会话最大消息数')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chatbot_config'
        verbose_name = '聊天机器人配置'
        verbose_name_plural = '聊天机器人配置'

    def __str__(self):
        return f'{self.name} ({self.get_provider_display()})'

    def get_masked_api_key(self):
        """Return masked API key for display."""
        if not self.api_key:
            return ''
        k = self.api_key
        if len(k) <= 8:
            return '*' * len(k)
        return k[:4] + '*' * (len(k) - 8) + k[-4:]

    def get_default_model(self):
        defaults = {
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-5-haiku-20241022',
            'google': 'gemini-1.5-flash',
            'qwen': 'qwen-plus',
            'deepseek': 'deepseek-chat',
            'openrouter': 'nvidia/nemotron-3-super-120b-a12b:free',
            'custom': '',
        }
        return self.model_name or defaults.get(self.provider, '')


class ChatSession(models.Model):
    """A single chat session (anonymous or user-linked)."""
    session_key = models.CharField(max_length=64, db_index=True, verbose_name='Session Key')
    user = models.ForeignKey('SiteUser', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='chat_sessions', verbose_name='用户')
    config = models.ForeignKey(ChatbotConfig, null=True, on_delete=models.SET_NULL,
                               related_name='sessions', verbose_name='配置')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    last_active = models.DateTimeField(auto_now=True, verbose_name='最近活跃')
    message_count = models.IntegerField(default=0, verbose_name='消息数')
    is_closed = models.BooleanField(default=False)
    context = models.TextField(blank=True, default='', verbose_name='上下文摘要')

    class Meta:
        db_table = 'chat_session'
        ordering = ['-last_active']
        verbose_name = '聊天会话'
        verbose_name_plural = '聊天会话'

    def __str__(self):
        return f'Session {self.session_key[:12]} ({self.message_count} msgs)'


class ChatMessage(models.Model):
    """A single message in a chat session."""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE,
                                related_name='messages', verbose_name='会话')
    role = models.CharField(max_length=10, choices=CHAT_ROLE_CHOICES, verbose_name='角色')
    content = models.TextField(verbose_name='内容')
    tokens_used = models.IntegerField(default=0, verbose_name='Token 用量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'chat_message'
        ordering = ['created_at']
        verbose_name = '聊天消息'
        verbose_name_plural = '聊天消息'

    def __str__(self):
        return f'[{self.role}] {self.content[:60]}'


# ==========================================
# Loyalty / Gamification System
# ==========================================

class LoyaltyPoints(models.Model):
    """Loyalty points balance and tier for each SiteUser."""
    TIER_CHOICES = [
        ('bronze', '铜牌'),
        ('silver', '银牌'),
        ('gold', '金牌'),
        ('platinum', '白金'),
    ]

    user = models.OneToOneField(SiteUser, on_delete=models.CASCADE,
                                 related_name='loyalty', verbose_name='用户')
    points_balance = models.PositiveIntegerField(default=0, verbose_name='积分余额')
    lifetime_points = models.PositiveIntegerField(default=0, verbose_name='累计积分')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='bronze', verbose_name='会员等级')
    last_spin = models.DateField(null=True, blank=True, verbose_name='上次转盘日期')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loyalty_points'
        verbose_name = '积分账户'
        verbose_name_plural = '积分账户'

    def __str__(self):
        return f'{self.user.name} — {self.points_balance}pts ({self.get_tier_display()})'

    def update_tier(self):
        lp = self.lifetime_points
        if lp >= 5000:
            self.tier = 'platinum'
        elif lp >= 1000:
            self.tier = 'gold'
        elif lp >= 200:
            self.tier = 'silver'
        else:
            self.tier = 'bronze'

    def next_tier_threshold(self):
        thresholds = {'bronze': 200, 'silver': 1000, 'gold': 5000, 'platinum': None}
        return thresholds.get(self.tier)

    def can_spin(self):
        from datetime import date
        return self.last_spin != date.today()

    @property
    def last_spin_today(self):
        from datetime import date
        return self.last_spin == date.today()


class PointTransaction(models.Model):
    """Individual point earn/spend transactions."""
    REASON_CHOICES = [
        ('purchase', '购买'),
        ('review', '评价'),
        ('daily_spin', '每日转盘'),
        ('referral', '推荐好友'),
        ('redeem', '积分兑换'),
        ('admin', '管理员调整'),
    ]

    user = models.ForeignKey(SiteUser, on_delete=models.CASCADE,
                              related_name='point_transactions', verbose_name='用户')
    points = models.IntegerField(verbose_name='积分变动(正=增加,负=扣除)')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, verbose_name='原因')
    description = models.CharField(max_length=200, blank=True, default='', verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'point_transaction'
        ordering = ['-created_at']
        verbose_name = '积分流水'
        verbose_name_plural = '积分流水'

    def __str__(self):
        sign = '+' if self.points > 0 else ''
        return f'{self.user.name} {sign}{self.points} ({self.get_reason_display()})'


class UserFollowedShop(models.Model):
    """Tracks which publishers/shops a SiteUser follows."""
    user = models.ForeignKey(SiteUser, on_delete=models.CASCADE,
                              related_name='followed_shops', verbose_name='用户')
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE,
                                   related_name='followers', verbose_name='出版商')
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_followed_shop'
        unique_together = ('user', 'publisher')
        ordering = ['-followed_at']
        verbose_name = '关注的店铺'
        verbose_name_plural = '关注的店铺'

    def __str__(self):
        return f'{self.user.name} → {self.publisher.publisher_name}'


class UserFollowedVendor(models.Model):
    """Tracks which marketplace vendors a SiteUser follows."""
    user = models.ForeignKey(SiteUser, on_delete=models.CASCADE,
                              related_name='followed_vendors', verbose_name='用户')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE,
                                related_name='followers', verbose_name='卖家')
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_followed_vendor'
        unique_together = ('user', 'vendor')
        ordering = ['-followed_at']
        verbose_name = '关注的卖家'
        verbose_name_plural = '关注的卖家'

    def __str__(self):
        return f'{self.user.name} → {self.vendor.company_name}'


CONVERSATION_TYPE_CHOICES = [
    ('buyer_seller', '买家-卖家'),
    ('support', '用户-客服'),
    ('vendor_support', '卖家-客服'),
]

SENDER_TYPE_CHOICES = [
    ('buyer', '买家'),
    ('vendor', '卖家'),
    ('admin', '管理员'),
]


class Conversation(models.Model):
    """Direct messaging conversation. AI chatbot remains separate for support/admin interactions."""
    conversation_type = models.CharField(max_length=20, choices=CONVERSATION_TYPE_CHOICES, default='support', verbose_name='会话类型')
    buyer = models.ForeignKey(SiteUser, on_delete=models.CASCADE, null=True, blank=True, related_name='buyer_conversations', verbose_name='买家')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True, related_name='vendor_conversations', verbose_name='卖家')
    subject = models.CharField(max_length=200, blank=True, default='', verbose_name='主题')
    ref_item_type = models.CharField(max_length=20, blank=True, default='', verbose_name='商品类型')
    ref_item_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='商品ID')
    is_closed = models.BooleanField(default=False, verbose_name='已关闭')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversation'
        ordering = ['-updated_at']
        verbose_name = '会话'
        verbose_name_plural = '会话'

    def __str__(self):
        return self.subject or f'{self.get_conversation_type_display()} #{self.pk}'


class DirectMessage(models.Model):
    """Message inside a direct conversation."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='direct_messages', verbose_name='会话')
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES, verbose_name='发送方类型')
    sender_name = models.CharField(max_length=100, blank=True, default='', verbose_name='发送方名称')
    content = models.TextField(verbose_name='内容')
    attachment = models.FileField(upload_to='message_attachments/%Y/%m/', blank=True, null=True, verbose_name='附件')
    is_read = models.BooleanField(default=False, verbose_name='已读')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'direct_message'
        ordering = ['created_at']
        verbose_name = '消息'
        verbose_name_plural = '消息'

    def __str__(self):
        return f'[{self.sender_type}] {self.content[:60]}'


# 创建(同步)数据表命令
# 创建数据库db_book
# python manage.py makemigrations
# python manage.py migrate
