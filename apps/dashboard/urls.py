"""
Dashboard URL Configuration
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('overview/', views.executive_overview, name='overview'),
    path('forecasts/', views.forecast_explorer, name='forecasts'),
    path('risk-monitor/', views.risk_monitor, name='risk-monitor'),
    path('recommendations/', views.recommendations, name='recommendations'),
    
    # Chart API endpoints
    path('api/revenue-trend/', views.api_revenue_trend, name='api-revenue-trend'),
    path('api/risk-distribution/', views.api_risk_distribution, name='api-risk-distribution'),
    path('api/product-forecast/<str:sku>/', views.api_product_forecast, name='api-product-forecast'),
]