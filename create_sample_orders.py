"""
Django management command to create sample order data for testing
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from manager.models import Order, OrderItem, Book, Publisher


def create_sample_orders():
    """Create sample orders for testing the order management system"""
    
    # First, ensure we have some books
    if not Book.objects.exists():
        print("Creating sample books first...")
        # Create a publisher
        publisher, created = Publisher.objects.get_or_create(
            publisher_name="测试出版社",
            defaults={'publisher_address': "北京市朝阳区"}
        )
        
        # Create some books
        books_data = [
            {"name": "Python编程从入门到实践", "price": Decimal("89.00"), "inventory": 50, "sale_num": 10},
            {"name": "Django Web开发实战", "price": Decimal("75.50"), "inventory": 30, "sale_num": 5},
            {"name": "数据结构与算法分析", "price": Decimal("95.00"), "inventory": 25, "sale_num": 15},
            {"name": "机器学习实战", "price": Decimal("120.00"), "inventory": 20, "sale_num": 8},
            {"name": "深入理解计算机系统", "price": Decimal("139.00"), "inventory": 15, "sale_num": 3},
        ]
        
        for book_data in books_data:
            Book.objects.create(
                publisher=publisher,
                **book_data
            )
        print(f"Created {len(books_data)} sample books")
    
    books = list(Book.objects.all())
    
    # Sample customer data
    customers = [
        {
            "name": "张三", 
            "email": "zhangsan@example.com", 
            "phone": "13800138001",
            "address": "北京市朝阳区建国路1号",
            "city": "北京",
            "state": "北京市"
        },
        {
            "name": "李四", 
            "email": "lisi@example.com", 
            "phone": "13800138002",
            "address": "上海市浦东新区陆家嘴环路1000号",
            "city": "上海",
            "state": "上海市"
        },
        {
            "name": "王五", 
            "email": "wangwu@example.com", 
            "phone": "13800138003",
            "address": "广州市天河区珠江新城花城大道123号",
            "city": "广州",
            "state": "广东省"
        },
        {
            "name": "赵六", 
            "email": "zhaoliu@example.com", 
            "phone": "13800138004",
            "address": "深圳市南山区科技园南区深南大道9999号",
            "city": "深圳",
            "state": "广东省"
        },
        {
            "name": "钱七", 
            "email": "qianqi@example.com", 
            "phone": "13800138005",
            "address": "杭州市西湖区文三路123号",
            "city": "杭州",
            "state": "浙江省"
        },
    ]
    
    # Order statuses for variety
    order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    payment_statuses = ['pending', 'paid', 'failed', 'refunded']
    payment_methods = ['alipay', 'wechat_pay', 'credit_card', 'bank_transfer']
    
    orders_created = 0
    
    # Create orders for the last 30 days
    for i in range(20):  # Create 20 sample orders
        # Random date within last 30 days
        days_ago = random.randint(0, 30)
        created_date = datetime.now() - timedelta(days=days_ago)
        
        # Random customer
        customer = random.choice(customers)
        
        # Random order details
        order_status = random.choice(order_statuses)
        payment_status = random.choice(payment_statuses)
        payment_method = random.choice(payment_methods)
        
        # Create order
        order = Order.objects.create(
            customer_name=customer["name"],
            customer_email=customer["email"],
            customer_phone=customer["phone"],
            shipping_address=customer["address"],
            shipping_city=customer["city"],
            shipping_state=customer["state"],
            shipping_country="中国",
            shipping_postal_code=f"{100000 + random.randint(1, 99999)}",
            payment_method=payment_method,
            status=order_status,
            payment_status=payment_status,
            total_amount=Decimal("0.00"),  # Will be calculated below
            customer_notes=f"测试订单备注 {i+1}",
            admin_notes=f"管理员备注 - 订单 {i+1}"
        )
        
        # Manually set created_at to simulate historical orders
        Order.objects.filter(id=order.id).update(created_at=created_date)
        
        # Add random books to order
        num_items = random.randint(1, 4)  # 1-4 books per order
        selected_books = random.sample(books, min(num_items, len(books)))
        total_amount = Decimal("0.00")
        
        for book in selected_books:
            quantity = random.randint(1, 3)
            unit_price = book.price
            total_price = unit_price * quantity
            total_amount += total_price
            
            OrderItem.objects.create(
                order=order,
                book=book,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
        
        # Update order total
        order.total_amount = total_amount
        order.save()
        
        orders_created += 1
        
        print(f"Created order {order.order_number} for {customer['name']} - ¥{total_amount}")
    
    print(f"\nSuccessfully created {orders_created} sample orders!")
    print("You can now test the order management system at: http://127.0.0.1:8000/manager/order_list/")


if __name__ == "__main__":
    create_sample_orders()
