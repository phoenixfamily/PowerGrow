import jdatetime
from Calendar.models import Year, Month, Day

def update_days():
    """
    آپدیت همه رکوردهای Day:
    - محاسبه gregorian_date
    - محاسبه weekday (شنبه=0, جمعه=6)
    """
    for day in Day.objects.all():
        try:
            year = day.month.year.number
            month = day.month.number
            day_number = day.number

            # تبدیل Jalali → Gregorian
            g_date = jdatetime.date(year, month, day_number).togregorian()
            day.gregorian_date = g_date

            # محاسبه weekday: Python Monday=0 ... Sunday=6
            python_weekday = g_date.weekday()  # Monday=0
            # تبدیل به شنبه=0 ... جمعه=6
            weekday_map = {0:1, 1:2, 2:3, 3:4, 4:5, 5:6, 6:0}
            day.weekday = weekday_map[python_weekday]

            day.save(update_fields=['gregorian_date', 'weekday'])
            print(f"Updated Day {day} -> {day.gregorian_date}, weekday={day.weekday}")
        except Exception as e:
            print(f"Error updating Day {day.id}: {e}")

if __name__ == "__main__":
    update_days()
