from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.http import HttpResponse
from api.wsclient import ws_client

# Create your views here.

# This is a little complex because we need to detect when we are
# running in various configurations

class HomeView(View):
    def get(self, request):
        ws_client('stop')       # stop market websocket client
        print("Host: ", request.get_host())
        host = request.get_host()
        islocal = host.find('localhost') >= 0 or host.find('127.0.0.1') >= 0
        context = {
            'installed': settings.INSTALLED_APPS,
            'islocal': islocal
        }
        return render(request, 'vanilla/index.html', context)


def hello(request):
    return HttpResponse("Hello, world. d3bc3878 is the polls index.")

