from django.urls import path
from .views import UpdateLanguageView, UpdateTimezoneView

urlpatterns = [
    path("language/", UpdateLanguageView.as_view(), name="update-language"),
    path("timezone/", UpdateTimezoneView.as_view(), name="update-timezone"),
]
