from django.db import models
from django.utils import timezone
from jdatetime import date as jdate

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
    active = models.BooleanField(blank=True, null=True, verbose_name='فعال')
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
    active = models.BooleanField(blank=True, null=True, verbose_name='فعال')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True, verbose_name="دوره")

    def __str__(self):
        return f"{self.course}-{self.number} جلسه "


class Days(models.Model):
    title = models.TextField(blank=True, null=True, verbose_name="روز هفته")
    tuition = models.IntegerField(verbose_name="شهریه")
    off = models.IntegerField(blank=True, null=True, verbose_name="تخفیف")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='days', null=True, blank=True, verbose_name="جلسه")


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

    endDay = models.ForeignKey(Day, on_delete=models.CASCADE, related_name='end_participants',
                               blank=True, null=True, verbose_name='پایان')

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='participants', null=True, blank=True)
    created = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant',
                                blank=True, null=True)
    authority = models.TextField(unique=True, blank=True, null=True)
    success = models.BooleanField(blank=True, null=True)
    expired = models.BooleanField(default=False)

    # 👇 متد جدید برای تبدیل به jdate
    def to_jdate(self):
        try:
            return jdate(self.month.year.number, self.month.number, self.number)
        except Exception:
            return None


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




