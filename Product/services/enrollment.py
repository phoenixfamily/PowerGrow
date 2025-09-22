from Calendar.models import Day
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

        # فیلتر دستی
        filtered_days = [d for d in raw_days if normalize_persian_text(d.weekday_name) in normalized_allowed]

        start_jdate = self.start_day.jdate

        valid_days = sorted(
            [d for d in filtered_days if d.jdate and d.jdate >= start_jdate],
            key=lambda d: d.jdate
        )

        return valid_days, normalized_allowed, filtered_days

    def get_start_and_end_day(self):
        valid_days, normalized_allowed, filtered_days = self.get_valid_days()
        if len(valid_days) > self.session_count:
            raise ValueError({
                "normalized_allowed": normalized_allowed,
                "filtered_days": [(d.id, d.name, d.weekday_name, d.jdate) for d in filtered_days],
                "valid_days": [(d.id, d.name, d.weekday_name, d.jdate) for d in valid_days],
                "needed_session_count": self.session_count
            })
        return valid_days[0], valid_days[-1]
