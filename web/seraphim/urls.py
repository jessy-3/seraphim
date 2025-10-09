"""
Seraphim Crypto & Stock Trading System URL Configuration

The `urlpatterns` list routes URLs to views.
"""
import os
from django.urls import path, include, re_path
from django.contrib import admin
from seraphim import views
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

urlpatterns = [
    # Authentication
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Main application routes
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('api/market-data/', views.MarketDataView.as_view(), name='market-data'),
    path('api/market-regime/', views.MarketRegimeView.as_view(), name='market-regime'),
    path('api/trading-signals/', views.TradingSignalsView.as_view(), name='trading-signals'),
    path('api/trading-signals/<int:signal_id>/', views.TradingSignalDetailView.as_view(), name='trading-signal-detail'),
    path('api/', include('api.urls')),
    path('trading/', include('trading.urls')),
    
    # Admin
    path('admin/', admin.site.urls),
]

# Static files
urlpatterns += [
    path('favicon.ico', serve, {
            'path': 'favicon.ico',
            'document_root': os.path.join(BASE_DIR, '/web/static'),
        }
    ),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)