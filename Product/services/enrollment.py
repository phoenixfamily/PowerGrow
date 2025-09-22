from jdatetime import date, timedelta
from Calendar.models import Day
from Product.utils import normalize_persian_text

class EnrollmentService:
    def __init__(self, start_day, session_count, allowed_day_names):
        self.start_day = start_day  # instance of Day
        self.session_count = session_count
        self.allowed_day_names = allowed_day_names
        # تبدیل نام‌های روز به اعداد (0=شنبه, 1=یک‌شنبه, ..., 6=جمعه)
        self.day_name_to_index = {
            normalize_persian_text("شنبه"): 0,
            normalize_persian_text("یک‌شنبه"): 1,
            normalize_persian_text("دوشنبه"): 2,
            normalize_persian_text("سه ‌شنبه"): 3,
            normalize_persian_text("چهارشنبه"): 4,
            normalize_persian_text("پنجشنبه"): 5,
            normalize_persian_text("جمعه"): 6,
        }

    def get_valid_days(self):
        normalized_allowed = [normalize_persian_text(d) for d in self.allowed_day_names]
        allowed_day_indices = [self.day_name_to_index[name] for name in normalized_allowed if name in self.day_name_to_index]

        # تبدیل start_day به تاریخ شمسی
        start_date = date(
            self.start_day.month.year.number,
            self.start_day.month.number,
            self.start_day.number
        )

        valid_days = []
        current_date = start_date
        days_checked = 0
        max_days_to_check = self.session_count * 7  # حداکثر بررسی برای جلوگیری از حلقه بی‌نهایت

        while len(valid_days) < self.session_count and days_checked < max_days_to_check:
            # بررسی آیا روز جاری در allowed_day_names است
            if current_date.weekday() in allowed_day_indices:
                # بررسی تعطیل نبودن در دیتابیس
                try:
                    day = Day.objects.get(
                        number=current_date.day,
                        month__number=current_date.month,
                        month__year__number=current_date.year,
                        holiday=False
                    )
                    valid_days.append(day)
                except Day.DoesNotExist:
                    pass  # روز تعطیل است یا وجود ندارد

            current_date += timedelta(days=1)
            days_checked += 1

        if len(valid_days) < self.session_count:
            raise ValueError(f"تعداد روزهای معتبر کافی نیست. یافت‌شده: {len(valid_days)}، مورد نیاز: {self.session_count}")

        return valid_days

    def get_start_and_end_day(self):
        days = self.get_valid_days()
        return days[0], days[-1]