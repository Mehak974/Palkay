import os
import sys

# Point to your project root
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palkay.settings_production')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
