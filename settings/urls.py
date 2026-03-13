from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.users.views import RegisterViewSet
from apps.users.jwt_users import (
    RateLimitedTokenObtainPairView,
    DocumentedTokenRefreshView,
)

from apps.blog.urls import router as blog_router

auth_router = DefaultRouter()
auth_router.register(r"auth/register", RegisterViewSet, basename="register")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include(auth_router.urls)),
    path("api/auth/", include("apps.users.urls")),
    path(
        "api/auth/token/",
        RateLimitedTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/auth/token/refresh/",
        DocumentedTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("api/", include(blog_router.urls)),
    path("api/", include("apps.stats.urls")),
]
