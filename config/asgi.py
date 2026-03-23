import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path, re_path
from api.consumers import ProjectConsumer

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': URLRouter([
        re_path(r'ws/projects/(?P<project_id>[^/]+)/?$', ProjectConsumer.as_asgi()),
    ]),
})
