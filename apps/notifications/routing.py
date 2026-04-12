from django.urls import re_path

from apps.blog.consumers import CommentConsumer

websocket_urlpatterns = [
    re_path(r"^ws/posts/(?P<slug>[-\w]+)/comments/$", CommentConsumer.as_asgi()),
]
