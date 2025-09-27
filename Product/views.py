import requests
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils import json
import jdatetime
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from About.models import AboutUs
from Calendar.models import Day
from PowerGrow.decorators import *
from Product.serializer import *
from django.conf import settings
import json
from PowerGrow.permissions import *

from Product.services.enrollment import EnrollmentService

from Product.utils import normalize_persian_text
from rest_framework.parsers import MultiPartParser, FormParser

User = get_user_model()

if settings.SANDBOX:
    sandbox = 'sandbox'
else:
    sandbox = 'www'

ZP_API_REQUEST = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
ZP_API_VERIFY = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentVerification.json"
ZP_API_STARTPAY = f"https://{sandbox}.zarinpal.com/pg/StartPay/"
CallbackURL = 'https://powergrow.ir/product/verify/'


@cache_page(60 * 15)
def sport_view(request):
    about = AboutUs.objects.first()
    sports = Sport.objects.all()

    # برای هر ورزش، لیست دوره‌هاش رو بگیر
    sport_data = []
    for sport in sports:
        courses = Course.objects.filter(sport=sport, active=True).order_by('-datetime')[:10]
        sport_data.append({
            'sport': sport,
            'courses': courses
        })

    context = {
        "about": about,
        "sport_data": sport_data
    }

    return render(request, 'public/sports.html', context)


@cache_page(60 * 15)
def category_view(request, pk):
    about = AboutUs.objects.first()  # Assuming there's only one AboutUs instance
    sport = get_object_or_404(Sport, id=pk)  # Ensure the sport exists
    courses = Course.objects.filter(sport=sport, active=True)

    context = {
        "about": about,
        "sport": sport,
        "courses": courses,
    }

    return render(request, 'public/category.html', context)


@cache_page(60 * 15)
def offer_view(request):
    about = AboutUs.objects.first()  # Assuming there's only one AboutUs instance

    day = Days.objects.filter(off__gt=0).order_by('pk').values_list('session__course__id', flat=True)
    course = Course.objects.filter(pk__in=list(day)).order_by("datetime").values()

    context = {
        "course": course,
        "about": about,
    }

    return render(request, 'public/offer.html', context)


def product_view(request, pk):
    about = AboutUs.objects.first()
    sport = Sport.objects.all()
    product = get_object_or_404(Course, id=pk)
    session = Session.objects.all().filter(course_id=pk, active=True).order_by("number")
    days = Days.objects.all().filter(session__course=pk, session__course__active=True)

    update_expired_participants(pk)

    participants = Participants.objects.filter(
        course=product,
        user__is_teacher=False,
        user__is_superuser=False,
        user__is_staff=False,
        price__gt=0,
        success=True
    )

    context = {
        "about": about,
        "product": product,
        "participants": participants,
        "days": days,
        "sport": sport,
        "session": session,
    }

    return render(request, 'public/product.html', context)


def course_search(request):
    q = (request.GET.get("q") or "").strip()
    qs = Course.objects.all().filter(active=True)
    if q:
        vector = SearchVector("title", weight="A") + SearchVector("description", weight="B")
        query = SearchQuery(q)
        qs = qs.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0.001).order_by("-rank")

    paginator = Paginator(qs, 12)  # هر صفحه ۱۲ نتیجه (دلخواه)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "q": q,
        "page_obj": page_obj,
        "results_count": paginator.count,
    }
    return render(request, "public/search_results.html", context)


def get_days_for_session(request):
    session_id = request.GET.get('session_id')
    days = Days.objects.filter(session_id=session_id).values('id', 'title', 'tuition', 'off')
    return JsonResponse(list(days), safe=False)


@session_auth_required
def payment_view(request, pk, session, day, start):
    about = AboutUs.objects.first()  # Assuming there's only one AboutUs instance
    product = get_object_or_404(Course, id=pk)
    sessions = get_object_or_404(Session, id=session)
    days = get_object_or_404(Days, id=day)
    start_day = get_object_or_404(Day, id=start)

    context = {
        "about": about,
        "product": product,
        "session": sessions,
        "day": days,
        "start": start_day,
    }

    return render(request, 'public/payment.html', context)


