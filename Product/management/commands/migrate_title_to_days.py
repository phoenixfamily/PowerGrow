import re
from Product.models import Days

# mapping فارسی روز هفته به عدد
weekday_map = {
    "شنبه": 0,
    "یکشنبه": 1,
    "دوشنبه": 2,
    "سه‌شنبه": 3,
    "چهارشنبه": 4,
    "پنجشنبه": 5,
    "جمعه": 6,
}

def migrate_title_to_days():
    for day in Days.objects.all():
        try:
            if day.title:
                # جدا کردن اسم‌ها با کاما یا ویرگول فارسی
                day_names = re.split(r'[،,]', day.title)
                # تبدیل به لیست اعداد
                day_list = [weekday_map[name.strip()] for name in day_names if name.strip() in weekday_map]
                # ذخیره در فیلد days (JSONField)
                day.days = day_list
                day.save(update_fields=['days'])
                print(f"Updated Days id={day.id}: {day.title} -> {day.days}")
            else:
                day.days = []
                day.save(update_fields=['days'])
                print(f"Updated Days id={day.id}: title خالی -> days=[]")
        except Exception as e:
            print(f"Error updating Days id={day.id}: {e}")

if __name__ == "__main__":
    migrate_title_to_days()
