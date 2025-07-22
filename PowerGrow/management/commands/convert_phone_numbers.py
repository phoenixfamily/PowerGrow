from django.core.management.base import BaseCommand
from User.models import User
from phonenumber_field.phonenumber import PhoneNumber

class Command(BaseCommand):
    help = 'Convert PhoneNumberField data to string for TextField'

    def handle(self, *args, **kwargs):
        updated = 0
        for profile in User.objects.all():
            if profile.number and isinstance(profile.number, PhoneNumber):
                profile.number = str(profile.number)  # تبدیل به رشته
                profile.save()
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully converted {updated} phone numbers to string.'))