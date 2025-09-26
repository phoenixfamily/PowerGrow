from datetime import timedelta
from jdatetime import date
from Calendar.models import Day
from Product.utils import normalize_persian_text


class EnrollmentService:
    def __init__(self, start_day, session_count, allowed_day_names):
        self.start_day = start_day
        self.session_count = session_count
        self.allowed_day_names = allowed_day_names

        # مپینگ استاندارد روزها
        raw_map = {
            "شنبه": 0,
            "یکشنبه": 1,
            "دوشنبه": 2,
            "سه شنبه": 3,
            "چهارشنبه": 4,
            "پنج‌شنبه": 5,
            "جمعه": 6,
        }
        # همه کلیدها رو normalize می‌کنیم
        self.day_name_to_index = {
            normalize_persian_text(k): v for k, v in raw_map.items()
        }

    def get_valid_days(self):
        allowed_day_indices = [
            self.day_name_to_index[normalize_persian_text(name)]
            for name in self.allowed_day_names
            if normalize_persian_text(name) in self.day_name_to_index
        ]

        # تبدیل start_day به تاریخ شمسی
        start_date = date(
            self.start_day.month.year.number,
            self.start_day.month.number,
            self.start_day.number
        )

        valid_days = []
        current_date = start_date
        days_checked = 0
        max_days_to_check = self.session_count * 7  # حداکثر بررسی

        while len(valid_days) < self.session_count and days_checked < max_days_to_check:
            if current_date.weekday() in allowed_day_indices:
                try:
                    day = Day.objects.get(
                        number=current_date.day,
                        month__number=current_date.month,
                        month__year__number=current_date.year,
                        holiday=False
                    )
                    valid_days.append(day)
                except Day.DoesNotExist:
                    pass

            current_date += timedelta(days=1)
            days_checked += 1

        if len(valid_days) < self.session_count:
            raise ValueError(
                f"تعداد روزهای معتبر کافی نیست. یافت‌شده: {len(valid_days)}، مورد نیاز: {self.session_count}"
            )

        return valid_days

    def get_start_and_end_day(self):
        days = self.get_valid_days()
        return days[0], days[-1]