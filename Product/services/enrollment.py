from Calendar.models import Day  # یا مسیر درست مدل خودت
from Product.utils import normalize_persian_text


class EnrollmentService:

    def __init__(self, start_day, session_count, allowed_day_names):
        self.start_day = start_day  # instance of Day
        self.session_count = session_count
        self.allowed_day_names = allowed_day_names

    def get_valid_days(self):
        normalized_allowed = [normalize_persian_text(d) for d in self.allowed_day_names]
        print("✅ normalized_allowed =", normalized_allowed)

        raw_days = Day.objects.filter(
            holiday=False,
            month__year__number__gte=self.start_day.month.year.number - 1
        ).select_related("month", "month__year")


        normalized_raw = []
        for d in raw_days:
            norm_name = normalize_persian_text(d.weekday_name)
            print(f"📅 Day {d} → raw='{d.weekday_name}' → normalized='{norm_name}'")
            if norm_name in normalized_allowed:
                normalized_raw.append(d)

        start_jdate = self.start_day.jdate

        valid_days = sorted(
            [d for d in raw_days if d.jdate and d.jdate >= start_jdate],
            key=lambda d: d.jdate
        )

        return valid_days[:self.session_count]

    def get_start_and_end_day(self):
        days = self.get_valid_days()
        if len(days) < self.session_count:
            raise ValueError("تعداد روزهای معتبر کافی نیست.")
        return days[0], days[-1]
