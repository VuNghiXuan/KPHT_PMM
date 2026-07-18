from celery import Celery
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NexusChat.settings')
app = Celery('vnxChatBot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()