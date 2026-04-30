"""
Generate stylish book cover images for all books in the database.
Design: Green card with white border, book title in white, gradient top bar, 
BESTSELLER badge, and "精品图书" label at the bottom.
"""
import django, os, sys, textwrap, random
os.environ['DJANGO_SETTINGS_MODULE'] = 'book_Project.settings'
django.setup()

from PIL import Image, ImageDraw, ImageFont
from manager.models import Book

# ---------- Config ----------
WIDTH, HEIGHT = 400, 560
CARD_MARGIN = 28
BORDER_WIDTH = 3
BG_COLOR = '#f8faff'
WHITE = (255, 255, 255)
BADGE_GOLD = (241, 196, 15)
BADGE_TEXT = (120, 80, 0)

# Color palette: (main, dark variant) — randomly assigned to each book
COLOR_PALETTE = [
    ((39, 174, 96),   (30, 132, 73)),    # Green
    ((52, 152, 219),  (41, 121, 175)),    # Blue
    ((155, 89, 182),  (124, 71, 146)),    # Purple
    ((231, 76, 60),   (185, 61, 48)),     # Red
    ((230, 126, 34),  (184, 101, 27)),    # Orange
    ((26, 188, 156),  (21, 150, 125)),    # Teal
    ((241, 196, 15),  (193, 157, 12)),    # Gold
    ((44, 62, 80),    (35, 50, 64)),      # Dark Navy
    ((142, 68, 173),  (114, 54, 138)),    # Amethyst
    ((22, 160, 133),  (18, 128, 106)),    # Dark Teal
]

COVER_DIR = os.path.join(os.path.dirname(__file__), 'media', 'book_covers')
os.makedirs(COVER_DIR, exist_ok=True)


