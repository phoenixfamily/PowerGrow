from rest_framework import serializers

from .models import *


class ManagerParticipantsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participants
        fields = [
            'id',
            'description',
            'session',
            'day',
            'startDay',
            'price',
            'user',
            'course',
            'success',
            'created',
        ]



class ParticipantsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participants
        fields = ['description', 'startDay', 'session', 'day', 'price', 'user', 'course',
                  'authority', 'success']


class DaysSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)  # فقط برای read
    participants = ParticipantsSerializer(read_only=True, many=True)


    class Meta:
        model = Days
        fields = ['id', 'title', 'days', 'active', 'tuition', 'off', 'session', 'participants']


class SessionSerializer(serializers.ModelSerializer):
    days = DaysSerializer(read_only=True, many=True)
    participants = ParticipantsSerializer(read_only=True, many=True)

    class Meta:
        model = Session
        fields = "__all__"

    def create(self, validated_data):
        return Session.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.number = validated_data.get('number', instance.number)
        instance.active = validated_data.get('active', instance.active)
        instance.course = validated_data.get('course', instance.course)
        instance.save()
        return instance


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ['datetime']

    def create(self, validated_data):
        return Course.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # در صورتی که بخوای لاگ بزاری یا چیزی خاصی بعد از آپدیت انجام بدی، اینجا می‌تونی بنویسی
        return super().update(instance, validated_data)



class SportSerializer(serializers.ModelSerializer):
    courses = CourseSerializer(read_only=True, many=True)

    class Meta:
        model = Sport
        fields = "__all__"

    def create(self, validated_data):
        return Sport.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.save()
        return instance


class ChangeDayPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Days
        fields = ('tuition', 'off')  # می‌توانید فیلدهای دلخواه را اضافه کنید

    def update(self, instance, validated_data):
        instance.tuition = validated_data.get('tuition', instance.tuition)
        instance.off = validated_data.get('off', instance.off)
        instance.save()
        return instance


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offers
        fields = [
            'id',  # شناسه
            'type',  # توضیحات
            'product',  # جلسه
            'session',  # روز
            'off',  # روز شروع
        ]

    def create(self, validated_data):
        return Offers.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.type = validated_data.get('type', instance.type)
        instance.product = validated_data.get('product', instance.product)
        instance.session = validated_data.get('session', instance.session)
        instance.off = validated_data.get('off', instance.off)

        instance.save()
        return instance


class UpdateDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Participants
        fields = ['startDay', 'endDay']

    def validate(self, attrs):
        start_day = attrs.get('startDay')
        end_day = attrs.get('endDay')

        return attrs

    def update(self, instance, validated_data):
        instance.startDay = validated_data.get('startDay', instance.startDay)
        instance.endDay = validated_data.get('endDay', instance.endDay)
        instance.save()

        return instance
