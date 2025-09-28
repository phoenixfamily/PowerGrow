import re

def normalize_persian_text(text: str) -> str:
    if not text:
        return ""

    # حذف کاراکترهای مخفی و فاصله عجیب
    text = re.sub(r"[\u200c\u200f\u202a\u202b\u202c\u00a0]", " ", text)

    # یکی‌سازی ک عربی (ك) → ک فارسی
    text = text.replace("ك", "ک")

    # یکی‌سازی ی عربی (ي) → ی فارسی
    text = text.replace("ي", "ی")

    # چند فاصله یا نیم فاصله پشت سر هم → یک فاصله
    text = re.sub(r"\s+", " ", text).strip()

    return text

