#coding=utf8
from django.urls import path, include, re_path
from . import views

app_name = "trading"

urlpatterns = [
    path('', views.TradingListView.as_view(), name='tl_listing'),

    #    re_path(r'^test1/$', views.schema_view, name="schema_view"),
]