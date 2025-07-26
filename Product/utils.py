import re

def normalize_persian_space(s):
    if not s:
        return ''
    # جایگزین کردن هر ترکیب فاصله و نیم فاصله با یه فاصله عادی
    return re.sub(r'[\u200c\s]+', ' ', s).strip()
