import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palkay.settings_production')
django.setup()

from users.models import User

email = 'mehakiqbal974@gmail.com'
password = 'Palkay@2026'  # CHANGE THIS AFTER FIRST LOGIN

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print(f'Superuser {email} created successfully!')
else:
    print(f'User {email} already exists.')
