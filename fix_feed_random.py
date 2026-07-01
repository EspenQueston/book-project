
import re
with open('marketplace/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''feed = cache.get(cache_key)
    if feed is not None:
        return feed'''
new_str = '''feed = cache.get(cache_key)
    if feed is not None:
        import random
        feed_copy = list(feed)
        random.shuffle(feed_copy)
        return feed_copy'''

content = content.replace(old_str, new_str)
with open('marketplace/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed feed randomness')