@api_view(['GET'])
def verify(request):
    authority = request.GET.get('Authority', '')
    participants = get_object_or_404(Participants, authority=authority)

    about = AboutUs.objects.first()  # Assuming there's only one AboutUs instance
    sport = Sport.objects.all()

    authority_data = {
        "MerchantID": settings.MERCHANT,
        "Authority": participants.authority,
        "Amount": participants.price
    }

    data = json.dumps(authority_data)
    headers = {'content-type': 'application/json', 'content-length': str(len(data))}
    response = requests.post(ZP_API_VERIFY, data=data, headers=headers)
    response_data = response.json()

    if response_data.get('Status') == 100:
        participants.success = True
        participants.save()
        return render(request, 'public/check.html', {
            "about": about,
            "sport": sport,
            "participants": participants
        })
    else:
        return render(request, 'public/error.html', {
            "about": about,
            "sport": sport,
            "participants": participants
        })


@session_staff_required
def manager_sports_view(request):
    sport = Sport.objects.all()
    about = AboutUs.objects.values().first()
    context = {
        "about": about,
        "sport": sport,
    }
    return render(request, 'manager/sports.html', context)


@session_admin_required
def admin_sports_view(request):
    sport = Sport.objects.all()
    about = AboutUs.objects.first()
    context = {
        "about": about,
        "sport": sport,
    }
    return render(request, 'admin/sports.html', context)


@session_staff_required
def manager_courses_view(request):
    # بارگذاری اطلاعات دوره‌ها و اطلاعات اضافی
    courses = Course.objects.all().order_by("-pk")
    about = AboutUs.objects.first()
    users = User.objects.all()

    # پیاده‌سازی pagination
    paginator = Paginator(courses, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
        "users": users
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'manager/courses.html', context)


@session_admin_required
def admin_courses_view(request):
    courses = Course.objects.all().order_by("-pk")
    about = AboutUs.objects.first()
    users = User.objects.all()

    # پیاده‌سازی pagination
    paginator = Paginator(courses, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
        "users": users
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'admin/courses.html', context)


@session_teacher_required
def teacher_courses_view(request, pk):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری شرکت‌کنندگان مربوط به معلم
    participants = Participants.objects.filter(user_id=pk).order_by('-pk')

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "participants": participants,
        "user": pk,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'teacher/courses.html', context)


@session_auth_required
def user_courses_view(request, pk):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری شرکت‌کنندگان مربوط به کاربر
    participants = Participants.objects.filter(user_id=pk).order_by('-pk')

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "participants": participants,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'user/course.html', context)


@session_staff_required
def manager_session_view(request):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری تمامی جلسات
    sessions = Session.objects.all().order_by('-pk')

    # پیاده‌سازی pagination
    paginator = Paginator(sessions, 250)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'manager/sessions.html', context)


@session_admin_required
def admin_session_view(request):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری تمامی جلسات
    sessions = Session.objects.all().order_by('-pk')

    # پیاده‌سازی pagination
    paginator = Paginator(sessions, 250)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'admin/sessions.html', context)


@session_staff_required
def manager_days_view(request):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری تمامی روزها
    days = Days.objects.all().order_by('-pk')

    # پیاده‌سازی pagination
    paginator = Paginator(days, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'manager/days.html', context)


@session_admin_required
def admin_days_view(request):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری تمامی روزها
    days = Days.objects.all().order_by('-pk')

    # پیاده‌سازی pagination
    paginator = Paginator(days, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
    }
    return render(request, 'admin/days.html', context)


@session_staff_required
def manager_offers_view(request):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری تمامی روزها
    offers = Offers.objects.all().order_by('-pk')

    # پیاده‌سازی pagination
    paginator = Paginator(offers, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'manager/offers.html', context)


@session_admin_required
def admin_offers_view(request):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری تمامی روزها
    offers = Offers.objects.all().order_by('-pk')

    # پیاده‌سازی pagination
    paginator = Paginator(offers, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
    }
    return render(request, 'admin/offers.html', context)


@session_staff_required
def manager_user_list(request, pk):
    about = AboutUs.objects.first()

    participants_qs = Participants.objects.filter(course_id=pk)

    update_expired_participants(pk)

    # ✅ بعد از بروزرسانی، paginate کن
    participants = participants_qs.order_by('-endDay', 'startDay')

    paginator = Paginator(participants, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {
        "about": about,
        "page_obj": page_obj,
        "course_id": pk
    }
    return render(request, 'manager/list.html', context)


@session_admin_required
def admin_user_list(request, pk):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    # بارگذاری دوره با استفاده از get_object_or_404
    participants_qs = Participants.objects.filter(course_id=pk)

    update_expired_participants(pk)

    # ✅ بعد از بروزرسانی، paginate کن
    participants = participants_qs.order_by('-endDay', 'startDay')


    paginator = Paginator(participants, 150)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برگردیم

    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "page_obj": page_obj,
        "course_id": pk
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'admin/list.html', context)


