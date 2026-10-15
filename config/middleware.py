from django.http import HttpResponse
from django.shortcuts import redirect
from services import auth

OPEN = ('/login/', '/static/')


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(OPEN) or auth.is_logged_in(request.session):
            return self.get_response(request)
        if request.headers.get('HX-Request') == 'true':
            resp = HttpResponse(status=200)
            resp['HX-Redirect'] = '/login/'
            return resp
        return redirect('/login/')