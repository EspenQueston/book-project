import re

with open('locale/en/LC_MESSAGES/django.po', encoding='utf-8') as f:
    content = f.read()

strings = [
    '卖家导航', '卖家中心', '概览', '店铺前台', '订单中心', '图书管理', '上架图书',
    '商品列表', '添加商品', '课程列表', '添加课程', '超市商品', '添加超市商品',
    '客户消息', '买家评价', '浏览市场', '退出登录',
    '总览', '店铺设置', '总销量', '总收入', '数据概览', '商品', '课程',
    '图书与商城共用相近状态键时可联合筛选',
    '数据概览 · 店铺与货获 · 订单与设置',
    '卖家仪表板', '近7天收入趋势', '商品分类分布', '收入构成', '商品收入', '课程收入',
    '上架商品', '下架商品', '发布课程', '课程注册', '热销商品 TOP 5', '最近订单',
    '暂无销量数据', '暂无订单', '匿名',
]

for s in strings:
    pattern = f'msgid "{s}"\nmsgstr "'
    idx = content.find(pattern)
    if idx >= 0:
        rest = content[idx + len(pattern):]
        end = rest.index('"')
        val = rest[:end]
        print(f'  FOUND [{s}] -> "{val}"')
    else:
        print(f'  MISSING: [{s}]')
