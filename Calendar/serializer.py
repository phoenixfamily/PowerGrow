from rest_framework import serializers
from Calendar.models import *
from Reservation.serializer import ReservationSerializer

class TimeSerializer(serializers.ModelSerializer):
    reservations = ReservationSerializer(read_only=True, many=True)

    class Meta:
        model = Time
        read_only_fields = ['res_id']
        fields = "__all__"




class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ['number']

class DaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Day
        fields = ['id', 'number', 'name', 'description', 'holiday']

class MonthSerializer(serializers.ModelSerializer):
    year = YearSerializer()
    days = DaySerializer(many=True, read_only=True)
    start_weekday = serializers.SerializerMethodField()


    class Meta:
        model = Month
        fields = ['id', 'name', 'number', 'max', 'year', 'days', 'start_weekday']

    def get_start_weekday(self, obj):
        return obj.start_weekday



class ChangeCostSerializer(serializers.ModelSerializer):
    all = serializers.BooleanField()

    class Meta:
        model = Time
        model_fields = ['price', 'off']
        extra_fields = ['all']
        fields = model_fields + extra_fields


class ChangeDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Day
        fields = ['description', 'holiday', 'name']

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.holiday = validated_data.get("holiday", instance.holiday)
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        return instance
