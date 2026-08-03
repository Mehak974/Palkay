import threading
from django.core.mail import send_mail

# ponytail: Using threading instead of celery for background emails to avoid extra worker processes. 
# Upgrade path: switch to celery/django-rq if we exceed 10+ emails/sec.

def send_mail_background(subject, message, from_email, recipient_list, **kwargs):
    """Sends email in a background thread so it doesn't block the web request."""
    thread = threading.Thread(
        target=send_mail,
        args=(subject, message, from_email, recipient_list),
        kwargs=kwargs
    )
    thread.daemon = True
    thread.start()
