import sys
from django.views.debug import technical_500_response


class AdminDebugMiddleware:
    """
    Show Django's detailed technical error page to logged-in admins,
    even when DEBUG=False. Regular users see the friendly 500 page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Only show detailed traces to verified admin sessions (not just any
        # logged-in customer who happens to have a "name" in their session).
        if request.session.get("is_admin") is True:
            return technical_500_response(request, *sys.exc_info())
        return None
