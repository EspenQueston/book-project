import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from manager.models import Order, OrderItem, Book

print("=" * 60)
print("Checking orders with Django Web开发指南 book")
print("=" * 60)

# Find the Django book
django_book = Book.objects.filter(name__icontains='Django').first()
if not django_book:
    print("❌ Django book not found!")
    exit()

print(f"\n📚 Book Found: {django_book.name}")
print(f"   Book ID: {django_book.id}")
print(f"   Has Download: {django_book.has_download()}")
print(f"   Download Link: {django_book.download_link}")
print(f"   Download Type: {django_book.get_download_type()}")

# Find orders containing this book
order_items = OrderItem.objects.filter(book=django_book).select_related('order')

if not order_items.exists():
    print("\n❌ No orders found containing this book")
else:
    print(f"\n✅ Found {order_items.count()} order(s) containing this book:\n")
    for item in order_items:
        order = item.order
        print(f"📦 Order #{order.order_number}")
        print(f"   Order ID: {order.id}")
        print(f"   Customer: {order.customer_name}")
        print(f"   Status: {order.status} ({order.get_status_display()})")
        print(f"   Payment Status: {order.payment_status} ({order.get_payment_status_display()})")
        print(f"   Created: {order.created_at}")
        
        # Check if download should work
        valid_statuses = ['paid', 'confirmed', 'processing', 'shipped', 'delivered']
        can_download = order.status in valid_statuses and order.payment_status == 'completed'
        
        print(f"   ✅ Can Download: {can_download}")
        if not can_download:
            if order.status not in valid_statuses:
                print(f"      ❌ Status '{order.status}' not in valid statuses: {valid_statuses}")
            if order.payment_status != 'completed':
                print(f"      ❌ Payment status '{order.payment_status}' is not 'completed'")
        print()

# Show most recent orders
print("\n" + "=" * 60)
print("Most Recent Orders (all orders):")
print("=" * 60)
recent_orders = Order.objects.all().order_by('-created_at')[:5]
for order in recent_orders:
    print(f"\n📦 Order #{order.order_number}")
    print(f"   Status: {order.status} / Payment: {order.payment_status}")
    print(f"   Books: {', '.join([item.book.name for item in order.orderitem_set.all()])}")
