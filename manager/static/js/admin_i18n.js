/**
 * Admin Panel i18n - Chinese/English/French Translation System
 * Uses dictionary-based text node replacement + data-zh/data-en/data-fr attribute support.
 * Language choice is persisted in localStorage('adminLang').
 * Supports: zh (Chinese), en (English), fr (French)
 */
(function () {
    'use strict';

    /* ============================
     * English Translation Dictionary (Chinese → English)
     * Keys sorted longest-first at runtime to ensure proper matching.
     * ============================ */
    var T = {
        // ---------- Page Titles ----------
        '管理员仪表板 - DUNO 360': 'Dashboard - DUNO 360',
        '图书列表 - DUNO 360': 'Books - DUNO 360',
        '作者列表 - DUNO 360': 'Authors - DUNO 360',
        '出版社列表 - DUNO 360': 'Publishers - DUNO 360',
        '订单管理 - DUNO 360': 'Orders - DUNO 360',
        '卖家管理 - DUNO 360': 'Vendors - DUNO 360',
        '用户管理 - DUNO 360': 'Users - DUNO 360',
        '通知管理 - DUNO 360': 'Notifications - DUNO 360',
        '博客管理 - DUNO 360': 'Blog - DUNO 360',
        '邮件管理 - DUNO 360': 'Email - DUNO 360',
        '消息管理 - DUNO 360': 'Messages - DUNO 360',

        // ---------- Sidebar / Navigation ----------
        '管理面板': 'Admin Panel',
        '欢迎回来，': 'Welcome, ',
        '仪表板': 'Dashboard',
        '图书管理': 'Books',
        '作者管理': 'Authors',
        '出版社管理': 'Publishers',
        '订单管理': 'Orders',
        '博客管理': 'Blog',
        '消息管理': 'Messages',
        '邮件管理': 'Email',
        '平台管理': 'Platform',
        '用户管理': 'Users',
        '卖家管理': 'Vendors',
        '查看网站': 'View Site',
        '退出登录': 'Logout',
        '退出': 'Logout',

        // ---------- Dashboard ----------
        '智能数据分析仪表板': 'Analytics Dashboard',
        '系统概览 · 数据分析 · 业务洞察': 'Overview · Analytics · Insights',
        '图书总数': 'Total Books',
        '总收入': 'Total Revenue',
        '订单总数': 'Total Orders',
        '库存预警': 'Low Stock Alert',
        '作者总数': 'Total Authors',
        '本月订单': 'Monthly Orders',
        '本月收入': 'Monthly Revenue',
        '近7日销售趋势': '7-Day Sales Trend',
        '订单状态分布': 'Order Status',
        '出版社图书分布': 'Publisher Distribution',
        '热销图书：销量 vs 库存': 'Top Books: Sales vs Stock',
        '近6月订单趋势': '6-Month Trend',
        '图书价格区间分布': 'Price Distribution',
        '热销图书 TOP 5': 'Top 5 Bestsellers',
        '最近订单动态': 'Recent Orders',
        '暂无数据': 'No data',
        '暂无订单': 'No orders',

        // ---------- Common UI ----------
        '搜索': 'Search',
        '筛选': 'Filter',
        '重置': 'Reset',
        '添加': 'Add',
        '编辑': 'Edit',
        '删除': 'Delete',
        '保存': 'Save',
        '取消': 'Cancel',
        '确定': 'Confirm',
        '确认': 'Confirm',
        '关闭': 'Close',
        '返回': 'Back',
        '提交': 'Submit',
        '导出': 'Export',
        '刷新': 'Refresh',
        '加载中...': 'Loading...',
        '操作成功': 'Success',
        '操作失败': 'Failed',
        '所有状态': 'All Status',
        '全部状态': 'All Status',
        '所有类型': 'All Types',

        // ---------- Table Headers ----------
        '排名': 'Rank',
        '序号': 'No.',
        '图书名称': 'Book Name',
        '书名': 'Title',
        '封面': 'Cover',
        '作者': 'Author',
        '价格': 'Price',
        '描述': 'Description',
        '销量': 'Sales',
        '库存': 'Stock',
        '库存量': 'Stock',
        '操作': 'Actions',
        '订单号': 'Order No.',
        '客户': 'Customer',
        '金额': 'Amount',
        '总金额': 'Total',
        '状态': 'Status',
        '日期': 'Date',
        '时间': 'Time',
        '姓名': 'Name',
        '年龄': 'Age',
        '性别': 'Gender',
        '电话': 'Phone',
        '邮箱': 'Email',
        '地址': 'Address',
        '注册时间': 'Registered',
        '创建时间': 'Created',
        '更新时间': 'Updated',

        // ---------- Publisher ----------
        '出版社名称': 'Publisher Name',
        '出版社地址': 'Publisher Address',
        '城市': 'City',
        '出版社列表': 'Publisher List',
        '添加出版社': 'Add Publisher',
        '编辑出版社': 'Edit Publisher',
        '删除出版社': 'Delete Publisher',

        // ---------- Book ----------
        '图书列表': 'Book List',
        '添加图书': 'Add Book',
        '编辑图书': 'Edit Book',
        '删除图书': 'Delete Book',
        '出版社': 'Publisher',

        // ---------- Author ----------
        '作者列表': 'Author List',
        '添加作者': 'Add Author',
        '编辑作者': 'Edit Author',
        '删除作者': 'Delete Author',
        '男': 'Male',
        '女': 'Female',

        // ---------- Order ----------
        '订单列表': 'Order List',
        '订单详情': 'Order Details',
        '付款状态': 'Payment',
        '待付款': 'Pending',
        '待处理': 'Pending',
        '处理中': 'Processing',
        '已发货': 'Shipped',
        '已完成': 'Completed',
        '已取消': 'Cancelled',
        '已退款': 'Refunded',
        '支付完成': 'Paid',
        '未支付': 'Unpaid',
        '客户名': 'Customer',
        '客户名称': 'Customer Name',
        '收货地址': 'Shipping Address',
        '商品数量': 'Quantity',
        '订单备注': 'Notes',
        '管理员备注': 'Admin Notes',
        '下单时间': 'Order Date',
        '查看详情': 'View Details',
        '更新状态': 'Update Status',
        '删除订单': 'Delete Order',
        '导出订单': 'Export Orders',

        // ---------- Vendor ----------
        '卖家列表': 'Vendor List',
        '添加卖家': 'Add Vendor',
        '编辑卖家': 'Edit Vendor',
        '删除卖家': 'Delete Vendor',
        '店铺名称': 'Store Name',
        '联系人': 'Contact',
        '佣金率': 'Commission',
        '图书数': 'Books',
        '待审核': 'Pending',
        '已批准': 'Approved',
        '已拒绝': 'Rejected',
        '已暂停': 'Suspended',
        '更改状态': 'Change Status',
        '批准': 'Approve',
        '拒绝': 'Reject',
        '暂停': 'Suspend',
        '管理平台卖家和店铺': 'Manage platform vendors & stores',
        '位卖家': ' vendors',
        '共': 'Total ',
        '密码': 'Password',

        // ---------- User Management ----------
        '用户列表': 'User List',
        '添加用户': 'Add User',
        '编辑用户': 'Edit User',
        '删除用户': 'Delete User',
        '头像': 'Avatar',
        '活跃': 'Active',
        '已禁用': 'Disabled',
        '启用': 'Enable',
        '禁用': 'Disable',
        '管理平台注册用户': 'Manage registered users',
        '位用户': ' users',
        '搜索姓名、邮箱或电话...': 'Search name, email or phone...',

        // ---------- Notification ----------
        '通知管理': 'Notifications',
        '通知列表': 'Notification List',
        '通知中心': 'Notifications',
        '全部已读': 'Mark All Read',
        '暂无通知': 'No notifications',
        '查看全部通知': 'View All',
        '清空已读': 'Clear Read',
        '清空全部通知': 'Clear All',
        '未读通知': 'Unread',
        '已读通知': 'Read',
        '总通知数': 'Total',
        '通知类型': 'Types',
        '未读': 'Unread',
        '已读': 'Read',
        '标为已读': 'Mark Read',
        '前往': 'Go to',
        '查看': 'View',
        '前往相关页面': 'Go to page',
        '条未读': ' unread',
        '条通知': ' notifications',
        '新订单': 'New Order',
        '新用户注册': 'New User',
        '待下单提醒': 'Abandoned Cart',
        '未完成注册': 'Incomplete Registration',
        '订单已付款': 'Order Paid',
        '新卖家注册': 'New Vendor',
        '库存不足': 'Low Stock',
        '查看和管理所有系统通知': 'View and manage all notifications',
        '系统暂时没有通知，有新的事件时会自动显示': 'No notifications right now. New events will appear here.',
        '全部清除': 'Clear All',
        '清除已读': 'Clear Read',

        // ---------- Blog ----------
        '博客列表': 'Blog List',
        '添加文章': 'Add Post',
        '编辑文章': 'Edit Post',
        '删除文章': 'Delete Post',
        '标题': 'Title',
        '分类': 'Category',
        '发布日期': 'Published',
        '浏览次数': 'Views',
        '已发布': 'Published',
        '草稿': 'Draft',
        '分类管理': 'Categories',
        '管理博客文章和分类': 'Manage blog posts & categories',
        '篇文章': ' posts',

        // ---------- Email / Messages ----------
        '消息中心': 'Messages',
        '邮件': 'Email',
        '收件箱': 'Inbox',
        '发件箱': 'Sent',
        '草稿箱': 'Drafts',
        '垃圾箱': 'Trash',
        '写邮件': 'Compose',
        '回复': 'Reply',
        '转发': 'Forward',
        '发件人': 'From',
        '收件人': 'To',
        '主题': 'Subject',
        '附件': 'Attachment',
        '标记已读': 'Mark Read',
        '标记未读': 'Mark Unread',

        // ---------- Breadcrumbs ----------
        '图书': 'Books',
        '作家': 'Authors',

        // ---------- Header cards ----------
        '欢迎回来': 'Welcome back',
        '管理员': 'Admin',
        '今天是': "Today's date:",
        '搜索图书名称...': 'Search books...',
        '搜索作者姓名...': 'Search authors...',
        '搜索出版社...': 'Search publishers...',
        '搜索订单号或客户名...': 'Search order or customer...',
        '搜索店铺名、联系人或邮箱...': 'Search store, contact or email...',
        '搜索文章标题...': 'Search post title...',

        // ---------- Confirmations ----------
        '确定要删除吗？此操作不可撤销。': 'Are you sure? This cannot be undone.',
        '此操作不可撤销': 'This cannot be undone',
        '状态已更新': 'Status updated',
        '已删除': 'Deleted',
        '已更新': 'Updated',
        '已添加': 'Added',

        // ---------- Form labels ----------
        '图书名称': 'Book Name',
        '图书描述': 'Description',
        '图书价格': 'Price',
        '图书库存': 'Stock',
        '选择出版社': 'Select Publisher',
        '选择作者': 'Select Author',
        '上传封面': 'Upload Cover',
        '联系人姓名': 'Contact Name',
        '公司名称': 'Company Name',
        '佣金率 (%)': 'Commission (%)',

        // ---------- Chatbot / AI Config ----------
        'AI 聊天配置 - DUNO 360': 'AI Chat Config - DUNO 360',
        'AI 聊天配置': 'AI Chat Config',
        'AI 聊天机器人配置': 'AI Chatbot Configuration',
        'AI 聊天机器人': 'AI Chatbot',
        'AI 聊天': 'AI Chat',
        '管理 AI 对话服务、API 密钥和前端小部件': 'Manage AI chat service, API keys & widgets',
        '配置 AI 助手 · 管理 API 密钥 · 监控对话 · 实时平台数据': 'Configure AI · Manage API Keys · Monitor Chats · Real-time Data',
        '返回仪表盘': 'Back to Dashboard',
        '总对话': 'Total Conversations',
        '总对话数': 'Total Conversations',
        '总消息': 'Total Messages',
        '总消息数': 'Total Messages',
        '当前供应商': 'Current Provider',
        '小部件状态': 'Widget Status',
        '运行中': 'Running',
        '已禁用': 'Disabled',
        '活跃会话': 'Active Sessions',
        '消耗 Tokens': 'Tokens Used',
        '配置': 'Settings',
        '测试 API': 'Test API',
        '对话记录': 'Chat History',
        '对话会话记录': 'Chat Session Records',
        '平台上下文': 'Platform Context',
        '免费 API 指南': 'Free API Guide',
        'AI 供应商': 'AI Provider',
        'AI 供应商选择': 'AI Provider Selection',
        'API 凭证 & 模型': 'API Credentials & Model',
        'API 凭证': 'API Credentials',
        '模型 ID': 'Model ID',
        '模型名称': 'Model Name',
        'API 密钥': 'API Key',
        '输入 API 密钥（以 *** 开头表示保持不变）': 'Enter API key (*** means keep unchanged)',
        '含 * 的值不会被覆盖': 'Values with * will not be overwritten',
        '留空使用默认模型': 'Leave blank for default model',
        '留空用默认': 'Leave blank for default',
        '自定义 API 端点': 'Custom API Endpoint',
        '快速填充：': 'Quick Fill:',
        '小部件外观': 'Widget Appearance',
        '小部件设置': 'Widget Settings',
        '副标题': 'Subtitle',
        '欢迎语': 'Welcome Message',
        '在公开页面显示': 'Show on Public Pages',
        '公开页面显示': 'Show on Public Pages',
        '访客和注册用户可以使用聊天功能': 'Visitors and registered users can use chat',
        '在管理后台显示': 'Show on Admin Panel',
        '管理页面显示': 'Show on Admin Pages',
        '管理员可以在后台使用 AI 助手': 'Admins can use AI assistant in backend',
        '启用聊天机器人': 'Enable Chatbot',
        '关闭后聊天窗口将不再显示': 'Chat widget will be hidden when disabled',
        'AI 参数调优': 'AI Parameter Tuning',
        'AI 参数': 'AI Parameters',
        '系统提示词': 'System Prompt',
        '留空则使用默认提示词（含平台数据自动注入）': 'Leave blank for default (auto platform data injection)',
        '平台实时数据（图书列表、作者、出版社、销量统计）会自动注入，无需手动填写。': 'Real-time platform data (books, authors, publishers, sales) is auto-injected.',
        '最大 Token 数': 'Max Tokens',
        '温度（随机性）': 'Temperature (Randomness)',
        '温度 (随机性)': 'Temperature (Randomness)',
        '精准': 'Precise',
        '精确 0': 'Precise 0',
        '创意': 'Creative',
        '创造 2': 'Creative 2',
        '每会话最大消息数': 'Max Messages per Session',
        '建议': 'Recommended',
        '先测试': 'Test First',
        '保存配置': 'Save Configuration',
        '保存中...': 'Saving...',
        '配置已保存': 'Configuration Saved',
        '保存失败': 'Save Failed',
        '实时 API 测试': 'Real-time API Test',
        '使用已保存配置 + 平台实时数据测试': 'Test with saved config + real-time data',
        '在更改配置后，使用此工具验证 API 密钥和模型是否正常工作。': 'After changes, use this tool to verify your API key and model work correctly.',
        '测试消息': 'Test Message',
        '输入测试消息...': 'Enter test message...',
        '快速测试：': 'Quick Tests:',
        '介绍平台热销图书': 'Show popular books',
        '有哪些科幻类图书？': 'Any sci-fi books?',
        '如何查看我的订单？': 'How to check my order?',
        '推荐一本适合初学者的书': 'Recommend a beginner book',
        '平台共有多少本书？': 'How many books on platform?',
        '你好！请简单介绍一下你自己。': 'Hello! Please briefly introduce yourself.',
        '你好！请介绍一下这个图书平台上有哪些热门图书。': 'Hello! What are the popular books on this platform?',
        '运行测试': 'Run Test',
        '测试中...': 'Testing...',
        'API 测试成功': 'API Test Passed',
        '最近对话': 'Recent Conversations',
        '确认清除所有对话记录？此操作不可撤销。': 'Clear all records? This cannot be undone.',
        '确认清除所有对话记录？': 'Confirm clear all conversation records?',
        '会话标识': 'Session ID',
        '用户': 'User',
        '消息数': 'Messages',
        '开始时间': 'Start Time',
        '最后活跃': 'Last Active',
        '匿名': 'Anonymous',
        '已结束': 'Ended',
        '暂无对话记录': 'No conversation records',
        '清除全部': 'Clear All',
        '清除失败': 'Clear Failed',
        '实时平台上下文': 'Real-time Platform Context',
        '每次请求自动刷新': 'Auto-refreshed per request',
        '以下数据会在每次 AI 对话时实时注入到系统提示词中，让 AI 拥有平台的最新完整知识。数据库变化后下一次对话即生效，无需任何手动操作。': 'Data below is injected into the AI system prompt in real-time. Database changes take effect on the next conversation.',
        '图书（实时）': 'Books (Live)',
        '作者（实时）': 'Authors (Live)',
        '出版社（实时）': 'Publishers (Live)',
        '上下文预览（发送给 AI 的真实内容）': 'Context Preview (actual content sent to AI)',
        '刷新预览': 'Refresh Preview',
        '点击"刷新预览"查看将发送给 AI 的实时平台数据...': 'Click "Refresh" to see real-time data sent to AI...',
        '免费 AI API 平台推荐': 'Free AI API Platforms',
        '以下平台提供免费或丰厚的免费额度。推荐': 'These platforms offer free or generous free tiers. Recommended:',
        '（一个 Key，20+ 免费模型）或': '(one key, 20+ free models) or',
        '（Gemini 免费额度极大）。': '(very generous Gemini free tier).',
        '免费模型': 'Free Models',
        '说明': 'Description',
        '获取 API Key': 'Get API Key',
        '获取密钥': 'Get Key',
        '当前使用': 'In Use',
        '免费模型（点击即可应用）': 'Free Models (click to apply)',
        '点击任意模型卡片，自动填充到配置页面并切换至 OpenRouter 供应商。': 'Click any model card to auto-fill and switch to OpenRouter.',
        '已应用模型 ID，记得保存配置': 'Model ID applied, remember to save',
        '已填充模型 ID': 'Model ID filled',
        '请输入测试消息': 'Please enter a test message',
        '实时数据': 'Live Data',
        '本书': ' books',
        '位作者': ' authors',

        // ---------- Add/Edit Book Form ----------
        '添加图书 - DUNO 360': 'Add Book - DUNO 360',
        '添加新图书': 'Add New Book',
        '为系统添加新的图书信息': 'Add new book to the system',
        '快速导航': 'Quick Navigation',
        '退出系统': 'Logout',
        '请输入图书名称': 'Enter book name',
        '请输入图书的详细描述信息...': 'Enter book description...',
        '详细的图书描述有助于读者了解图书内容': 'Descriptions help readers understand the book',
        '价格 (元)': 'Price (¥)',
        '库存数量': 'Stock Quantity',
        '销售数量': 'Sales Count',
        '上传封面图片': 'Upload Cover Image',
        '支持 JPG, PNG, GIF 格式': 'Supports JPG, PNG, GIF',
        '最大 5MB': 'Max 5MB',
        '电子书下载': 'Ebook Download',
        '提示：': 'Note:',
        '您可以上传电子书文件（PDF、EPUB等）或提供外部下载链接（如Google Drive、OneDrive等）': 'Upload ebook files (PDF, EPUB, etc.) or provide external download links',
        '上传电子书文件': 'Upload Ebook File',
        '支持格式: PDF, EPUB, MOBI, AZW, TXT, DOC, DOCX': 'Formats: PDF, EPUB, MOBI, AZW, TXT, DOC, DOCX',
        '外部下载链接': 'External Download Link',
        '或提供Google Drive、OneDrive等外部链接': 'Or provide Google Drive, OneDrive links',
        '如不上传，系统将自动生成精美封面': 'If not uploaded, the system will auto-generate a stylish cover',
        '您可以上传电子书文件或提供外部下载链接': 'You can upload an ebook file or provide an external download link',
        '已上传文件': 'File uploaded',
        '当前封面（上传新图片可替换）': 'Current cover (upload new image to replace)',
        '新建': 'New',
        '新建作者': 'New Author',
        '新建出版社': 'New Publisher',
        '请输入作者名称': 'Enter author name',
        '请输入出版社名称': 'Enter publisher name',
        '请输入出版社地址': 'Enter publisher address',
        '创建': 'Create',
        '按住 Ctrl/Cmd 可多选作者': 'Hold Ctrl/Cmd to select multiple',
        '请选择出版社': 'Select a publisher',

        // ---------- Vendor Dashboard ----------
        '业绩概览': 'Performance Overview',
        '平均售价': 'Average Price',
        '上架率': 'Active Rate',
        '畅销图书': 'Best Seller',
        '已售': 'Sold',
        '账户信息': 'Account Info',
        '入驻时间': 'Joined',
        '上架中': 'Active',
        '已下架': 'Delisted',
        '缺货': 'Out of Stock',
        '快捷操作': 'Quick Actions',
        '上架新书': 'List New Book',
        '管理员视图': 'Admin View',
        '我的图书': 'My Books',
        '暂无上架图书': 'No books listed yet',
        '上架第一本书': 'List your first book',
        '下架': 'Delist',
        '上架': 'List',
        'DUNO 360': 'DUNO 360',

        // ---------- Email Account Management ----------
        '邮箱账户管理 - DUNO 360': 'Email Accounts - DUNO 360',
        '邮箱账户管理': 'Email Account Management',
        '返回邮箱': 'Back to Email',
        '网站': 'Website',
        '默认': 'Default',
        'IMAP 服务器': 'IMAP Server',
        'IMAP 端口': 'IMAP Port',
        'SMTP 服务器': 'SMTP Server',
        'SMTP 端口': 'SMTP Port',
        '最后同步': 'Last Sync',
        '测试': 'Test',
        '暂无邮箱账户，请添加一个': 'No email accounts, please add one',
        '添加账户': 'Add Account',
        '添加新邮箱账户': 'Add New Email Account',
        '名称': 'Name',
        '邮箱地址': 'Email Address',
        '用户名': 'Username',
        '通常是邮箱地址': 'Usually the email address',
        '密码 / 应用密码': 'Password / App Password',
        '确定删除账户': 'Confirm delete account',
        '该账户的所有邮件也将被删除。': 'All emails from this account will also be deleted.',

        // ---------- Order Detail ----------
        '联系电话': 'Phone',
        '国家': 'Country',
        '微信/电话': 'WeChat / Phone',
        '客户备注': 'Customer Notes',
        '最后更新': 'Last Updated',
        '支付方式': 'Payment Method',
        '订单状态': 'Order Status',
        '支付状态': 'Payment Status',
        '电子邮箱': 'Email',
        '客户姓名': 'Customer Name',

        // ---------- Form Pages (Add/Edit) ----------
        '首页': 'Home',
        '基本信息': 'Basic Info',
        '返回列表': 'Back to List',
        '文章标题': 'Post Title',
        '文章内容': 'Post Content',
        '摘要': 'Summary',
        '发布设置': 'Publish Settings',
        '无分类': 'No Category',
        '作者名称': 'Author Name',
        '设为精选文章': 'Set as Featured',
        '封面图片': 'Cover Image',
        '保存文章': 'Save Post',
        '保存出版社': 'Save Publisher',
        '保存作者': 'Save Author',
        '出版社信息': 'Publisher Info',
        '作者信息': 'Author Info',
        '关联图书': 'Associated Books',
        '搜索图书名称...': 'Search books...',
        '图书封面': 'Book Cover',
        '点击上传图片': 'Click to upload image',
        '新建文章': 'New Post',
        '保存图书': 'Save Book',
        '支持 JPG、PNG、GIF 格式': 'Supports JPG, PNG, GIF',
        '网络错误': 'Network Error',

        // ---------- Login Page ----------
        '管理员登录': 'Admin Login',
        '请输入账号': 'Enter account',
        '请输入密码': 'Enter password',
        '登录': 'Login',
        '忘记登录信息？': 'Forgot login info?',
        '访问公共图书目录': 'Visit public book catalog',
        '现代化DUNO 360': 'Modern DUNO 360',
        '智能图书管理': 'Smart Book Management',
        '作者信息管理': 'Author Information Management',
        '销售数据统计': 'Sales Data Analytics',
        '安全可靠': 'Secure & Reliable',

        // ---------- Misc ----------
        '暂无': 'N/A',
        '无': 'N/A',
        '是': 'Yes',
        '否': 'No',
        '或': 'or',
        '和': 'and',
        '个': '',
        '本': '',
        '位': '',
        '篇': '',
        '条': '',
        '项': '',

        // ---------- Chart labels (used in JS too) ----------
        '销售额 (¥)': 'Revenue (¥)',
        '订单数': 'Orders',
        '图书数量': 'Books Count',

        // ---------- Vendor Center (卖家中心) ----------
        '卖家中心': 'Vendor Center',
        '我的商品': 'My Products',
        '我的课程': 'My Courses',
        '查看市场': 'View Market',
        '商品': 'Product',
        '添加商品': 'Add Product',
        '搜索商品名称或SKU...': 'Search product name or SKU...',
        '全部': 'All',
        '上架': 'Active',
        '下架': 'Inactive',
        '切换状态': 'Toggle Status',
        '暂无商品': 'No products yet',
        '添加第一个商品': 'Add your first product',
        '确定删除此商品?': 'Delete this product?',
        '确定删除？': 'Confirm delete?',

        // ---------- Course Management (课程管理) ----------
        '课程管理': 'Courses',
        '添加课程': 'Add Course',
        '搜索课程...': 'Search courses...',
        '门课程': ' courses',
        '课程': 'Course',
        '讲师': 'Instructor',
        '级别': 'Level',
        '注册人数': 'Enrollments',
        '课时': 'Lessons',
        '发布': 'Published',
        '推荐': 'Featured',
        '管理内容': 'Manage Content',
        '暂无课程': 'No courses yet',

        // ---------- Course Content Management (课程内容管理) ----------
        '课程内容管理': 'Course Content',
        '编辑课程': 'Edit Course',
        '返回列表': 'Back to List',
        '个章节': ' sections',
        '添加章节': 'Add Section',
        '编辑章节': 'Edit Section',
        '章节标题': 'Section Title',
        '排序': 'Order',
        '暂无章节': 'No sections yet',
        '添加课时': 'Add Lesson',
        '编辑课时': 'Edit Lesson',
        '课时标题': 'Lesson Title',
        '暂无课时': 'No lessons yet',
        '时长(分钟)': 'Duration (min)',
        '课时描述': 'Lesson Description',
        '视频内容': 'Video Content',
        '上传视频文件': 'Upload Video File',
        '或输入视频链接': 'Or Enter Video URL',
        '课件': 'Course Material',
        '免费试看': 'Free Preview',
        '免费': 'Free',
        '视频': 'Video',
        '分钟': 'min',
        '保存中...': 'Saving...',
        '操作失败': 'Operation failed',
        '请输入章节标题': 'Please enter section title',
        '请输入课时标题': 'Please enter lesson title',
        '找不到课时数据': 'Lesson data not found',
        '删除当前视频': 'Remove current video',
        '删除当前PDF': 'Remove current PDF',

        // ---------- Vendor Admin (卖家管理 - Marketplace Overview) ----------
        '管理平台卖家和店铺': 'Manage platform vendors & stores',
        '卖家总数': 'Total Vendors',
        '卖家商品总数': 'Vendor Products',
        '卖家课程总数': 'Vendor Courses',
        '总销量': 'Total Sales',
        '最畅销商品 (全平台)': 'Top Products (Platform)',
        '销量最高卖家': 'Top Vendors by Sales',
        '暂无销售数据': 'No sales data',
        '件': 'pcs',
        '卖家列表': 'Vendor List',
        '位卖家': ' vendors',
        '添加卖家': 'Add Vendor',
        '市场内容': 'Marketplace Content',
        '查看内容': 'View Content',
        '更改状态': 'Change Status',
        '编辑卖家': 'Edit Vendor',
        '删除卖家': 'Delete Vendor',
        '违规删除': 'Remove Violation',
        '该卖家暂无商品': 'No products for this vendor',
        '该卖家暂无课程': 'No courses for this vendor',
        '的市场内容': "'s Marketplace Content",
        '未分类': 'Uncategorized',

        // ---------- Marketplace Admin ----------
        '市场管理': 'Marketplace',
        '商品管理': 'Products',
        '超市管理': 'Supermarket',
        '分类管理': 'Categories',
        '属性管理': 'Attributes',
        '订单管理': 'Orders',
        '市场概览': 'Market Overview',
        '商品总数': 'Total Products',
        '课程总数': 'Total Courses',
        '本月收入': 'Monthly Revenue',

        // ---------- Marketplace Dashboard ----------
        '市场管理仪表板': 'Marketplace Dashboard',
        '概览 · 商品 · 课程 · 超市': 'Overview · Products · Courses · Supermarket',
        '超市商品': 'Supermarket Items',
        '快捷操作': 'Quick Actions',
        '添加超市商品': 'Add Supermarket Item',
        '添加分类': 'Add Category',
        '最近订单': 'Recent Orders',
        '返回主面板': 'Back to Admin',

        // ---------- Marketplace Product Form ----------
        '编辑商品': 'Edit Product',
        '商品名称': 'Product Name',
        '商品描述': 'Product Description',
        '原价': 'Original Price',
        '品牌': 'Brand',
        '状况': 'Condition',
        '全新': 'New',
        '几乎全新': 'Like New',
        '二手': 'Used',
        '翻新': 'Refurbished',
        '重量 (kg)': 'Weight (kg)',
        '主图': 'Main Image',
        '图片2': 'Image 2',
        '图片3': 'Image 3',
        '推荐商品': 'Featured Product',
        '商品属性与可选项': 'Product Attributes & Options',
        '商品属性与可选规格': 'Attributes & Specifications',
        '添加属性': 'Add Attribute',
        '属性名称': 'Attribute Name',
        '属性值': 'Attribute Value',
        '快速添加：': 'Quick Add:',
        '颜色': 'Color',
        '尺寸': 'Size',
        '材质': 'Material',
        '重量': 'Weight',
        '长度': 'Length',
        '宽度': 'Width',
        '高度': 'Height',
        '型号': 'Model',
        '产地': 'Origin',
        '保质期': 'Shelf Life',
        '保存修改': 'Save Changes',
        '选择分类': 'Select Category',
        '-- 选择分类 --': '-- Select Category --',
        '搜索商品...': 'Search products...',
        '件商品': ' products',

        // ---------- Marketplace Course Form ----------
        '课程标题': 'Course Title',
        '课程描述': 'Course Description',
        '时长(小时)': 'Duration (hrs)',
        '课时数': 'Lessons Count',
        '难度级别': 'Difficulty Level',
        '全部级别': 'All Levels',
        '入门': 'Beginner',
        '中级': 'Intermediate',
        '高级': 'Advanced',
        '教学语言': 'Language',
        '预览链接': 'Preview URL',
        '推荐课程': 'Featured Course',

        // ---------- Marketplace Orders ----------
        '市场订单管理': 'Market Order Management',
        '搜索订单号、客户名、邮箱、电话...': 'Search order, customer, email, phone...',
        '全部支付状态': 'All Payment Status',
        '已付款': 'Paid',
        '已送达': 'Delivered',
        '笔订单': ' orders',
        '确认删除订单': 'Confirm Delete Order',
        '此操作不可逆！': 'This cannot be undone!',
        '确认删除': 'Confirm Delete',
        '删除中...': 'Deleting...',
        '删除时发生错误': 'Error deleting',
        '已完成或已送达的订单不能删除！': 'Completed or delivered orders cannot be deleted!',
        '警告：': 'Warning:',

        // ---------- Marketplace Order Detail ----------
        '订单 #': 'Order #',
        '创建时间：': 'Created: ',
        '订单总金额': 'Order Total',
        '客户信息': 'Customer Info',
        '未知': 'Unknown',
        '未提供': 'Not provided',
        '备注': 'Notes',
        '订单时间线': 'Order Timeline',
        '订单创建': 'Order Created',
        '订单确认': 'Order Confirmed',
        '订单发货': 'Order Shipped',
        '订单完成': 'Order Completed',
        '操作选项': 'Actions',
        '更新订单状态': 'Update Order Status',
        '更新支付状态': 'Update Payment',
        '打印订单': 'Print Order',
        '订单商品': 'Order Items',
        '图片': 'Image',
        '商品信息': 'Product Info',
        '类型': 'Type',
        '单价': 'Unit Price',
        '数量': 'Qty',
        '小计': 'Subtotal',
        '无商品': 'No items',
        '商品总数：': 'Total Items: ',
        '订单总计': 'Order Total',
        '更新订单状态失败：': 'Update failed: ',
        '更新订单状态时发生错误': 'Error updating status',
        '更新支付状态失败：': 'Update failed: ',
        '更新支付状态时发生错误': 'Error updating payment',
        '您确定要删除以下订单吗？': 'Are you sure you want to delete this order?',
        '订单号：': 'Order No.: ',
        '客户：': 'Customer: ',
        '订单状态：': 'Order Status: ',
        '订单金额：': 'Order Amount: ',
        '删除后，所有相关的订单项目和历史记录都将被永久删除。': 'All related items and history will be permanently deleted.',
        '交易ID': 'Transaction ID',
        '输入支付交易ID...': 'Enter payment transaction ID...',
        '添加备注信息...': 'Add notes...',

        // ---------- Marketplace Categories ----------
        '分类名称': 'Category Name',
        '版块': 'Section',
        '上级分类': 'Parent Category',
        '暂无分类': 'No categories yet',
        '确定删除该分类？': 'Delete this category?',
        '编辑分类': 'Edit Category',
        '所属版块': 'Section',
        '-- 无 (顶级分类) --': '-- None (Top Level) --',
        '分类图片': 'Category Image',
        '超市': 'Supermarket',

        // ---------- Marketplace Supermarket ----------
        '暂无超市商品': 'No supermarket items yet',
        '编辑超市商品': 'Edit Supermarket Item',
        '单位': 'Unit',
        '个': 'Piece',
        '公斤': 'kg',
        '克': 'g',
        '升': 'Liter',
        '毫升': 'ml',
        '包': 'Pack',
        '盒': 'Box',
        '瓶': 'Bottle',
        '袋': 'Bag',
        '有机食品': 'Organic',
        '前台规格逻辑': 'Product Spec Logic',
        '单值属性显示为商品规格，多值属性显示为用户可选规格。请保持命名一致，避免同一属性出现多种拼写。': 'Single-value shows as spec; multi-value shows as selectable option. Keep naming consistent.',
        '用这里定义前台可选配置与技术规格，例如颜色、尺寸、材质、容量、版本。': 'Define selectable options & specs such as color, size, material, capacity, version.',
        '用这里定义用户可选规格与商品说明，例如包装、净含量、保质期、成分、储存方式。': 'Define selectable specs & product info such as packaging, weight, shelf life, ingredients, storage.',
        '成分': 'Ingredients',
        '储存方式': 'Storage',
        '规格': 'Specification',
        '生产日期': 'Production Date',
        '营养成分': 'Nutrition Facts',
        '过敏原': 'Allergens',

        // ---------- Vendor Dashboard ----------
        '卖家仪表板': 'Vendor Dashboard',
        '数据概览': 'Data Overview',
        '管理商品': 'Manage Products',
        '管理课程': 'Manage Courses',
        '近7天收入趋势': '7-Day Revenue Trend',
        '商品分类分布': 'Category Distribution',
        '收入构成': 'Revenue Breakdown',
        '商品收入': 'Product Revenue',
        '课程收入': 'Course Revenue',
        '上架商品': 'Active Products',
        '下架商品': 'Inactive Products',
        '发布课程': 'Published Courses',
        '课程注册': 'Course Enrollments',
        '热销商品 TOP 5': 'Top 5 Products',
        '暂无销量数据': 'No sales data yet',

        // ---------- Vendor Product Form ----------
        '英文名称': 'English Name',
        '商品状况': 'Product Condition',
        '选择分类': 'Select Category',
        '价格与库存': 'Pricing & Stock',
        '销售价格': 'Selling Price',
        '商品图片': 'Product Images',
        '商品属性': 'Product Attributes',
        '立即上架': 'Publish Now',
        '填写商品信息': 'Fill in product details',

        // ---------- Vendor Course Form ----------
        '英文标题': 'English Title',
        '讲师名称': 'Instructor Name',
        '价格信息': 'Pricing',
        '课程价格': 'Course Price',
        '语言': 'Language',
        '课程详情': 'Course Details',
        '课程时长 (小时)': 'Duration (hours)',
        '课程节数': 'Lesson Count',
        '预览视频URL': 'Preview Video URL',
        '课程封面': 'Course Cover',
        '立即发布': 'Publish Now',
        '填写课程信息': 'Fill in course details',
        '推荐尺寸: 800×450px, 最大5MB': 'Recommended: 800×450px, max 5MB',

        // ---------- Marketplace misc ----------
        '当前: ': 'Current: ',
        '支持 MP4, WebM, OGG 等格式，最大 500MB': 'MP4, WebM, OGG etc., max 500MB',
        '点击上方"添加章节"开始创建课程内容': 'Click "Add Section" above to start building course content',

        // ---------- Vendor list JS strings (toasts, modals, confirms) ----------
        '暂无卖家': 'No vendors yet',
        '点击"添加卖家"开始管理': 'Click "Add Vendor" to get started',
        '确定要将该卖家状态更改为"': 'Change vendor status to "',
        '"吗？': '"?',
        '状态已更新': 'Status updated',
        '确定要删除卖家 "': 'Delete vendor "',
        '" 吗？此操作不可撤销。': '"? This cannot be undone.',
        '卖家已删除': 'Vendor deleted',
        '删除失败': 'Delete failed',
        '违规删除': 'Remove Violation',
        '确定要删除': 'Are you sure you want to delete ',
        '" 吗？该操作将从平台中移除此内容。': '"? This content will be removed from the platform.',
        '已删除': 'Deleted',
        '卖家已更新': 'Vendor updated',
        '卖家已添加': 'Vendor added',
        '加载失败': 'Failed to load',
        '查看内容': 'View Content',

        // ---------- Course content JS strings ----------
        '确定删除章节 "': 'Delete section "',
        '" 及其所有课时？': '" and all its lessons?',
        '操作失败': 'Operation failed',
        '确定删除课时 "': 'Delete lesson "',
        '" ？': '"?',
        '例如: 第一章 基础入门': 'e.g. Chapter 1: Getting Started',
        'YouTube, Bilibili 等嵌入链接': 'YouTube, Bilibili embed links',

        // ---------- Vendor product page JS strings ----------
        '切换状态': 'Toggle Status',
        '状态切换失败': 'Status toggle failed',
        '状态切换时发生错误': 'Error toggling status',

        // ---------- Product/Course form misc ----------
        '保存修改': 'Save Changes',
        '-- 选择分类 --': '-- Select Category --',
        '推荐商品': 'Featured Product',
        '推荐课程': 'Featured Course',

        // ---------- Vendor detail panel ----------
        '的市场内容': "'s Marketplace Content",
        '注册': 'Enrolled',

        // ---------- Pagination ----------
        '上一页': 'Previous',
        '下一页': 'Next',

        // ---------- Marketplace title (dashboard standalone) ----------
        '市场管理 - Dashboard': 'Marketplace - Dashboard',
        'Marketplace Admin': 'Marketplace Admin',
    };

    /* ============================
     * French Translation Dictionary (Chinese → French)
     * ============================ */
    var F = {
        // ---------- Page Titles ----------
        '管理员仪表板 - DUNO 360': 'Tableau de bord - DUNO 360',
        '图书列表 - DUNO 360': 'Livres - DUNO 360',
        '作者列表 - DUNO 360': 'Auteurs - DUNO 360',
        '出版社列表 - DUNO 360': 'Éditeurs - DUNO 360',
        '订单管理 - DUNO 360': 'Commandes - DUNO 360',
        '卖家管理 - DUNO 360': 'Vendeurs - DUNO 360',
        '用户管理 - DUNO 360': 'Utilisateurs - DUNO 360',
        '通知管理 - DUNO 360': 'Notifications - DUNO 360',
        '博客管理 - DUNO 360': 'Blog - DUNO 360',
        '邮件管理 - DUNO 360': 'E-mail - DUNO 360',
        '消息管理 - DUNO 360': 'Messages - DUNO 360',

        // ---------- Sidebar / Navigation ----------
        '管理面板': 'Panneau d\'administration',
        '欢迎回来，': 'Bienvenue, ',
        '仪表板': 'Tableau de bord',
        '图书管理': 'Livres',
        '作者管理': 'Auteurs',
        '出版社管理': 'Éditeurs',
        '订单管理': 'Commandes',
        '博客管理': 'Blog',
        '消息管理': 'Messages',
        '邮件管理': 'E-mail',
        '平台管理': 'Plateforme',
        '用户管理': 'Utilisateurs',
        '卖家管理': 'Vendeurs',
        '查看网站': 'Voir le site',
        '退出登录': 'Déconnexion',
        '退出': 'Déconnexion',

        // ---------- Dashboard ----------
        '智能数据分析仪表板': 'Tableau de bord analytique',
        '系统概览 · 数据分析 · 业务洞察': 'Aperçu · Analyse · Perspectives',
        '图书总数': 'Total livres',
        '总收入': 'Revenu total',
        '订单总数': 'Total commandes',
        '库存预警': 'Alerte stock bas',
        '作者总数': 'Total auteurs',
        '本月订单': 'Commandes du mois',
        '本月收入': 'Revenu du mois',
        '近7日销售趋势': 'Tendance 7 jours',
        '订单状态分布': 'Statut commandes',
        '出版社图书分布': 'Distribution éditeurs',
        '热销图书：销量 vs 库存': 'Top livres : Ventes vs Stock',
        '近6月订单趋势': 'Tendance 6 mois',
        '图书价格区间分布': 'Distribution prix',
        '热销图书 TOP 5': 'Top 5 meilleures ventes',
        '最近订单动态': 'Commandes récentes',
        '暂无数据': 'Aucune donnée',
        '暂无订单': 'Aucune commande',

        // ---------- Common UI ----------
        '搜索': 'Chercher',
        '筛选': 'Filtrer',
        '重置': 'Réinitialiser',
        '添加': 'Ajouter',
        '编辑': 'Modifier',
        '删除': 'Supprimer',
        '保存': 'Enregistrer',
        '取消': 'Annuler',
        '确定': 'Confirmer',
        '确认': 'Confirmer',
        '关闭': 'Fermer',
        '返回': 'Retour',
        '提交': 'Soumettre',
        '导出': 'Exporter',
        '刷新': 'Actualiser',
        '加载中...': 'Chargement...',
        '操作成功': 'Succès',
        '操作失败': 'Échec',
        '所有状态': 'Tous les statuts',
        '全部状态': 'Tous les statuts',
        '所有类型': 'Tous les types',

        // ---------- Table Headers ----------
        '排名': 'Rang',
        '序号': 'N°',
        '图书名称': 'Nom du livre',
        '书名': 'Titre',
        '封面': 'Couverture',
        '作者': 'Auteur',
        '价格': 'Prix',
        '描述': 'Description',
        '销量': 'Ventes',
        '库存': 'Stock',
        '库存量': 'Stock',
        '操作': 'Actions',
        '订单号': 'N° commande',
        '客户': 'Client',
        '金额': 'Montant',
        '总金额': 'Total',
        '状态': 'Statut',
        '日期': 'Date',
        '时间': 'Heure',
        '姓名': 'Nom',
        '年龄': 'Âge',
        '性别': 'Genre',
        '电话': 'Téléphone',
        '邮箱': 'E-mail',
        '地址': 'Adresse',
        '注册时间': 'Inscrit le',
        '创建时间': 'Créé le',
        '更新时间': 'Mis à jour',

        // ---------- Publisher ----------
        '出版社名称': 'Nom de l\'éditeur',
        '出版社地址': 'Adresse de l\'éditeur',
        '城市': 'Ville',
        '出版社列表': 'Liste des éditeurs',
        '添加出版社': 'Ajouter un éditeur',
        '编辑出版社': 'Modifier l\'éditeur',
        '删除出版社': 'Supprimer l\'éditeur',

        // ---------- Book ----------
        '图书列表': 'Liste des livres',
        '添加图书': 'Ajouter un livre',
        '编辑图书': 'Modifier le livre',
        '删除图书': 'Supprimer le livre',
        '出版社': 'Éditeur',

        // ---------- Author ----------
        '作者列表': 'Liste des auteurs',
        '添加作者': 'Ajouter un auteur',
        '编辑作者': 'Modifier l\'auteur',
        '删除作者': 'Supprimer l\'auteur',
        '男': 'Homme',
        '女': 'Femme',

        // ---------- Order ----------
        '订单列表': 'Liste des commandes',
        '订单详情': 'Détails de la commande',
        '付款状态': 'Paiement',
        '待付款': 'En attente',
        '待处理': 'En attente',
        '处理中': 'En cours',
        '已发货': 'Expédié',
        '已完成': 'Terminé',
        '已取消': 'Annulé',
        '已退款': 'Remboursé',
        '支付完成': 'Payé',
        '未支付': 'Non payé',
        '客户名': 'Client',
        '客户名称': 'Nom du client',
        '收货地址': 'Adresse de livraison',
        '商品数量': 'Quantité',
        '订单备注': 'Notes',
        '管理员备注': 'Notes admin',
        '下单时间': 'Date de commande',
        '查看详情': 'Voir détails',
        '更新状态': 'Mettre à jour',
        '删除订单': 'Supprimer la commande',
        '导出订单': 'Exporter les commandes',

        // ---------- Vendor ----------
        '卖家列表': 'Liste des vendeurs',
        '添加卖家': 'Ajouter un vendeur',
        '编辑卖家': 'Modifier le vendeur',
        '删除卖家': 'Supprimer le vendeur',
        '店铺名称': 'Nom du magasin',
        '联系人': 'Contact',
        '佣金率': 'Commission',
        '图书数': 'Livres',
        '待审核': 'En attente',
        '已批准': 'Approuvé',
        '已拒绝': 'Refusé',
        '已暂停': 'Suspendu',
        '更改状态': 'Changer le statut',
        '批准': 'Approuver',
        '拒绝': 'Refuser',
        '暂停': 'Suspendre',
        '管理平台卖家和店铺': 'Gérer les vendeurs et boutiques',
        '位卖家': ' vendeurs',
        '共': 'Total ',
        '密码': 'Mot de passe',

        // ---------- User Management ----------
        '用户列表': 'Liste des utilisateurs',
        '添加用户': 'Ajouter un utilisateur',
        '编辑用户': 'Modifier l\'utilisateur',
        '删除用户': 'Supprimer l\'utilisateur',
        '头像': 'Avatar',
        '活跃': 'Actif',
        '已禁用': 'Désactivé',
        '启用': 'Activer',
        '禁用': 'Désactiver',
        '管理平台注册用户': 'Gérer les utilisateurs',
        '位用户': ' utilisateurs',
        '搜索姓名、邮箱或电话...': 'Rechercher nom, e-mail ou tél...',

        // ---------- Notification ----------
        '通知管理': 'Notifications',
        '通知列表': 'Liste des notifications',
        '通知中心': 'Notifications',
        '全部已读': 'Tout lu',
        '暂无通知': 'Aucune notification',
        '查看全部通知': 'Voir tout',
        '清空已读': 'Effacer les lus',
        '清空全部通知': 'Tout effacer',
        '未读通知': 'Non lu',
        '已读通知': 'Lu',
        '总通知数': 'Total',
        '通知类型': 'Types',
        '未读': 'Non lu',
        '已读': 'Lu',
        '标为已读': 'Marquer lu',
        '前往': 'Aller à',
        '查看': 'Voir',
        '前往相关页面': 'Aller à la page',
        '条未读': ' non lu(s)',
        '条通知': ' notifications',
        '新订单': 'Nouvelle commande',
        '新用户注册': 'Nouvel utilisateur',
        '待下单提醒': 'Panier abandonné',
        '未完成注册': 'Inscription incomplète',
        '订单已付款': 'Commande payée',
        '新卖家注册': 'Nouveau vendeur',
        '库存不足': 'Stock bas',
        '查看和管理所有系统通知': 'Voir et gérer toutes les notifications',
        '系统暂时没有通知，有新的事件时会自动显示': 'Aucune notification. Les nouveaux événements apparaîtront ici.',
        '全部清除': 'Tout effacer',
        '清除已读': 'Effacer les lus',

        // ---------- Blog ----------
        '博客列表': 'Liste des articles',
        '添加文章': 'Ajouter un article',
        '编辑文章': 'Modifier l\'article',
        '删除文章': 'Supprimer l\'article',
        '标题': 'Titre',
        '分类': 'Catégorie',
        '发布日期': 'Publié le',
        '浏览次数': 'Vues',
        '已发布': 'Publié',
        '草稿': 'Brouillon',
        '分类管理': 'Catégories',
        '管理博客文章和分类': 'Gérer les articles et catégories',
        '篇文章': ' articles',

        // ---------- Email / Messages ----------
        '消息中心': 'Messages',
        '邮件': 'E-mail',
        '收件箱': 'Boîte de réception',
        '发件箱': 'Envoyés',
        '草稿箱': 'Brouillons',
        '垃圾箱': 'Corbeille',
        '写邮件': 'Rédiger',
        '回复': 'Répondre',
        '转发': 'Transférer',
        '发件人': 'De',
        '收件人': 'À',
        '主题': 'Sujet',
        '附件': 'Pièce jointe',
        '标记已读': 'Marquer lu',
        '标记未读': 'Marquer non lu',

        // ---------- Breadcrumbs ----------
        '图书': 'Livres',
        '作家': 'Auteurs',

        // ---------- Header cards ----------
        '欢迎回来': 'Bienvenue',
        '管理员': 'Admin',
        '今天是': 'Aujourd\'hui :',
        '搜索图书名称...': 'Rechercher des livres...',
        '搜索作者姓名...': 'Rechercher des auteurs...',
        '搜索出版社...': 'Rechercher des éditeurs...',
        '搜索订单号或客户名...': 'Rechercher commande ou client...',
        '搜索店铺名、联系人或邮箱...': 'Rechercher boutique, contact ou e-mail...',
        '搜索文章标题...': 'Rechercher un titre...',

        // ---------- Confirmations ----------
        '确定要删除吗？此操作不可撤销。': 'Confirmer ? Cette action est irréversible.',
        '此操作不可撤销': 'Action irréversible',
        '状态已更新': 'Statut mis à jour',
        '已删除': 'Supprimé',
        '已更新': 'Mis à jour',
        '已添加': 'Ajouté',

        // ---------- Form labels ----------
        '图书名称': 'Nom du livre',
        '图书描述': 'Description',
        '图书价格': 'Prix',
        '图书库存': 'Stock',
        '选择出版社': 'Choisir un éditeur',
        '选择作者': 'Choisir un auteur',
        '上传封面': 'Télécharger la couverture',
        '联系人姓名': 'Nom du contact',
        '公司名称': 'Nom de l\'entreprise',
        '佣金率 (%)': 'Commission (%)',

        // ---------- AI Chatbot Config ----------
        'AI 聊天配置 - DUNO 360': 'Config. IA - DUNO 360',
        'AI 聊天配置': 'Config. IA Chat',
        'AI 聊天机器人配置': 'Configuration du chatbot IA',
        'AI 聊天机器人': 'Chatbot IA',
        'AI 聊天': 'Chat IA',
        '管理 AI 对话服务、API 密钥和前端小部件': 'Gérer le service IA, clés API et widgets',
        '配置 AI 助手 · 管理 API 密钥 · 监控对话 · 实时平台数据': 'Configurer IA · Gérer API · Monitorer chats · Données temps réel',
        '返回仪表盘': 'Retour au tableau de bord',
        '总对话': 'Conversations',
        '总对话数': 'Total conversations',
        '总消息': 'Total messages',
        '总消息数': 'Total messages',
        '当前供应商': 'Fournisseur actuel',
        '小部件状态': 'Statut du widget',
        '运行中': 'En cours',
        '活跃会话': 'Sessions actives',
        '消耗 Tokens': 'Tokens utilisés',
        '配置': 'Configuration',
        '测试 API': 'Tester API',
        '对话记录': 'Historique',
        '对话会话记录': 'Historique des sessions',
        '平台上下文': 'Contexte plateforme',
        '免费 API 指南': 'Guide API gratuit',
        'AI 供应商': 'Fournisseur IA',
        'AI 供应商选择': 'Choix du fournisseur IA',
        'API 凭证 & 模型': 'Identifiants API et modèle',
        'API 凭证': 'Identifiants API',
        '模型 ID': 'ID du modèle',
        '模型名称': 'Nom du modèle',
        'API 密钥': 'Clé API',
        '输入 API 密钥（以 *** 开头表示保持不变）': 'Entrer la clé API (*** = inchangé)',
        '含 * 的值不会被覆盖': 'Les valeurs avec * ne seront pas écrasées',
        '留空使用默认模型': 'Laisser vide pour le modèle par défaut',
        '留空用默认': 'Vide pour défaut',
        '自定义 API 端点': 'Endpoint API personnalisé',
        '快速填充：': 'Remplissage rapide :',
        '小部件外观': 'Apparence du widget',
        '小部件设置': 'Paramètres du widget',
        '副标题': 'Sous-titre',
        '欢迎语': 'Message d\'accueil',
        '在公开页面显示': 'Afficher sur les pages publiques',
        '公开页面显示': 'Pages publiques',
        '访客和注册用户可以使用聊天功能': 'Visiteurs et utilisateurs peuvent chatter',
        '在管理后台显示': 'Afficher dans l\'admin',
        '管理页面显示': 'Pages admin',
        '管理员可以在后台使用 AI 助手': 'Les admins peuvent utiliser l\'IA',
        '启用聊天机器人': 'Activer le chatbot',
        '关闭后聊天窗口将不再显示': 'Le chat sera masqué si désactivé',
        'AI 参数调优': 'Réglage des paramètres IA',
        'AI 参数': 'Paramètres IA',
        '系统提示词': 'Prompt système',
        '留空则使用默认提示词（含平台数据自动注入）': 'Vide pour le prompt par défaut (injection auto)',
        '平台实时数据（图书列表、作者、出版社、销量统计）会自动注入，无需手动填写。': 'Les données de la plateforme sont injectées automatiquement.',
        '最大 Token 数': 'Tokens max',
        '温度（随机性）': 'Température (aléatoire)',
        '温度 (随机性)': 'Température (aléatoire)',
        '精准': 'Précis',
        '精确 0': 'Précis 0',
        '创意': 'Créatif',
        '创造 2': 'Créatif 2',
        '每会话最大消息数': 'Messages max par session',
        '建议': 'Recommandé',
        '先测试': 'Tester d\'abord',
        '保存配置': 'Enregistrer la config.',
        '保存中...': 'Enregistrement...',
        '配置已保存': 'Configuration enregistrée',
        '保存失败': 'Échec de l\'enregistrement',
        '实时 API 测试': 'Test API en temps réel',
        '使用已保存配置 + 平台实时数据测试': 'Tester avec la config. + données temps réel',
        '在更改配置后，使用此工具验证 API 密钥和模型是否正常工作。': 'Après modification, vérifiez votre clé API et votre modèle.',
        '测试消息': 'Message de test',
        '输入测试消息...': 'Entrer un message de test...',
        '快速测试：': 'Tests rapides :',
        '介绍平台热销图书': 'Livres populaires',
        '有哪些科幻类图书？': 'Livres de science-fiction ?',
        '如何查看我的订单？': 'Comment voir ma commande ?',
        '推荐一本适合初学者的书': 'Recommander un livre débutant',
        '平台共有多少本书？': 'Combien de livres sur la plateforme ?',
        '你好！请简单介绍一下你自己。': 'Bonjour ! Présentez-vous brièvement.',
        '你好！请介绍一下这个图书平台上有哪些热门图书。': 'Bonjour ! Quels sont les livres populaires ?',
        '运行测试': 'Lancer le test',
        '测试中...': 'Test en cours...',
        'API 测试成功': 'Test API réussi',
        '最近对话': 'Conversations récentes',
        '确认清除所有对话记录？此操作不可撤销。': 'Effacer tout ? Action irréversible.',
        '确认清除所有对话记录？': 'Confirmer l\'effacement ?',
        '会话标识': 'ID de session',
        '用户': 'Utilisateur',
        '消息数': 'Messages',
        '开始时间': 'Début',
        '最后活跃': 'Dernière activité',
        '匿名': 'Anonyme',
        '已结束': 'Terminé',
        '暂无对话记录': 'Aucun historique',
        '清除全部': 'Tout effacer',
        '清除失败': 'Échec de l\'effacement',
        '实时平台上下文': 'Contexte plateforme en temps réel',
        '每次请求自动刷新': 'Actualisé à chaque requête',
        '以下数据会在每次 AI 对话时实时注入到系统提示词中，让 AI 拥有平台的最新完整知识。数据库变化后下一次对话即生效，无需任何手动操作。': 'Les données sont injectées dans le prompt IA en temps réel.',
        '图书（实时）': 'Livres (temps réel)',
        '作者（实时）': 'Auteurs (temps réel)',
        '出版社（实时）': 'Éditeurs (temps réel)',
        '上下文预览（发送给 AI 的真实内容）': 'Aperçu du contexte (contenu envoyé à l\'IA)',
        '刷新预览': 'Actualiser l\'aperçu',
        '点击"刷新预览"查看将发送给 AI 的实时平台数据...': 'Cliquez sur "Actualiser" pour voir les données...',
        '免费 AI API 平台推荐': 'Plateformes API IA gratuites',
        '以下平台提供免费或丰厚的免费额度。推荐': 'Ces plateformes offrent des niveaux gratuits. Recommandé :',
        '（一个 Key，20+ 免费模型）或': '(une clé, 20+ modèles gratuits) ou',
        '（Gemini 免费额度极大）。': '(forfait Gemini gén.).',
        '免费模型': 'Modèles gratuits',
        '说明': 'Description',
        '获取 API Key': 'Obtenir la clé API',
        '获取密钥': 'Obtenir la clé',
        '当前使用': 'En cours',
        '免费模型（点击即可应用）': 'Modèles gratuits (cliquer pour appliquer)',
        '点击任意模型卡片，自动填充到配置页面并切换至 OpenRouter 供应商。': 'Cliquez pour remplir et passer à OpenRouter.',
        '已应用模型 ID，记得保存配置': 'ID modèle appliqué, pensez à enregistrer',
        '已填充模型 ID': 'ID modèle rempli',
        '请输入测试消息': 'Entrez un message de test',
        '实时数据': 'Données temps réel',
        '本书': ' livres',
        '位作者': ' auteurs',

        // ---------- Add/Edit Book Form ----------
        '添加图书 - DUNO 360': 'Ajouter un livre - DUNO 360',
        '添加新图书': 'Ajouter un nouveau livre',
        '为系统添加新的图书信息': 'Ajouter un nouveau livre au système',
        '快速导航': 'Navigation rapide',
        '退出系统': 'Déconnexion',
        '请输入图书名称': 'Entrer le nom du livre',
        '请输入图书的详细描述信息...': 'Entrer la description du livre...',
        '详细的图书描述有助于读者了解图书内容': 'La description aide les lecteurs',
        '价格 (元)': 'Prix (¥)',
        '库存数量': 'Quantité en stock',
        '销售数量': 'Quantité vendue',
        '上传封面图片': 'Télécharger la couverture',
        '支持 JPG, PNG, GIF 格式': 'Formats JPG, PNG, GIF',
        '最大 5MB': 'Max 5 Mo',
        '电子书下载': 'Téléchargement e-book',
        '提示：': 'Note :',
        '您可以上传电子书文件（PDF、EPUB等）或提供外部下载链接（如Google Drive、OneDrive等）': 'Télécharger des fichiers (PDF, EPUB) ou fournir des liens externes',
        '上传电子书文件': 'Télécharger un e-book',
        '支持格式: PDF, EPUB, MOBI, AZW, TXT, DOC, DOCX': 'Formats : PDF, EPUB, MOBI, AZW, TXT, DOC, DOCX',
        '外部下载链接': 'Lien de téléchargement',
        '或提供Google Drive、OneDrive等外部链接': 'Ou fournir un lien Google Drive, OneDrive',
        '如不上传，系统将自动生成精美封面': 'Si non téléchargée, le système génèrera une couverture automatiquement',
        '您可以上传电子书文件或提供外部下载链接': 'Vous pouvez télécharger un fichier e-book ou fournir un lien externe',
        '已上传文件': 'Fichier téléchargé',
        '当前封面（上传新图片可替换）': 'Couverture actuelle (télécharger une nouvelle image pour remplacer)',
        '新建': 'Nouveau',
        '新建作者': 'Nouvel auteur',
        '新建出版社': 'Nouvel éditeur',
        '请输入作者名称': 'Entrer le nom de l\'auteur',
        '请输入出版社名称': 'Entrer le nom de l\'éditeur',
        '请输入出版社地址': 'Entrer l\'adresse de l\'éditeur',
        '创建': 'Créer',
        '按住 Ctrl/Cmd 可多选作者': 'Ctrl/Cmd pour sélection multiple',
        '请选择出版社': 'Choisir un éditeur',

        // ---------- Vendor Dashboard ----------
        '业绩概览': 'Aperçu des performances',
        '平均售价': 'Prix moyen',
        '上架率': 'Taux d\'activité',
        '畅销图书': 'Meilleures ventes',
        '已售': 'Vendu',
        '账户信息': 'Infos du compte',
        '入驻时间': 'Inscrit depuis',
        '上架中': 'Actif',
        '已下架': 'Retiré',
        '缺货': 'Rupture de stock',
        '快捷操作': 'Actions rapides',
        '上架新书': 'Publier un livre',
        '管理员视图': 'Vue admin',
        '我的图书': 'Mes livres',
        '暂无上架图书': 'Aucun livre publié',
        '上架第一本书': 'Publier votre premier livre',
        '下架': 'Retirer',
        '上架': 'Publier',
        'DUNO 360': 'DUNO 360',

        // ---------- Email Account Management ----------
        '邮箱账户管理 - DUNO 360': 'Comptes e-mail - DUNO 360',
        '邮箱账户管理': 'Gestion des comptes e-mail',
        '返回邮箱': 'Retour aux e-mails',
        '网站': 'Site web',
        '默认': 'Par défaut',
        'IMAP 服务器': 'Serveur IMAP',
        'IMAP 端口': 'Port IMAP',
        'SMTP 服务器': 'Serveur SMTP',
        'SMTP 端口': 'Port SMTP',
        '最后同步': 'Dernière sync.',
        '测试': 'Test',
        '暂无邮箱账户，请添加一个': 'Aucun compte, veuillez en ajouter un',
        '添加账户': 'Ajouter un compte',
        '添加新邮箱账户': 'Nouveau compte e-mail',
        '名称': 'Nom',
        '邮箱地址': 'Adresse e-mail',
        '用户名': 'Nom d\'utilisateur',
        '通常是邮箱地址': 'Généralement l\'adresse e-mail',
        '密码 / 应用密码': 'Mot de passe / Clé d\'application',
        '确定删除账户': 'Confirmer la suppression du compte',
        '该账户的所有邮件也将被删除。': 'Tous les e-mails de ce compte seront supprimés.',

        // ---------- Order Detail ----------
        '联系电话': 'Téléphone',
        '国家': 'Pays',
        '微信/电话': 'WeChat / Tél.',
        '客户备注': 'Notes du client',
        '最后更新': 'Dernière mise à jour',
        '支付方式': 'Mode de paiement',
        '订单状态': 'Statut de la commande',
        '支付状态': 'Statut du paiement',
        '电子邮箱': 'E-mail',
        '客户姓名': 'Nom du client',

        // ---------- Form Pages (Add/Edit) ----------
        '首页': 'Accueil',
        '基本信息': 'Informations de base',
        '返回列表': 'Retour à la liste',
        '文章标题': 'Titre de l\'article',
        '文章内容': 'Contenu de l\'article',
        '摘要': 'Résumé',
        '发布设置': 'Paramètres de publication',
        '无分类': 'Sans catégorie',
        '作者名称': 'Nom de l\'auteur',
        '设为精选文章': 'Définir comme article vedette',
        '封面图片': 'Image de couverture',
        '保存文章': 'Enregistrer l\'article',
        '保存出版社': 'Enregistrer l\'éditeur',
        '保存作者': 'Enregistrer l\'auteur',
        '出版社信息': 'Infos de l\'éditeur',
        '作者信息': 'Infos de l\'auteur',
        '关联图书': 'Livres associés',
        '搜索图书名称...': 'Rechercher des livres...',
        '图书封面': 'Couverture du livre',
        '点击上传图片': 'Cliquer pour télécharger',
        '新建文章': 'Nouvel article',
        '保存图书': 'Enregistrer le livre',
        '支持 JPG、PNG、GIF 格式': 'Formats JPG, PNG, GIF',
        '网络错误': 'Erreur réseau',

        // ---------- Login Page ----------
        '管理员登录': 'Connexion admin',
        '请输入账号': 'Entrer le compte',
        '请输入密码': 'Entrer le mot de passe',
        '登录': 'Connexion',
        '忘记登录信息？': 'Mot de passe oublié ?',
        '访问公共图书目录': 'Accéder au catalogue public',
        '现代化DUNO 360': 'DUNO 360',
        '智能图书管理': 'Gestion intelligente des livres',
        '作者信息管理': 'Gestion des auteurs',
        '销售数据统计': 'Statistiques de ventes',
        '安全可靠': 'Sûr et fiable',

        // ---------- Misc ----------
        '暂无': 'N/A',
        '无': 'N/A',
        '是': 'Oui',
        '否': 'Non',
        '或': 'ou',
        '和': 'et',
        '个': '',
        '本': '',
        '位': '',
        '篇': '',
        '条': '',
        '项': '',

        // ---------- Chart labels ----------
        '销售额 (¥)': 'Revenus (¥)',
        '订单数': 'Commandes',
        '图书数量': 'Nombre de livres',

        // ---------- Vendor Center (卖家中心) ----------
        '卖家中心': 'Centre vendeur',
        '我的商品': 'Mes produits',
        '我的课程': 'Mes cours',
        '查看市场': 'Voir le marché',
        '商品': 'Produit',
        '添加商品': 'Ajouter un produit',
        '搜索商品名称或SKU...': 'Rechercher produit ou SKU...',
        '全部': 'Tout',
        '上架': 'Actif',
        '下架': 'Inactif',
        '切换状态': 'Basculer le statut',
        '暂无商品': 'Aucun produit',
        '添加第一个商品': 'Ajouter votre premier produit',
        '确定删除此商品?': 'Supprimer ce produit ?',
        '确定删除？': 'Confirmer la suppression ?',

        // ---------- Course Management ----------
        '课程管理': 'Cours',
        '添加课程': 'Ajouter un cours',
        '搜索课程...': 'Rechercher des cours...',
        '门课程': ' cours',
        '课程': 'Cours',
        '讲师': 'Instructeur',
        '级别': 'Niveau',
        '注册人数': 'Inscriptions',
        '课时': 'Leçons',
        '发布': 'Publié',
        '推荐': 'En vedette',
        '管理内容': 'Gérer le contenu',
        '暂无课程': 'Aucun cours',

        // ---------- Course Content Management ----------
        '课程内容管理': 'Contenu du cours',
        '编辑课程': 'Modifier le cours',
        '个章节': ' chapitres',
        '添加章节': 'Ajouter un chapitre',
        '编辑章节': 'Modifier le chapitre',
        '章节标题': 'Titre du chapitre',
        '排序': 'Ordre',
        '暂无章节': 'Aucun chapitre',
        '添加课时': 'Ajouter une leçon',
        '编辑课时': 'Modifier la leçon',
        '课时标题': 'Titre de la leçon',
        '暂无课时': 'Aucune leçon',
        '时长(分钟)': 'Durée (min)',
        '课时描述': 'Description de la leçon',
        '视频内容': 'Contenu vidéo',
        '上传视频文件': 'Télécharger la vidéo',
        '或输入视频链接': 'Ou entrer l\'URL de la vidéo',
        '课件': 'Support de cours',
        '免费试看': 'Aperçu gratuit',
        '免费': 'Gratuit',
        '视频': 'Vidéo',
        '分钟': 'min',
        '保存中...': 'Enregistrement...',
        '请输入章节标题': 'Entrer le titre du chapitre',
        '请输入课时标题': 'Entrer le titre de la leçon',
        '找不到课时数据': 'Données de leçon introuvables',
        '删除当前视频': 'Supprimer la vidéo',
        '删除当前PDF': 'Supprimer le PDF',

        // ---------- Vendor Admin (Marketplace Overview) ----------
        '卖家总数': 'Total vendeurs',
        '卖家商品总数': 'Produits vendeurs',
        '卖家课程总数': 'Cours vendeurs',
        '总销量': 'Ventes totales',
        '最畅销商品 (全平台)': 'Top produits (plateforme)',
        '销量最高卖家': 'Top vendeurs par ventes',
        '暂无销售数据': 'Aucune donnée de ventes',
        '件': 'unité(s)',
        '市场内容': 'Contenu du marché',
        '查看内容': 'Voir le contenu',
        '违规删除': 'Supprimer pour violation',
        '该卖家暂无商品': 'Aucun produit pour ce vendeur',
        '该卖家暂无课程': 'Aucun cours pour ce vendeur',
        '的市场内容': ' — contenu marché',
        '未分类': 'Non classé',

        // ---------- Marketplace Admin ----------
        '市场管理': 'Marché',
        '商品管理': 'Produits',
        '超市管理': 'Supermarché',
        '分类管理': 'Catégories',
        '属性管理': 'Attributs',
        '订单管理': 'Commandes',
        '市场概览': 'Aperçu du marché',
        '商品总数': 'Total produits',
        '课程总数': 'Total cours',
        '本月收入': 'Revenus du mois',

        // ---------- Marketplace Dashboard ----------
        '市场管理仪表板': 'Tableau de bord du marché',
        '概览 · 商品 · 课程 · 超市': 'Aperçu · Produits · Cours · Supermarché',
        '超市商品': 'Articles supermarché',
        '快捷操作': 'Actions rapides',
        '添加超市商品': 'Ajouter un article supermarché',
        '添加分类': 'Ajouter une catégorie',
        '最近订单': 'Commandes récentes',
        '返回主面板': 'Retour à l\'admin',

        // ---------- Marketplace Product Form ----------
        '编辑商品': 'Modifier le produit',
        '商品名称': 'Nom du produit',
        '商品描述': 'Description du produit',
        '原价': 'Prix original',
        '品牌': 'Marque',
        '状况': 'État',
        '全新': 'Neuf',
        '几乎全新': 'Comme neuf',
        '二手': 'Occasion',
        '翻新': 'Reconditionné',
        '重量 (kg)': 'Poids (kg)',
        '主图': 'Image principale',
        '图片2': 'Image 2',
        '图片3': 'Image 3',
        '推荐商品': 'Produit en vedette',
        '商品属性与可选项': 'Attributs et options du produit',
        '商品属性与可选规格': 'Attributs et spécifications',
        '添加属性': 'Ajouter un attribut',
        '属性名称': 'Nom de l\'attribut',
        '属性值': 'Valeur de l\'attribut',
        '快速添加：': 'Ajout rapide :',
        '颜色': 'Couleur',
        '尺寸': 'Taille',
        '材质': 'Matériau',
        '重量': 'Poids',
        '长度': 'Longueur',
        '宽度': 'Largeur',
        '高度': 'Hauteur',
        '型号': 'Modèle',
        '产地': 'Origine',
        '保质期': 'Date de péremption',
        '保存修改': 'Enregistrer',
        '选择分类': 'Choisir la catégorie',
        '-- 选择分类 --': '-- Choisir la catégorie --',
        '搜索商品...': 'Rechercher des produits...',
        '件商品': ' produits',

        // ---------- Marketplace Course Form ----------
        '课程标题': 'Titre du cours',
        '课程描述': 'Description du cours',
        '时长(小时)': 'Durée (h)',
        '课时数': 'Nombre de leçons',
        '难度级别': 'Niveau de difficulté',
        '全部级别': 'Tous niveaux',
        '入门': 'Débutant',
        '中级': 'Intermédiaire',
        '高级': 'Avancé',
        '教学语言': 'Langue d\'enseignement',
        '预览链接': 'Lien de prévisualisation',
        '推荐课程': 'Cours en vedette',

        // ---------- Marketplace Orders ----------
        '市场订单管理': 'Gestion des commandes',
        '搜索订单号、客户名、邮箱、电话...': 'Rechercher commande, client, e-mail, tél...',
        '全部支付状态': 'Tous les statuts de paiement',
        '已付款': 'Payé',
        '已送达': 'Livré',
        '笔订单': ' commandes',
        '确认删除订单': 'Confirmer la suppression',
        '此操作不可逆！': 'Cette action est irréversible !',
        '确认删除': 'Confirmer la suppression',
        '删除中...': 'Suppression...',
        '删除时发生错误': 'Erreur lors de la suppression',
        '已完成或已送达的订单不能删除！': 'Les commandes terminées ou livrées ne peuvent pas être supprimées !',
        '警告：': 'Attention :',

        // ---------- Marketplace Order Detail ----------
        '订单 #': 'Commande #',
        '创建时间：': 'Créée le : ',
        '订单总金额': 'Montant total',
        '客户信息': 'Infos client',
        '未知': 'Inconnu',
        '未提供': 'Non fourni',
        '备注': 'Notes',
        '订单时间线': 'Chronologie de la commande',
        '订单创建': 'Commande créée',
        '订单确认': 'Commande confirmée',
        '订单发货': 'Commande expédiée',
        '订单完成': 'Commande terminée',
        '操作选项': 'Actions',
        '更新订单状态': 'Mettre à jour le statut',
        '更新支付状态': 'Mettre à jour le paiement',
        '打印订单': 'Imprimer la commande',
        '订单商品': 'Articles de la commande',
        '图片': 'Image',
        '商品信息': 'Infos produit',
        '类型': 'Type',
        '单价': 'Prix unitaire',
        '数量': 'Qté',
        '小计': 'Sous-total',
        '无商品': 'Aucun article',
        '商品总数：': 'Total articles : ',
        '订单总计': 'Total de la commande',
        '更新订单状态失败：': 'Mise à jour échouée : ',
        '更新订单状态时发生错误': 'Erreur de mise à jour du statut',
        '更新支付状态失败：': 'Mise à jour échouée : ',
        '更新支付状态时发生错误': 'Erreur de mise à jour du paiement',
        '您确定要删除以下订单吗？': 'Voulez-vous vraiment supprimer cette commande ?',
        '订单号：': 'N° de commande : ',
        '客户：': 'Client : ',
        '订单状态：': 'Statut : ',
        '订单金额：': 'Montant : ',
        '删除后，所有相关的订单项目和历史记录都将被永久删除。': 'Tous les articles et l\'historique seront définitivement supprimés.',
        '交易ID': 'ID de transaction',
        '输入支付交易ID...': 'Entrer l\'ID de transaction...',
        '添加备注信息...': 'Ajouter une note...',

        // ---------- Marketplace Categories ----------
        '分类名称': 'Nom de la catégorie',
        '版块': 'Section',
        '上级分类': 'Catégorie parente',
        '暂无分类': 'Aucune catégorie',
        '确定删除该分类？': 'Supprimer cette catégorie ?',
        '编辑分类': 'Modifier la catégorie',
        '所属版块': 'Section',
        '-- 无 (顶级分类) --': '-- Aucune (niveau supérieur) --',
        '分类图片': 'Image de catégorie',
        '超市': 'Supermarché',

        // ---------- Marketplace Supermarket ----------
        '暂无超市商品': 'Aucun article supermarché',
        '编辑超市商品': 'Modifier l\'article supermarché',
        '单位': 'Unité',
        '个': 'Pièce',
        '公斤': 'kg',
        '克': 'g',
        '升': 'Litre',
        '毫升': 'ml',
        '包': 'Paquet',
        '盒': 'Boîte',
        '瓶': 'Bouteille',
        '袋': 'Sachet',
        '有机食品': 'Bio',
        '前台规格逻辑': 'Logique des spécifications',
        '单值属性显示为商品规格，多值属性显示为用户可选规格。请保持命名一致，避免同一属性出现多种拼写。': 'Valeur unique = spécification ; valeurs multiples = option sélectionnable. Gardez un nom cohérent.',
        '用这里定义前台可选配置与技术规格，例如颜色、尺寸、材质、容量、版本。': 'Définir les options et spéc. techniques : couleur, taille, matériau, capacité, version.',
        '用这里定义用户可选规格与商品说明，例如包装、净含量、保质期、成分、储存方式。': 'Définir les options : emballage, poids net, péremption, ingrédients, stockage.',
        '成分': 'Ingrédients',
        '储存方式': 'Conservation',
        '规格': 'Spécification',
        '生产日期': 'Date de production',
        '营养成分': 'Valeurs nutritionnelles',
        '过敏原': 'Allergènes',

        // ---------- Vendor Dashboard ----------
        '卖家仪表板': 'Tableau de bord vendeur',
        '数据概览': 'Aperçu des données',
        '管理商品': 'Gérer les produits',
        '管理课程': 'Gérer les cours',
        '近7天收入趋势': 'Tendance des revenus sur 7 jours',
        '商品分类分布': 'Répartition par catégorie',
        '收入构成': 'Composition des revenus',
        '商品收入': 'Revenus produits',
        '课程收入': 'Revenus cours',
        '上架商品': 'Produits actifs',
        '下架商品': 'Produits inactifs',
        '发布课程': 'Cours publiés',
        '课程注册': 'Inscriptions aux cours',
        '热销商品 TOP 5': 'Top 5 des produits',
        '暂无销量数据': 'Aucune donnée de ventes',

        // ---------- Vendor Product Form ----------
        '英文名称': 'Nom anglais',
        '商品状况': 'État du produit',
        '价格与库存': 'Prix et stock',
        '销售价格': 'Prix de vente',
        '商品图片': 'Images du produit',
        '商品属性': 'Attributs du produit',
        '立即上架': 'Publier maintenant',
        '填写商品信息': 'Remplir les infos produit',

        // ---------- Vendor Course Form ----------
        '英文标题': 'Titre anglais',
        '讲师名称': 'Nom de l\'instructeur',
        '价格信息': 'Tarification',
        '课程价格': 'Prix du cours',
        '语言': 'Langue',
        '课程详情': 'Détails du cours',
        '课程时长 (小时)': 'Durée (heures)',
        '课程节数': 'Nombre de leçons',
        '预览视频URL': 'URL de la vidéo de prévisualisation',
        '课程封面': 'Couverture du cours',
        '立即发布': 'Publier maintenant',
        '填写课程信息': 'Remplir les infos du cours',
        '推荐尺寸: 800×450px, 最大5MB': 'Recommandé : 800×450px, max 5 Mo',

        // ---------- Marketplace misc ----------
        '当前: ': 'Actuel : ',
        '支持 MP4, WebM, OGG 等格式，最大 500MB': 'MP4, WebM, OGG etc., max 500 Mo',
        '点击上方"添加章节"开始创建课程内容': 'Cliquez sur « Ajouter un chapitre » pour commencer',

        // ---------- Vendor list JS strings (toasts, modals, confirms) ----------
        '暂无卖家': 'Aucun vendeur',
        '点击"添加卖家"开始管理': 'Cliquez sur « Ajouter un vendeur » pour commencer',
        '确定要将该卖家状态更改为"': 'Changer le statut du vendeur en « ',
        '"吗？': '» ?',
        '状态已更新': 'Statut mis à jour',
        '确定要删除卖家 "': 'Supprimer le vendeur « ',
        '" 吗？此操作不可撤销。': '» ? Cette action est irréversible.',
        '卖家已删除': 'Vendeur supprimé',
        '删除失败': 'Échec de la suppression',
        '违规删除': 'Suppression pour infraction',
        '确定要删除': 'Voulez-vous supprimer ',
        '" 吗？该操作将从平台中移除此内容。': '» ? Ce contenu sera retiré de la plateforme.',
        '已删除': 'Supprimé',
        '卖家已更新': 'Vendeur mis à jour',
        '卖家已添加': 'Vendeur ajouté',
        '加载失败': 'Échec du chargement',
        '查看内容': 'Voir le contenu',

        // ---------- Course content JS strings ----------
        '确定删除章节 "': 'Supprimer le chapitre « ',
        '" 及其所有课时？': '» et toutes ses leçons ?',
        '操作失败': 'Opération échouée',
        '确定删除课时 "': 'Supprimer la leçon « ',
        '" ？': '» ?',
        '例如: 第一章 基础入门': 'Ex. : Chapitre 1 Introduction',
        'YouTube, Bilibili 等嵌入链接': 'Liens intégrés YouTube, Bilibili',

        // ---------- Vendor product page JS strings ----------
        '切换状态': 'Changer le statut',
        '状态切换失败': 'Échec du changement de statut',
        '状态切换时发生错误': 'Erreur lors du changement de statut',

        // ---------- Product/Course form misc ----------
        '保存修改': 'Enregistrer',
        '-- 选择分类 --': '-- Choisir une catégorie --',
        '推荐商品': 'Produit recommandé',
        '推荐课程': 'Cours recommandé',

        // ---------- Vendor detail panel ----------
        '的市场内容': ' – Contenu du marché',
        '注册': 'Inscrit(s)',

        // ---------- Pagination ----------
        '上一页': 'Précédent',
        '下一页': 'Suivant',

        // ---------- Marketplace title (dashboard standalone) ----------
        '市场管理 - Dashboard': 'Marché - Tableau de bord',
        'Marketplace Admin': 'Admin du marché',
    };

    // Sort keys longest-first for proper substring matching
    var sortedKeys = Object.keys(T).sort(function (a, b) { return b.length - a.length; });

    // Merge French keys too (in case some are only in F)
    var allKeys = Object.keys(T);
    Object.keys(F).forEach(function(k) { if (allKeys.indexOf(k) === -1) allKeys.push(k); });
    sortedKeys = allKeys.sort(function (a, b) { return b.length - a.length; });

    // Active dictionary based on language
    function getDict() { return lang === 'fr' ? F : T; }

    var lang = localStorage.getItem('adminLang') || 'zh';
    var originalMap = new WeakMap();
    var titleOriginal = '';

    /* ---- translate a single text node ---- */
    function translateTextNode(node) {
        var text = node.textContent;
        if (!text || !text.trim()) return;

        // Only process if text contains Chinese characters (when translating away from zh)
        if (!/[\u4e00-\u9fff]/.test(text) && lang !== 'zh') return;

        if (lang !== 'zh') {
            var D = getDict();
            if (!originalMap.has(node)) originalMap.set(node, text);
            var out = text;
            for (var i = 0; i < sortedKeys.length; i++) {
                var k = sortedKeys[i];
                if (out.indexOf(k) !== -1 && D[k]) {
                    out = out.split(k).join(D[k]);
                }
            }
            node.textContent = out;
        } else {
            var orig = originalMap.get(node);
            if (orig !== undefined) node.textContent = orig;
        }
    }

    /* ---- walk the DOM ---- */
    function translatePage() {
        // 1. Handle data-zh / data-en / data-fr elements
        document.querySelectorAll('[data-zh][data-en]').forEach(function (el) {
            if (lang === 'fr' && el.getAttribute('data-fr')) {
                el.textContent = el.getAttribute('data-fr');
            } else if (lang === 'en') {
                el.textContent = el.getAttribute('data-en');
            } else {
                el.textContent = el.getAttribute('data-zh');
            }
        });

        // 2. Handle placeholder attributes
        document.querySelectorAll('[data-ph-zh][data-ph-en]').forEach(function (el) {
            if (lang === 'fr' && el.getAttribute('data-ph-fr')) {
                el.placeholder = el.getAttribute('data-ph-fr');
            } else if (lang === 'en') {
                el.placeholder = el.getAttribute('data-ph-en');
            } else {
                el.placeholder = el.getAttribute('data-ph-zh');
            }
        });

        // 3. Walk text nodes
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
            acceptNode: function (n) {
                var p = n.parentNode;
                if (!p) return NodeFilter.FILTER_REJECT;
                var tag = p.tagName;
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'CODE' || tag === 'PRE')
                    return NodeFilter.FILTER_REJECT;
                if (tag === 'TEXTAREA') return NodeFilter.FILTER_REJECT;
                // Don't translate input values
                if (tag === 'INPUT') return NodeFilter.FILTER_REJECT;
                // Don't translate inside the lang toggle itself
                if (p.id === 'adminLangToggle' || p.closest('#adminLangToggle'))
                    return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });

        var nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        for (var i = 0; i < nodes.length; i++) translateTextNode(nodes[i]);

        // 4. Translate <title>
        if (lang !== 'zh') {
            var D = getDict();
            if (!titleOriginal) titleOriginal = document.title;
            var t = document.title;
            for (var j = 0; j < sortedKeys.length; j++) {
                if (t.indexOf(sortedKeys[j]) !== -1 && D[sortedKeys[j]]) {
                    t = t.split(sortedKeys[j]).join(D[sortedKeys[j]]);
                }
            }
            document.title = t;
        } else if (titleOriginal) {
            document.title = titleOriginal;
        }

        // 5. Translate select options (visual only; value stays the same)
        document.querySelectorAll('select option').forEach(function (opt) {
            var txt = opt.textContent.trim();
            if (lang !== 'zh') {
                var D = getDict();
                if (!opt.getAttribute('data-orig')) opt.setAttribute('data-orig', opt.textContent);
                for (var k = 0; k < sortedKeys.length; k++) {
                    if (txt.indexOf(sortedKeys[k]) !== -1 && D[sortedKeys[k]]) {
                        txt = txt.split(sortedKeys[k]).join(D[sortedKeys[k]]);
                    }
                }
                opt.textContent = txt;
            } else {
                var orig = opt.getAttribute('data-orig');
                if (orig) opt.textContent = orig;
            }
        });

        // 6. Translate placeholder attributes (inputs and textareas)
        document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(function (inp) {
            var ph = inp.placeholder;
            if (lang !== 'zh') {
                var D = getDict();
                if (!inp.getAttribute('data-ph-orig')) inp.setAttribute('data-ph-orig', ph);
                for (var k = 0; k < sortedKeys.length; k++) {
                    if (ph.indexOf(sortedKeys[k]) !== -1 && D[sortedKeys[k]]) {
                        ph = ph.split(sortedKeys[k]).join(D[sortedKeys[k]]);
                    }
                }
                inp.placeholder = ph;
            } else {
                var origPh = inp.getAttribute('data-ph-orig');
                if (origPh) inp.placeholder = origPh;
            }
        });

        // 7. Toggle body class for layout adjustments
        document.body.classList.remove('lang-en', 'lang-fr');
        if (lang !== 'zh') document.body.classList.add('lang-' + lang);
        document.documentElement.lang = lang === 'en' ? 'en' : (lang === 'fr' ? 'fr' : 'zh-Hans');
    }

    /* ---- toggle button ---- */
    function createToggle() {
        var wrap = document.createElement('div');
        wrap.id = 'adminLangToggle';
        wrap.title = 'Switch Language / 切换语言';
        wrap.style.cssText = [
            'position:fixed', 'bottom:24px', 'right:24px', 'z-index:9998',
            'background:linear-gradient(135deg,#667eea,#764ba2)', 'color:#fff',
            'border-radius:50px', 'padding:10px 18px', 'cursor:pointer',
            'box-shadow:0 6px 20px rgba(102,126,234,0.45)',
            'font-weight:700', 'font-size:0.85rem', 'user-select:none',
            'display:flex', 'align-items:center', 'gap:8px',
            'transition:transform .2s,box-shadow .2s',
            'font-family:Segoe UI,sans-serif'
        ].join(';');
        wrap.onmouseenter = function () { wrap.style.transform = 'translateY(-3px)'; wrap.style.boxShadow = '0 10px 30px rgba(102,126,234,0.55)'; };
        wrap.onmouseleave = function () { wrap.style.transform = ''; wrap.style.boxShadow = '0 6px 20px rgba(102,126,234,0.45)'; };
        wrap.onclick = function () { toggleLang(); };
        document.body.appendChild(wrap);
        updateToggle();
    }

    function updateToggle() {
        var el = document.getElementById('adminLangToggle');
        if (!el) return;
        if (lang === 'zh') {
            el.innerHTML = '<i class="fas fa-globe"></i> EN';
        } else if (lang === 'en') {
            el.innerHTML = '<i class="fas fa-globe"></i> FR';
        } else {
            el.innerHTML = '<i class="fas fa-globe"></i> 中文';
        }
    }

    function toggleLang() {
        if (lang === 'zh') { lang = 'en'; }
        else if (lang === 'en') { lang = 'fr'; }
        else { lang = 'zh'; }
        localStorage.setItem('adminLang', lang);
        // Clear cached originals when going back to Chinese
        translatePage();
        updateToggle();
    }

    /* ---- layout CSS for English/French mode ---- */
    function injectLangCSS() {
        var style = document.createElement('style');
        style.textContent = [
            '.lang-en .sidebar .nav-link, .lang-fr .sidebar .nav-link { font-size: 0.88rem; padding: 10px 16px; }',
            '.lang-en .sidebar h4, .lang-fr .sidebar h4 { font-size: 1.1rem; }',
            '.lang-en .sidebar h5, .lang-fr .sidebar h5 { font-size: 1rem; }',
            '.lang-en .kpi-label, .lang-fr .kpi-label { font-size: 0.72rem; }',
            '.lang-en .kpi-value, .lang-fr .kpi-value { font-size: 1.35rem; }',
            '.lang-en .chart-card h6, .lang-fr .chart-card h6 { font-size: 0.88rem; }',
            '.lang-en .table th, .lang-fr .table th { font-size: 0.8rem; white-space: nowrap; }',
            '.lang-en .table-header, .lang-fr .table-header { font-size: 0.88rem; }',
            '.lang-en .header-card h2, .lang-fr .header-card h2 { font-size: 1.4rem; }',
            '.lang-en .toolbar h5, .lang-fr .toolbar h5 { font-size: 0.95rem; }',
            '.lang-en .btn-modern, .lang-fr .btn-modern { font-size: 0.82rem; padding: 8px 14px; }',
            '.lang-en .table-modern thead th, .lang-fr .table-modern thead th { font-size: 0.82rem; padding: 12px 10px; white-space: nowrap; }',
            '.lang-en .table-modern tbody td, .lang-fr .table-modern tbody td { font-size: 0.85rem; padding: 12px 10px; }',
            '.lang-en .breadcrumb-modern, .lang-fr .breadcrumb-modern { font-size: 0.85rem; }',
            '.lang-en .welcome-header h3, .lang-fr .welcome-header h3 { font-size: 1.3rem; }',
            '.lang-en .notif-content .title, .lang-fr .notif-content .title { font-size: 0.82rem; }',
            '.lang-en .notif-content .msg, .lang-fr .notif-content .msg { font-size: 0.75rem; }',
            '.lang-en .notif-header h6, .lang-fr .notif-header h6 { font-size: 0.9rem; }',
            '.lang-en .stat-card .stat-label, .lang-fr .stat-card .stat-label { font-size: 0.78rem; }',
            '.lang-en .edit-modal-header h5, .lang-en .edit-modal-body .form-label, .lang-fr .edit-modal-header h5, .lang-fr .edit-modal-body .form-label { font-size: 0.9rem; }',
            '.lang-en .filter-bar .form-control, .lang-en .filter-bar .form-select, .lang-fr .filter-bar .form-control, .lang-fr .filter-bar .form-select { font-size: 0.85rem; }',
            /* Vendor sidebar adjustments */
            '.lang-en .page-header-card h4, .lang-fr .page-header-card h4 { font-size: 1.1rem; }',
            '.lang-en .content-card .table th, .lang-fr .content-card .table th { font-size: 0.78rem; white-space: nowrap; }',
            '.lang-en .content-card .table td, .lang-fr .content-card .table td { font-size: 0.85rem; }',
            '.lang-en .mp-stat-label, .lang-fr .mp-stat-label { font-size: 0.72rem; }',
            '.lang-en .ranking-card h6, .lang-fr .ranking-card h6 { font-size: 0.88rem; }',
            '.lang-en .v-metric, .lang-fr .v-metric { font-size: 0.72rem; }',
            '.lang-en .vendor-detail-tabs .nav-link, .lang-fr .vendor-detail-tabs .nav-link { font-size: 0.82rem; }',
            /* Section & lesson labels */
            '.lang-en .section-header-bar h5, .lang-fr .section-header-bar h5 { font-size: 0.92rem; }',
            '.lang-en .lesson-info .title, .lang-fr .lesson-info .title { font-size: 0.85rem; }',
            '.lang-en .lesson-info .meta, .lang-fr .lesson-info .meta { font-size: 0.75rem; }',
            '.lang-en .modal-title, .lang-fr .modal-title { font-size: 1rem; }',
            '.lang-en .form-label, .lang-fr .form-label { font-size: 0.85rem; }',
            /* French-specific: slightly smaller for longer text */
            '.lang-fr .btn-action { font-size: 0.78rem; padding: 5px 10px; }',
            '.lang-fr .badge-status { font-size: 0.75rem; }',
        ].join('\n');
        document.head.appendChild(style);
    }

    /* ---- init ---- */
    function init() {
        injectLangCSS();
        createToggle();
        if (lang !== 'zh') translatePage();

        // MutationObserver: translate dynamically inserted content (modals, toasts, AJAX)
        var observer = new MutationObserver(function (mutations) {
            if (lang === 'zh') return;
            var needsTranslate = false;
            for (var i = 0; i < mutations.length; i++) {
                var m = mutations[i];
                if (m.type === 'childList' && m.addedNodes.length > 0) {
                    for (var j = 0; j < m.addedNodes.length; j++) {
                        var node = m.addedNodes[j];
                        if (node.nodeType === Node.ELEMENT_NODE && !node.closest('#adminLangToggle')) {
                            needsTranslate = true;
                            break;
                        }
                    }
                }
                if (m.type === 'characterData') { needsTranslate = true; }
                if (needsTranslate) break;
            }
            if (needsTranslate) {
                // Debounce to avoid excessive calls
                clearTimeout(observer._timer);
                observer._timer = setTimeout(function () { translatePage(); }, 50);
            }
        });
        observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Public API
    window.adminI18n = {
        toggle: toggleLang,
        getLang: function () { return lang; },
        setLang: function (l) { lang = l; localStorage.setItem('adminLang', l); translatePage(); updateToggle(); },
        t: function (zh, en, fr) {
            if (lang === 'fr') return fr || en || zh;
            return lang === 'en' ? (en || zh) : zh;
        }
    };
})();
