from django.conf import settings
from django.utils import translation, timezone
from django.utils.deprecation import MiddlewareMixin


class UserLocaleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        supported_languages = {code for code, _ in settings.LANGUAGES}
        language = None

        user = getattr(request, "user", None)

        if user and user.is_authenticated and getattr(user, "preferred_language", None):
            language = user.preferred_language
        elif request.GET.get("lang"):
            language = request.GET.get("lang")
        else:
            header = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
            if header:
                raw_languages = [
                    item.split(";")[0].strip() for item in header.split(",")
                ]
                for item in raw_languages:
                    short = item[:2].lower()
                    if short in supported_languages:
                        language = short
                        break

        if language not in supported_languages:
            language = settings.LANGUAGE_CODE

        translation.activate(language)
        request.LANGUAGE_CODE = language

        if user and user.is_authenticated and getattr(user, "timezone", None):
            timezone.activate(user.timezone)
        else:
            timezone.activate("UTC")

    def process_response(self, request, response):
        translation.deactivate()
        timezone.deactivate()
        return response
