from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.views import RegisterViewSet
from apps.users.jwt_users import RateLimitedTokenObtainPairView

from rest_framework_simplejwt.views import TokenRefreshView

from apps.blog.urls import router as blog_router 

auth_router = DefaultRouter()
auth_router.register(r"auth/register", RegisterViewSet, basename="register")

urlpatterns = [
    path("api/", include(auth_router.urls)),
    path(
        "api/auth/token/",
        RateLimitedTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include(blog_router.urls)),
]
