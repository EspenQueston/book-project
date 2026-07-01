import re
with open('marketplace/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))',
    'sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))\\n    ).annotate(\\n        total_sold=F(\\'sales_count\\') + F(\\'sold_delivered\\')'
)

content = content.replace(
    'sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))',
    'sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))\\n    ).annotate(\\n        total_sold=F(\\'enrollment_count\\') + F(\\'sold_delivered\\')'
)
# Wait, let's just use string replace directly on the exact definitions.
