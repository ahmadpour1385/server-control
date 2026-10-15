from django.http import HttpResponse
from django.shortcuts import render
from services import store


def page(request, sid):
    s = next((s for s in store.load()['servers'] if s['id'] == sid), None)
    if not s:
        return HttpResponse(status=404)
    return render(request, 'terminal/page.html', {'s': s})