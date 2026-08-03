import os
import sys

# Point to your project root
sys.path.insert(0, os.path.dirname(__file__))

# Redirect error logs to a file we can read in File Manager
sys.stderr = open(os.path.join(os.path.dirname(__file__), 'passenger_stderr.log'), 'a')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'palkay.settings_production')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
