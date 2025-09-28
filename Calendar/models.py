import jdatetime
from django.db import models


DAY_CHOICES = [
    (0, "شنبه"),
    (1, "یکشنبه"),
    (2, "دوشنبه"),
    (3, "سه‌شنبه"),
    (4, "چهارشنبه"),
    (5, "پنجشنبه"),
    (6, "جمعه"),
]
WEEKDAY_NAMES = {num: name for num, name in DAY_CHOICES}

class Year(models.Model):
    number = models.IntegerField(unique=True, null=True, blank=True)
    leap = models.BooleanField(blank=True, null=True)


class Month(models.Model):
    name = models.CharField(blank=True, null=True, max_length=20)
    number = models.IntegerField(blank=True, null=True)
    max = models.IntegerField(blank=True, null=True)
    year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='months', null=True, blank=True)

    class Meta:
        unique_together = ('year', 'number')

    def __str__(self):
        # فرض بر این است که شماره روز و شماره ماه و سال را می‌خواهیم نمایش دهیم
        year = self.year.number if self and self.year else "Unknown Year"
        return f"{year}-{self.name}"  # به فرمت YYYY/MM/DD

    @property
    def start_day(self):
        """اولین روز این ماه"""
        return self.days.order_by("number").first()

    @property
    def end_day(self):
        """آخرین روز این ماه"""
        return self.days.order_by("-number").first()

    @property
    def start_weekday(self):
        """روز هفته شروع ماه"""
        first_day = self.start_day
        return first_day.weekday if first_day else None


class Day(models.Model):
    number = models.IntegerField(blank=True, null=True, verbose_name="شماره روز در ماه")
    name = models.CharField(blank=True, null=True, max_length=20, verbose_name="نام روز در هفته")
    weekday = models.IntegerField(choices=DAY_CHOICES, blank=True, null=True)
    gregorian_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات مناسبت")
    holiday = models.BooleanField(blank=True, null=True, verbose_name="تعطیلات")
    month = models.ForeignKey(Month, on_delete=models.CASCADE, related_name='days', null=True, blank=True,
                              verbose_name="ماه")

    class Meta:
        ordering = ['gregorian_date']  # پیمایش روزانه امن و سریع

    def save(self, *args, **kwargs):
        # اگر gregorian_date پر نشده، محاسبه کن
        if not self.gregorian_date:
            self.gregorian_date = jdatetime.date(self.month.year.number, self.month.number, self.number).togregorian()

        if self.weekday is not None:
            self.name = WEEKDAY_NAMES.get(self.weekday)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.month.year.number}/{self.month.number}/{self.number} ({self.get_weekday_display()})"



class Time(models.Model):
    time = models.TimeField(blank=True, null=True, verbose_name="زمان")
    duration = models.IntegerField(blank=True, null=True, verbose_name="مدت به دقیقه")
    reserved = models.BooleanField(blank=True, null=True, verbose_name="رزرو شده")
    res_id = models.IntegerField(blank=True, null=True)
    price = models.IntegerField(default=695000, verbose_name="قیمت")
    off = models.IntegerField(default=0, verbose_name="تخفیف")
    day = models.ForeignKey(Day, on_delete=models.CASCADE, related_name='times', null=True, blank=True,
                            verbose_name="تاریخ")

    def __str__(self):
        # فرض بر این است که شماره روز و شماره ماه و سال را می‌خواهیم نمایش دهیم
        year = self.day.month.year.number if self.day.month else "Unknown Year"
        return f"{year}/{self.day.month.number}/{self.day.number} : {self.time}"  # به فرمت YYYY/MM/DD
