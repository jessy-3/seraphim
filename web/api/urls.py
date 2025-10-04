#coding=utf8
from django.urls import path, include, re_path
from . import views

'''
from rest_framework import routers
router = routers.DefaultRouter()
router.register(r'getResponse', getResponse)
router.register(r'setMessage', setMessage)
router.register(r'setCounter', setCounter)
'''
urlpatterns = [
    path('student', views.Student.as_view(), name="sendemail"),
    path('ohlc/<str:symboluri>', views.Ohlc.as_view(), name='ohlc_lastday'),
    path('ohlc/<str:symboluri>/<str:pdt>', views.Ohlc.as_view(), name='ohlc_bydate'),
    path('ticker/<str:symboluri>', views.Ticker.as_view(), name='current'),
    path('getResponse', views.getResponse, name='getResponse'),
    path('setMessage', views.setMessage, name='setMessage'),
    path('setCounter', views.setCounter, name='setCounter'),
    #    re_path(r'^test1/$', views.schema_view, name="schema_view"),
]