import os
from django.urls import path, include, re_path
from api import consumers

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vanilla.settings')

websocket_urlpatterns = [
    path('ws/tick', consumers.TicksAsyncConsumer.as_asgi()),
]