from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PostViewSet, post_stream

router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="posts")


urlpatterns = [
    path("posts/stream/", post_stream, name="posts-stream"),
]
