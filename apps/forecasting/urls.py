"""
URL Configuration for Forecasting API
"""

from django.urls import path
from . import views

app_name = 'forecasting'

urlpatterns = [
    path('forecast/', views.generate_forecast, name='generate_forecast'),
    path('risk-analysis/', views.get_risk_analysis, name='risk_analysis'),
    path('recommendations/', views.get_recommendations, name='recommendations'),
    path('product/<str:sku>/', views.get_product_details, name='product_details'),
]