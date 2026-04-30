import re, os, sys, json
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

def parse_po(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()
    entries = re.findall(r'msgid "(.+?)"\nmsgstr "(.+?)"', content, re.DOTALL)
    return {k: v for k, v in entries if k}

def find_trans_strings(paths):
    found = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        for root, dirs, files in os.walk(path):
            for fname in files:
                if not fname.endswith('.html'):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                found.update(re.findall(r"""\{%\s*trans\s*'([^']+)'\s*%\}""", text))
                found.update(re.findall(r"""\{%\s*trans\s*"([^"]+)"\s*%\}""", text))
    return found

template_dirs = ['manager/templates', 'marketplace/templates', 'templates']
trans_strings = find_trans_strings(template_dirs)

en_po = parse_po('locale/en/LC_MESSAGES/django.po')
fr_po = parse_po('locale/fr/LC_MESSAGES/django.po')

missing_en = [s for s in sorted(trans_strings) if s not in en_po and re.search(r'[\u4e00-\u9fff]', s)]
missing_fr = [s for s in sorted(trans_strings) if s not in fr_po and re.search(r'[\u4e00-\u9fff]', s)]

print(f'Total trans strings found: {len(trans_strings)}')
print(f'Strings in EN .po: {len(en_po)}')
print(f'Strings in FR .po: {len(fr_po)}')
print(f'Missing from EN .po: {len(missing_en)}')
print(f'Missing from FR .po: {len(missing_fr)}')
print()
if missing_en:
    print('Missing EN translations:')
    for s in missing_en[:50]:
        print(f'  [{s}]')
else:
    print('EN translations: COMPLETE')
if missing_fr:
    print()
    print('Missing FR translations:')
    for s in missing_fr[:50]:
        print(f'  [{s}]')
else:
    print('FR translations: COMPLETE')

# Write missing strings to JSON for further processing
with open('missing_strings.json', 'w', encoding='utf-8') as f:
    json.dump({'missing_en': missing_en, 'missing_fr': missing_fr}, f, ensure_ascii=False, indent=2)
print(f'\nWritten to missing_strings.json')
