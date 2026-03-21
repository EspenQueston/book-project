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
    password = models.CharField(max_length=32, verbose_name="密码")
    name = models.CharField(max_length=32, verbose_name="名字")

    # 指定数据表名称（未指定即为默认类名）
    class Meta:
        db_table = "manager"


# 出版社类
class Publisher(models.Model):
    # 出版社名称
    publisher_name = models.CharField(max_length=32, verbose_name="出版社名称")
    # 出版社地址
    publisher_address = models.CharField(max_length=32, verbose_name="出版社地址")

    # 指定数据表名称（未指定即为默认类名）
    class Meta:
        db_table = "publisher"


# 图书类
class Book(models.Model):
    # 图书id
    id = models.AutoField(primary_key=True)
    # 图书名称
    name = models.CharField(max_length=32)
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
    price = models.DecimalField(max_digits=5, decimal_places=2)
    # 库存
    inventory = models.IntegerField(verbose_name='库存数')
    # 销量
    sale_num = models.IntegerField(verbose_name='卖出数')
    # 出版社（一对一 外键）
    publisher = models.ForeignKey(to='Publisher', on_delete=models.CASCADE)

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
    ('credit_card', '信用卡'),
    ('debit_card', '借记卡'),
    ('paypal', 'PayPal'),
    ('alipay', '支付宝'),
    ('wechat_pay', '微信支付'),
    ('bank_transfer', '银行转账'),
    ('cash_on_delivery', '货到付款'),
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
    customer_email = models.EmailField(verbose_name="客户邮箱")
    customer_phone = models.CharField(max_length=20, verbose_name="微信/电话号码")
    
    # 国家信息 (仅用于数字产品)
    country = models.CharField(max_length=50, default='China', verbose_name="国家")
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
    
    def is_payment_window_expired(self):
        """Check if 30-minute payment window has expired for unpaid orders"""
        from datetime import timedelta
        if self.status != 'payment_pending':
            return False
        
        expiration_time = self.created_at + timedelta(minutes=30)
        return timezone.now() > expiration_time
    
    def get_payment_time_remaining(self):
        """Get remaining time to pay in seconds"""
        from datetime import timedelta
        if self.status != 'payment_pending':
            return 0
        
        expiration_time = self.created_at + timedelta(minutes=30)
        remaining = expiration_time - timezone.now()
        return max(0, int(remaining.total_seconds()))
    
    def auto_cancel_if_expired(self):
        """Auto-cancel order if payment window expired"""
        if self.is_payment_window_expired():
            self.status = 'cancelled'
            self.save()
            return True
        return False
    
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
    session_key = models.CharField(max_length=40, verbose_name="会话密钥")
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


# 创建(同步)数据表命令
# 创建数据库db_book
# python manage.py makemigrations
# python manage.py migrate