def get_font(size, bold=False):
    """Try to load a good font, fallback to default."""
    font_candidates = [
        'C:/Windows/Fonts/msyh.ttc',      # Microsoft YaHei
        'C:/Windows/Fonts/msyhbd.ttc',     # Microsoft YaHei Bold
        'C:/Windows/Fonts/simhei.ttf',     # SimHei
        'C:/Windows/Fonts/simsun.ttc',     # SimSun
        'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    if bold:
        font_candidates.insert(0, 'C:/Windows/Fonts/msyhbd.ttc')
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(text, max_chars=12):
    """Wrap text into lines for display on cover."""
    lines = []
    for line in textwrap.wrap(text, width=max_chars):
        lines.append(line)
    return lines if lines else [text]


def generate_cover(book, card_color, card_color_dark):
    """Generate a single book cover image with the given color theme."""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # --- Card background with rounded appearance ---
    card_left = CARD_MARGIN
    card_top = CARD_MARGIN + 10
    card_right = WIDTH - CARD_MARGIN
    card_bottom = HEIGHT - CARD_MARGIN - 10
    
    # Draw rounded card
    draw.rounded_rectangle(
        [card_left, card_top, card_right, card_bottom],
        radius=16, fill=card_color
    )

    # --- Top gradient bar ---
    bar_height = 8
    for i in range(bar_height):
        r = card_color_dark[0] + (card_color[0] - card_color_dark[0]) * i // bar_height
        g = card_color_dark[1] + (card_color[1] - card_color_dark[1]) * i // bar_height
        b = card_color_dark[2] + (card_color[2] - card_color_dark[2]) * i // bar_height
        draw.line([(card_left, card_top + i), (card_right, card_top + i)], fill=(r, g, b))

    # --- White border frame inside card ---
    frame_margin = 30
    frame_left = card_left + frame_margin
    frame_top = card_top + 60
    frame_right = card_right - frame_margin
    frame_bottom = card_bottom - 110
    draw.rounded_rectangle(
        [frame_left, frame_top, frame_right, frame_bottom],
        radius=4, outline=WHITE, width=BORDER_WIDTH
    )

    # --- Horizontal line above title area ---
    line_y = frame_top - 20
    line_margin = 50
    draw.line(
        [(card_left + line_margin, line_y), (card_right - line_margin, line_y)],
        fill=WHITE, width=2
    )

    # --- Book Title (centered inside frame) ---
    title_font = get_font(22, bold=True)
    title_lines = wrap_text(book.name, max_chars=14)
    
    # Calculate total text height
    line_height = 32
    total_text_h = len(title_lines) * line_height
    text_start_y = frame_top + (frame_bottom - frame_top - total_text_h) // 2

    for i, line in enumerate(title_lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        tx = (frame_left + frame_right - tw) // 2
        ty = text_start_y + i * line_height
        draw.text((tx, ty), line, fill=WHITE, font=title_font)

    # --- BESTSELLER Badge ---
    badge_font = get_font(11, bold=True)
    badge_text = '★ BESTSELLER ★'
    badge_y = frame_bottom + 14
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bx = (card_left + card_right - bw) // 2
    
    # Badge background pill
    pad_x, pad_y = 14, 5
    draw.rounded_rectangle(
        [bx - pad_x, badge_y - pad_y, bx + bw + pad_x, badge_y + 16 + pad_y],
        radius=10, fill=BADGE_GOLD
    )
    draw.text((bx, badge_y), badge_text, fill=BADGE_TEXT, font=badge_font)

    # --- Bottom label: 精品图书 ---
    label_font = get_font(14)
    label_text = '精品图书'
    bbox = draw.textbbox((0, 0), label_text, font=label_font)
    lw = bbox[2] - bbox[0]
    lx = (card_left + card_right - lw) // 2
    ly = card_bottom - 38
    # Lighter tint of the card color for label text
    label_tint = (
        min(card_color[0] + 160, 255),
        min(card_color[1] + 160, 255),
        min(card_color[2] + 160, 255),
    )
    draw.text((lx, ly), label_text, fill=label_tint, font=label_font)

    # --- Dot indicators at the very bottom ---
    dot_y = card_bottom - 16
    dot_count = 5
    dot_spacing = 12
    dot_start_x = (WIDTH - (dot_count - 1) * dot_spacing) // 2
    dot_muted = (
        min(card_color[0] + 60, 255),
        min(card_color[1] + 60, 255),
        min(card_color[2] + 60, 255),
    )
    for i in range(dot_count):
        dx = dot_start_x + i * dot_spacing
        r = 3
        fill_color = WHITE if i == 0 else dot_muted
        draw.ellipse([dx - r, dot_y - r, dx + r, dot_y + r], fill=fill_color)

    # --- Heart icon (top left of card) ---
    heart_x, heart_y = card_left + 18, card_top + 18
    heart_r = 18
    heart_bg = (
        min(card_color[0] + 160, 255),
        min(card_color[1] + 160, 255),
        min(card_color[2] + 160, 255),
    )
    draw.ellipse(
        [heart_x - heart_r, heart_y - heart_r, heart_x + heart_r, heart_y + heart_r],
        fill=heart_bg
    )
    heart_font = get_font(18)
    draw.text((heart_x - 9, heart_y - 11), '♡', fill=card_color, font=heart_font)

    # --- Small dot indicator (top right) ---
    dot2_x = card_right - 35
    dot2_y = card_top + 18
    draw.ellipse([dot2_x - 4, dot2_y - 4, dot2_x + 4, dot2_y + 4], fill=dot_muted)

    return img


def main():
    books = list(Book.objects.all())
    print(f'Generating covers for {len(books)} books...\n')

    # Shuffle color palette and cycle through to ensure variety
    colors = list(COLOR_PALETTE)
    random.shuffle(colors)

    for idx, book in enumerate(books):
        card_color, card_color_dark = colors[idx % len(colors)]

        # Generate a clean filename
        safe_name = ''.join(c if c.isalnum() or c in '-_ ' else '' for c in book.name)[:30].strip()
        filename = f'gen_cover_{book.id}_{safe_name}.png'
        filepath = os.path.join(COVER_DIR, filename)

        img = generate_cover(book, card_color, card_color_dark)
        img.save(filepath, 'PNG', quality=95)

        # Update database
        book.cover_image = f'book_covers/{filename}'
        book.save(update_fields=['cover_image'])

        color_name = ['Green', 'Blue', 'Purple', 'Red', 'Orange', 'Teal', 'Gold', 'Navy', 'Amethyst', 'DarkTeal'][colors.index((card_color, card_color_dark))]
        print(f'  ✓ ID={book.id} | {book.name} → {filename} ({color_name})')

    print(f'\nDone! Generated {len(books)} covers with randomized colors.')


if __name__ == '__main__':
    main()
