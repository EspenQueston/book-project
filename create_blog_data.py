import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from manager.models import BlogCategory, BlogPost
from django.utils import timezone

# Create categories
cats = [
    ('reading-tips', 'Reading Tips', 'Tips and techniques for better reading', 'fas fa-lightbulb'),
    ('book-reviews', 'Book Reviews', 'Reviews of popular and classic books', 'fas fa-star'),
    ('author-interviews', 'Author Interviews', 'Conversations with authors', 'fas fa-microphone'),
    ('industry-news', 'Industry News', 'Latest news from the publishing world', 'fas fa-newspaper'),
    ('tech-reading', 'Tech & Reading', 'Technology meets literature', 'fas fa-laptop-code'),
]

for slug, name, desc, icon in cats:
    cat, created = BlogCategory.objects.get_or_create(slug=slug, defaults={'name': name, 'description': desc, 'icon': icon})
    print(f'{"Created" if created else "Exists"}: {name}')

reading_cat = BlogCategory.objects.get(slug='reading-tips')
reviews_cat = BlogCategory.objects.get(slug='book-reviews')
news_cat = BlogCategory.objects.get(slug='industry-news')
tech_cat = BlogCategory.objects.get(slug='tech-reading')

posts = [
    {
        'title': '10 Tips to Read More Books This Year',
        'slug': '10-tips-read-more-books',
        'category': reading_cat,
        'excerpt': 'Discover practical strategies to increase your reading habit and enjoy more books throughout the year.',
        'content': '<h2>Why Reading More Matters</h2><p>Reading is one of the most enriching activities we can engage in. It expands our vocabulary, enhances our critical thinking, and opens doors to new worlds and perspectives.</p><h3>1. Set a Reading Goal</h3><p>Start with a realistic goal. If you read 5 books last year, aim for 10 this year.</p><h3>2. Create a Reading List</h3><p>Keep a curated list of books you want to read. This prevents decision fatigue.</p><h3>3. Read Every Day</h3><p>Even 15-20 minutes a day adds up quickly. Make it a daily habit.</p><h3>4. Carry a Book Everywhere</h3><p>Whether physical or digital, having something to read during unexpected free moments adds hours to your monthly reading time.</p><h3>5. Join a Book Club</h3><p>Social accountability helps. A book club gives you deadlines and discussions.</p><blockquote>A reader lives a thousand lives before he dies. The man who never reads lives only one. — George R.R. Martin</blockquote><h3>6. Mix Up Genres</h3><p>Alternating between fiction, non-fiction, and different styles keeps reading fresh.</p><h3>7. Listen to Audiobooks</h3><p>Audiobooks count as reading! Perfect for commuting or exercising.</p><h3>8. Reduce Screen Time</h3><p>Replace social media scrolling with reading.</p><h3>9. Create a Cozy Reading Space</h3><p>A dedicated, comfortable spot for reading helps build the habit.</p><h3>10. Track Your Progress</h3><p>Use apps or a journal to track what you have read. Seeing progress is motivating.</p>',
        'is_featured': True,
        'views_count': 342,
    },
    {
        'title': 'The Rise of E-Books: Digital Reading in 2024',
        'slug': 'rise-of-ebooks-digital-reading-2024',
        'category': tech_cat,
        'excerpt': 'How digital reading is transforming the publishing industry and what it means for book lovers.',
        'content': '<h2>The Digital Reading Revolution</h2><p>The publishing industry has undergone a massive transformation. E-books have become a mainstream reading format embraced by millions worldwide.</p><h3>Market Growth</h3><p>The global e-book market continues to grow. Digital books account for approximately 30% of all book sales, with audiobooks adding another 15%.</p><h3>Benefits of E-Books</h3><p>Instant delivery, adjustable font sizes, built-in dictionaries, and the ability to carry an entire library in your pocket.</p><h3>The Physical Book Persists</h3><p>Despite the rise of digital, physical books have shown remarkable resilience. Print sales have actually stabilized in recent years.</p><blockquote>The future of reading is not about choosing between digital and physical — it is about having the freedom to read however, wherever, and whenever you want.</blockquote><h3>What is Next?</h3><p>AI-powered reading recommendations, interactive e-books, and enhanced audiobook experiences are just some innovations on the horizon.</p>',
        'is_featured': True,
        'views_count': 256,
    },
    {
        'title': 'Top 5 Must-Read Classic Novels',
        'slug': 'top-5-must-read-classic-novels',
        'category': reviews_cat,
        'excerpt': 'A curated list of timeless classics every book lover should read at least once.',
        'content': '<h2>Timeless Stories That Shaped Literature</h2><p>Classic novels endure because they speak to universal human experiences.</p><h3>1. Pride and Prejudice by Jane Austen</h3><p>A witty exploration of manners, morality, and marriage in Regency-era England.</p><h3>2. To Kill a Mockingbird by Harper Lee</h3><p>A powerful story about racial injustice, told through the innocent eyes of Scout Finch.</p><h3>3. 1984 by George Orwell</h3><p>A dystopian masterpiece about surveillance and totalitarianism that feels more prescient each year.</p><h3>4. One Hundred Years of Solitude by Gabriel Garcia Marquez</h3><p>A magical realist epic following seven generations of the Buendia family.</p><h3>5. The Great Gatsby by F. Scott Fitzgerald</h3><p>A dazzling portrait of the Jazz Age and the American Dream.</p><blockquote>You discover that your longings are universal longings, that you are not lonely and isolated. You belong. — F. Scott Fitzgerald</blockquote>',
        'is_featured': False,
        'views_count': 189,
    },
    {
        'title': 'How to Build a Personal Library on a Budget',
        'slug': 'build-personal-library-budget',
        'category': reading_cat,
        'excerpt': 'Smart strategies for growing your book collection without breaking the bank.',
        'content': '<h2>Your Dream Library Is Within Reach</h2><p>Building a personal library does not require a fortune. With creativity and patience, you can curate an impressive collection on any budget.</p><h3>Shop Second-Hand</h3><p>Used bookstores, charity shops, and online marketplaces are treasure troves for affordable books.</p><h3>Visit Library Sales</h3><p>Public libraries regularly hold book sales to make room for new acquisitions.</p><h3>Take Advantage of Free E-Books</h3><p>Many classic works are available for free through Project Gutenberg and Open Library.</p><h3>Trade with Friends</h3><p>Book swaps are a fantastic way to refresh your collection without spending money.</p><h3>Wait for Sales</h3><p>Online retailers frequently offer significant discounts during holidays and special events.</p>',
        'is_featured': False,
        'views_count': 127,
    },
    {
        'title': 'The Art of Book Cover Design',
        'slug': 'art-of-book-cover-design',
        'category': news_cat,
        'excerpt': 'How book covers influence reading choices and the creative process behind iconic designs.',
        'content': '<h2>Never Judge a Book by Its Cover? We All Do.</h2><p>Book covers play a crucial role in attracting readers. A well-designed cover can make the difference between a bestseller and a book that goes unnoticed.</p><h3>The Psychology of Cover Design</h3><p>Colors, typography, and imagery convey genre expectations and emotional tones.</p><h3>Evolution of Design Trends</h3><p>Recent years have seen a rise in minimalist designs, illustrated covers, and bold typographic treatments.</p><h3>The Design Process</h3><p>Professional cover designers work closely with publishers and authors to create covers that accurately represent the content while standing out in a crowded marketplace.</p><blockquote>A good cover design is the silent ambassador of your book.</blockquote>',
        'is_featured': True,
        'views_count': 203,
    },
]

for post_data in posts:
    post, created = BlogPost.objects.get_or_create(
        slug=post_data['slug'],
        defaults={
            'title': post_data['title'],
            'category': post_data['category'],
            'excerpt': post_data['excerpt'],
            'content': post_data['content'],
            'author_name': 'Admin',
            'status': 'published',
            'is_featured': post_data['is_featured'],
            'views_count': post_data['views_count'],
            'published_at': timezone.now(),
        }
    )
    print(f'{"Created" if created else "Exists"}: {post.title}')

print(f'\nTotal categories: {BlogCategory.objects.count()}')
print(f'Total posts: {BlogPost.objects.count()}')
