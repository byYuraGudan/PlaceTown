from django.shortcuts import redirect


def base(request):
    return redirect('/admin/')