@session_teacher_required
def teacher_user_list(request, pk):
    # بارگذاری اطلاعات مربوط به AboutUs
    about = AboutUs.objects.first()

    participants_qs = Participants.objects.filter(course_id=pk,expired=False, user__is_teacher=False, user__is_superuser=False, user__is_staff=False)

    update_expired_participants(pk)

    # ✅ بعد از بروزرسانی، paginate کن
    participants = participants_qs.order_by('-endDay', 'startDay')


    # آماده‌سازی context برای الگو
    context = {
        "about": about,
        "participants": participants,
    }

    # استفاده از render برای بارگذاری الگو
    return render(request, 'teacher/users.html', context)


@session_admin_required
def create_course_view(request):
    about = AboutUs.objects.first()
    sports = Sport.objects.all()

    context = {
        'about': about,
        'sports': sports,

    }

    return render(request, 'api/create-course.html', context)


@session_admin_required
def update_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    about = AboutUs.objects.first()
    sports = Sport.objects.all()


    context = {
        'course': course,
        'about': about,
        'sports': sports,

    }

    return render(request, 'api/update_course.html', context)


@session_admin_required
def update_session(request, pk):
    session = get_object_or_404(Session, pk=pk)
    about = AboutUs.objects.first()
    course = Course.objects.all()  # فرض بر این است که participant به course مرتبط است
    context = {
        'session': session,
        'course': course,
        'about': about,
    }

    return render(request, 'api/update_sessions.html', context)


@session_admin_required
def create_off_view(request):
    about = AboutUs.objects.first()
    sport = Sport.objects.all()
    course = Course.objects.all().order_by('-pk')
    context = {
        'about': about,
        'sport': sport,
        'course': course,
    }

    return render(request, 'api/create_off.html', context)


@session_admin_required
def create_participants(request, course_id):  # تغییر نام پارامتر به course_id
    about = AboutUs.objects.first()
    user = User.objects.all()
    course = get_object_or_404(Course, id=course_id)  # بارگذاری دوره با ID مربوطه
    days = Days.objects.filter(session__course=course_id)
    day = Day.objects.all().order_by('-pk')

    context = {
        'course': course,
        'days': days,
        'day': day,  # برای روزهای شروع و پایان
        'about': about,
        'user': user
    }

    return render(request, 'api/create-participants.html', context)


@session_admin_required
def update_participant_view(request, participant_id):
    participant = get_object_or_404(Participants, id=participant_id)
    course = Course.objects.all()  # فرض بر این است که participant به course مرتبط است
    session = Session.objects.filter(course_id=participant.course.id)  # تمام روزها را برای انتخاب
    days = Days.objects.filter(session__course=participant.course.id)  # تمام روزها را برای انتخاب
    day = Day.objects.all().order_by('-pk')
    about = AboutUs.objects.first()
    user = User.objects.all()

    context = {
        'participant': participant,
        'course': course,
        'session': session,
        'days': days,
        'day': day,  # برای روزهای شروع و پایان
        'about': about,
        'user': user

    }
    return render(request, 'api/update_participants.html', context)


class CourseListCreateView(generics.CreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUserOrStaff]


