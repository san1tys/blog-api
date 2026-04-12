import os

from django.core.asgi import get_asgi_application

from settings.conf import BLOG_ENV_ID

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{BLOG_ENV_ID}")


django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from settings.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
