import jdatetime
from django.db import models
from django.utils import timezone

from Calendar.models import Day
from PowerGrow import settings
from User.models import User

TYPE_CHOICE = [
    ('public', 'عمومی'),
    ('private', 'خصوصی'),
    ('semi_private', 'نیمه خصوصی'),  # گزینه جدید
]
GENDER_CHOICE = [
    ('male', 'مرد'),
    ('female', 'زن'),
]


DAY_CHOICES = [
    (0, "شنبه"),
    (1, "یکشنبه"),
    (2, "دوشنبه"),
    (3, "سه‌شنبه"),
    (4, "چهارشنبه"),
    (5, "پنجشنبه"),
    (6, "جمعه"),
]



class Sport(models.Model):
    title = models.CharField(max_length=50, verbose_name='نام')

    def __str__(self):
        return self.title  # به جای ID، نام ورزش را نمایش می‌دهد


class Course(models.Model):
    title = models.TextField(blank=True, null=True, verbose_name='عنوان')
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name='نام مربی')
    type = models.CharField(max_length=100, choices=TYPE_CHOICE, default='public', verbose_name='نوع دوره')
    time = models.TextField(blank=True, null=True,verbose_name='زمان')
    description = models.TextField(blank=True, null=True, verbose_name='توضیحات')
    image = models.ImageField(upload_to="images/", blank=True, null=True, verbose_name='تصویر')
    selected = models.BooleanField(default=False, blank=True, null=True, verbose_name='منتخب')
    capacity = models.IntegerField(blank=True, null=True, verbose_name='ظرفیت')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICE, verbose_name='جنسیت')
    datetime = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True, verbose_name='فعال')
    previous = models.BooleanField(default=False, blank=True, null=True, verbose_name='پیش ثبت نام')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='courses', null=True, blank=True,
                              verbose_name='ورزش')
    def __str__(self):
        return f"{self.title}-{self.pk}"  # به جای ID، نام ورزش را نمایش می‌دهد

    def is_full(self):
        active_participants = self.participants.filter(expired=False, success=True).count()
        return active_participants >= self.capacity


class Session(models.Model):
    number = models.IntegerField(blank=True, null=True, verbose_name="تعداد جلسات")
    active = models.BooleanField(default=True, verbose_name='فعال')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True, verbose_name="دوره")

    def __str__(self):
        return f"{self.course}-{self.number} جلسه "


class Days(models.Model):
    title = models.TextField(blank=True, null=True, verbose_name="روز هفته")
    days = models.JSONField(blank=True, null=True, verbose_name="روزهای هفته")
    active = models.BooleanField(default=True, verbose_name='فعال')
    tuition = models.IntegerField(verbose_name="شهریه")
    off = models.IntegerField(default=0, verbose_name="تخفیف")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='days', null=True, blank=True, verbose_name="جلسه")

    def save(self, *args, **kwargs):
        if self.days:
            # گرفتن متن روزها از ایندکس‌ها
            day_map = dict(DAY_CHOICES)
            self.title = '،'.join([day_map.get(d, '') for d in self.days if d in day_map])
        super().save(*args, **kwargs)


class Participants(models.Model):
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='participants', null=True, blank=True)
    day = models.ForeignKey(Days, on_delete=models.CASCADE, related_name='participants', null=True, blank=True)
    price = models.IntegerField(default=0)
    datetime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='participants',
                             blank=True, null=True)

    startDay = models.ForeignKey(Day, on_delete=models.CASCADE, related_name='participants',
                                 blank=True, null=True, verbose_name='َشروع')

    endDay = models.ForeignKey(Day, on_delete=models.CASCADE, related_name='end_participants', blank=True, null=True, verbose_name='پایان')

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='participants', null=True, blank=True)
    created = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant',
                                blank=True, null=True)
    authority = models.TextField(unique=True, blank=True, null=True)
    success = models.BooleanField(blank=True, null=True)
    expired = models.BooleanField(default=False)

    def calculate_start_day(self):
        """
        محاسبه اولین روز واقعی کلاس بعد از startDay کاربر،
        با توجه به روزهای انتخاب‌شده (مثلا یکشنبه/سه‌شنبه).
        """
        start_day = self.startDay
        selected_weekdays = self.day.days if self.day and self.day.days else []

        if not start_day or not selected_weekdays:
            return None

        days_qs = Day.objects.filter(
            gregorian_date__gte=start_day.gregorian_date
        ).order_by('gregorian_date').only('id', 'weekday', 'gregorian_date')

        for d in days_qs.iterator():
            if d.weekday in selected_weekdays:
                return d

        return None


    def calculate_end_day(self):
        start_day = self.startDay
        session_count = self.session.number if self.session else 0
        selected_weekdays = self.day.days if self.day and self.day.days else []

        if not start_day or not selected_weekdays or session_count == 0:
            return None

        sessions_done = 0
        days_qs = Day.objects.filter(
            gregorian_date__gte=start_day.gregorian_date
        ).order_by('gregorian_date').only('id', 'weekday', 'gregorian_date')

        for day in days_qs.iterator():
            if day.weekday in selected_weekdays:
                sessions_done += 1
                if sessions_done >= session_count:
                    return day

        # fallback: آخرین روز موجود در queryset
        return days_qs.last()

    @property
    def datetime_jalali(self):
        if not self.datetime:
            return ""
        return jdatetime.datetime.fromgregorian(datetime=self.datetime).strftime("%Y/%m/%d %H:%M")

    def save(self, *args, **kwargs):
        if self.startDay and self.session and self.day:
            real_start = self.calculate_start_day()
            if real_start:
                self.startDay = real_start
            self.endDay = self.calculate_end_day()
        super().save(*args, **kwargs)


class Offers(models.Model):
    TYPE_CHOICES = [
        ('ALL', 'All'),
        ('SPORT', 'ورزش'),
        ('COURSE', 'دوره'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    product = models.IntegerField(default=0, blank=True, null=True, verbose_name="محصول")
    session = models.IntegerField(default=0, blank=True, null=True, verbose_name="جلسات")
    off = models.IntegerField(blank=True, null=True, verbose_name="تخفیف")