class CourseDetailView(viewsets.ViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUserOrStaff]
    parser_classes = [MultiPartParser, FormParser]

    def update(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(course, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
            course.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Course.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class SportListCreateView(generics.CreateAPIView):
    queryset = Sport.objects.all()
    serializer_class = SportSerializer
    permission_classes = [IsAdminUserOrStaff]


class SportDetailView(viewsets.ViewSet):
    queryset = Sport.objects.all()
    serializer_class = SportSerializer
    permission_classes = [IsAdminUserOrStaff]

    def destroy(self, request, pk):
        try:
            sport = Sport.objects.get(pk=pk)
            sport.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Participants.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk):
        try:
            sport = Sport.objects.get(pk=pk)
        except Sport.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(sport, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DaysListCreateView(generics.CreateAPIView):
    queryset = Days.objects.all()
    serializer_class = DaysCreateSerializer
    permission_classes = [IsAdminUserOrStaff]


class DaysDetailView(viewsets.ViewSet):
    queryset = Days.objects.all()
    serializer_class = DaysSerializer
    permission_classes = [IsAdminUserOrStaff]

    def destroy(self, request, pk):
        try:
            days = Days.objects.get(pk=pk)
            days.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Participants.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk):
        try:
            days = Days.objects.get(pk=pk)
        except Days.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(days, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SessionListCreateView(generics.CreateAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAdminUserOrStaff]


class SessionDetailView(viewsets.ViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAdminUserOrStaff]

    def update(self, request, pk):
        try:
            session = Session.objects.get(pk=pk)
        except Session.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(session, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk):
        try:
            session = Session.objects.get(pk=pk)
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Participants.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ParticipationCreateView(viewsets.ViewSet):
    queryset = Participants.objects.all()
    serializer_class = ParticipantsSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        data = request.data
        # Validate required fields
        required_fields = ['price', 'session', 'day', 'startDay', 'course']
        for field in required_fields:
            if field not in data:
                return Response({'error': f'Missing field: {field}'}, status=status.HTTP_400_BAD_REQUEST)

        authority_data = {
            "MerchantID": settings.MERCHANT,
            "Amount": data["price"],
            "phone": str(request.user.number),
            "Description": data["description"],
            "CallbackURL": CallbackURL,
        }

        try:
            response = requests.post(ZP_API_REQUEST, json=authority_data, timeout=10)
            response_data = response.json()

            if response_data.get('Status') == 100:
                session = Session.objects.filter(id=data["session"]).first()
                week = Days.objects.filter(id=data["day"]).first()
                start = Day.objects.filter(id=data["startDay"]).first()
                course = Course.objects.get(id=data["course"])

                day_names = [normalize_persian_text(d) for d in week.title.split("،")]


                if not all([course, week, start, session]):
                    return Response({
                        'error': 'برخی از داده‌ها نامعتبر هستند.',
                        'debug': {
                            'course': bool(course),
                            'week': bool(week),
                            'start': bool(start),
                            'session': bool(session),
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    service = EnrollmentService(start_day=start, session_count=session.number,
                                                allowed_day_names=day_names)
                    startDay, endDay = service.get_start_and_end_day()
                except ValueError as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

                participant_data = {
                    'description': data["description"],
                    'startDay': startDay.id,
                    'endDay': endDay.id,
                    'session': session.id,
                    'day': week.id,
                    'price': data["price"],
                    'user': request.user.id,
                    'course': course.id,
                    'authority': str(response_data['Authority']),
                    'success': False
                }

                serializer = self.serializer_class(data=participant_data)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    return Response({'payment': ZP_API_STARTPAY, 'authority': str(response_data['Authority'])},
                                    status=status.HTTP_201_CREATED)
                else:
                    return Response({'error': 'Validation failed', 'details': serializer.errors},
                                    status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'error': 'Payment request failed'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': 'An unexpected error occurred', 'details': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ManagerParticipationView(viewsets.ViewSet):
    serializer_class = ManagerParticipantsSerializer
    permission_classes = [IsAdminUserOrStaff]

    def create(self, request, course):
        data = request.data
        required_fields = ['price', 'session', 'day', 'startDay', 'user']

        # بررسی فیلدهای اجباری
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return Response({'error': f'فیلدهای الزامی حذف شده: {missing_fields}'}, status=status.HTTP_400_BAD_REQUEST)

        # گرفتن آبجکت‌ها
        course_obj = Course.objects.filter(id=course).first()
        user_obj = User.objects.filter(number=data["user"]).first()
        day_obj = Days.objects.filter(id=data["day"]).first()
        start_day_obj = Day.objects.filter(id=data["startDay"]).select_related('month', 'month__year').first()
        session_obj = Session.objects.filter(id=data["session"]).first()

        if not all([course_obj, user_obj, day_obj, start_day_obj, session_obj]):
            return Response({
                'error': 'برخی از داده‌ها نامعتبر هستند.',
                'debug': {
                    'course': bool(course_obj),
                    'user': bool(user_obj),
                    'day': bool(day_obj),
                    'startDay': bool(start_day_obj),
                    'session': bool(session_obj),
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # normalize روزها
        day_names = [normalize_persian_text(d) for d in day_obj.title.split("،")]

        participant_data = {
            'description': data.get("description", ""),
            'startDay': start_day_obj.id,
            'session': session_obj.id,
            'day': day_obj.id,
            'price': data["price"],
            'user': user_obj.id,
            'course': course_obj.id,
            'success': True,
            'created': request.user.id
        }

        serializer = self.serializer_class(data=participant_data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()  # endDay توسط مدل محاسبه می‌شود
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'ولیدیشن ناموفق', 'details': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            participant = Participants.objects.get(pk=pk)
        except Participants.DoesNotExist:
            return Response({'error': 'موردی با این شناسه پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data

        # Mapping فیلدهای ForeignKey به مدلشون
        fk_fields = {
            'user': User,
            'course': Course,
            'day': Days,
            'session': Session,
            'startDay': Day
        }

        for field, value in data.items():
            if field in fk_fields:
                # گرفتن آبجکت
                obj = fk_fields[field].objects.filter(id=value).first() if field != 'user' else fk_fields[
                    field].objects.filter(number=value).first()
                if not obj:
                    return Response({'error': f'{field} نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)
                setattr(participant, field, obj)
            else:
                setattr(participant, field, value)

        participant.save()  # endDay خودش توسط مدل محاسبه می‌شود
        serializer = self.serializer_class(participant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk):
        try:
            participant = Participants.objects.get(pk=pk)
            participant.delete()
            return Response({'status': 'Deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Participants.DoesNotExist:
            return Response({'error': 'موردی با این شناسه پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

class ChangeDayPriceView(UpdateAPIView):
    serializer_class = ChangeDayPriceSerializer
    permission_classes = [IsAdminUserOrStaff]

    def get_object(self):
        day_id = self.kwargs['day_id']
        try:
            return Days.objects.get(id=day_id)
        except Days.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        day = self.get_object()
        if day is None:
            return Response({"detail": "day not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(day, data=request.data)  # اضافه کردن partial=True برای بروزرسانی جزئی
        serializer.is_valid(raise_exception=True)
        serializer.save()  # از متد save سریالایزر استفاده می‌کنیم

        return Response({"detail": "قیمت با موفقیت بروزرسانی شد"}, status=status.HTTP_200_OK)


class OfferView(viewsets.ViewSet):
    serializer_class = OfferSerializer
    permission_classes = [IsAdminUserOrStaff]

    def create(self, request):
        data = request.data

        offer_data = {
            'type': data['type'],
            'product': data['product'],
            'session': data['session'],
            'off': data['off']

        }

        try:
            # Filter Days objects based on the conditions
            if data['type'] == 'SPORT':
                if data['session'] == 0:
                    eligible_days = Days.objects.filter(
                        session__course__sport=data['product']
                    )
                else:
                    eligible_days = Days.objects.filter(
                        session__number=data['session'],
                        session__course__sport=data['product']
                    )
            elif data['type'] == 'COURSE':
                if data['session'] == 0:
                    eligible_days = Days.objects.filter(
                        session__course=data['product']
                    )
                else:
                    eligible_days = Days.objects.filter(
                        session__number=data['session'],
                        session__course=data['product']
                    )

            else:
                if data['session'] == 0:
                    eligible_days = Days.objects.all()
                else:
                    eligible_days = Days.objects.filter(
                        session__number=data['session'],
                    )

            # Apply 15% discount to eligible Days
            updated_count = eligible_days.update(off=data['off'])

            serializer = self.serializer_class(data=offer_data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()

            return Response(updated_count, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "error": "An error occurred while applying the discount.",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk):
        try:
            offer = Offers.objects.get(pk=pk)
            offer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Participants.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class UpdateAllParticipantsDaysAPIView(UpdateAPIView):
    serializer_class = UpdateDaySerializer

    def update(self, request, *args, **kwargs):
        serializer = UpdateDaySerializer(data=request.data)
        if serializer.is_valid():
            start_day = serializer.validated_data['startDay']
            end_day = serializer.validated_data['endDay']

            # به‌روزرسانی تمام رکوردهای Participants
            Participants.objects.filter(user__is_teacher=True).update(startDay=start_day, endDay=end_day)

            return Response(
                {"message": "All participants updated successfully!"},
                status=status.HTTP_200_OK,
            )

        # در صورت وجود خطا در داده‌های ورودی
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def update_expired_participants(pk):
    participants_qs = Participants.objects.filter(course_id=pk)

    for p in participants_qs:
        if p.endDay and p.endDay.month and p.endDay.month.year:
            end_date = jdatetime.date(
                p.endDay.month.year.number,
                p.endDay.month.number,
                p.endDay.number
            )
            if end_date < jdatetime.date.today():
                p.expired = True
                p.save(update_fields=["expired"])
            else:
                p.expired = False
                p.save(update_fields=["expired"])

