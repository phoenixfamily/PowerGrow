from Calendar.models import Day  # یا مسیر درست مدل خودت
from Product.utils import normalize_persian_text


class EnrollmentService:

    def __init__(self, start_day, session_count, allowed_day_names):
        self.start_day = start_day  # instance of Day
        self.session_count = session_count
        self.allowed_day_names = allowed_day_names

    def get_valid_days(self):
        normalized_allowed = [normalize_persian_text(d) for d in self.allowed_day_names]

        raw_days = Day.objects.filter(
            holiday=False,
            month__year__number__gte=self.start_day.month.year.number - 1
        ).select_related("month", "month__year").order_by('id')

        # فقط روزهایی که اسمشون داخل لیست مجاز هست
        raw_days = [d for d in raw_days if normalize_persian_text(d.name) in normalized_allowed]

        # تبدیل start_day به یک کلید عددی (سال، ماه، روز)
        start_key = (
            self.start_day.month.year.number,
            self.start_day.month.number,
            self.start_day.number,
        )

        # فیلتر و مرتب‌سازی
        valid_days = sorted(
            [
                d for d in raw_days
                if (
                    d.month and d.month.year and d.number and
                    (d.month.year.number, d.month.number, d.number) >= start_key
            )
            ],
            key=lambda d: (
                d.month.year.number,
                d.month.number,
                d.number,
                d.id  # برای پایداری مرتب‌سازی
            )
        )

        return valid_days[:self.session_count]

    def get_start_and_end_day(self):
        days = self.get_valid_days()
        if len(days) < self.session_count:
            raise ValueError("تعداد روزهای معتبر کافی نیست.")
        return days[0], days[-1]
