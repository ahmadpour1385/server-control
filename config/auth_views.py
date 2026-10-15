from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from services import auth


def login_view(request):
    if auth.is_logged_in(request.session):
        return redirect('/')
    first = not auth.is_set()
    error = None
    if request.method == 'POST':
        pw = request.POST.get('password', '')
        if first:
            if len(pw) < 8 or pw != request.POST.get('password2', ''):
                error = 'پسورد باید حداقل ۸ کاراکتر باشه و دو بار یکسان وارد بشه'
            else:
                auth.set_password(pw)
                auth.unlock(pw)
                request.session['auth'] = auth.token()
                return redirect('/')
        elif auth.locked():
            error = 'چند بار اشتباه زدی، ۵ دقیقه صبر کن'
        elif auth.verify(pw):
            auth.unlock(pw)
            request.session['auth'] = auth.token()
            return redirect('/')
        else:
            auth.fail()
            error = 'پسورد اشتباهه'
    return render(request, 'login.html', {'first': first, 'error': error})


@require_POST
def logout_view(request):
    request.session.flush()
    return redirect('/login/')