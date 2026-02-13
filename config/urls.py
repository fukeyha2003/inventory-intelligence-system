"""
URL configuration for fashion_inventory_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

"""
Main URL Configuration
"""

"""
Main URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from apps.dashboard import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/', views.api_documentation, name='api-docs'),  # ← Add this!
    
    # API endpoints (without 'api/' prefix since it's already in forecasting.urls)
    path('', include('apps.forecasting.urls')),  # This adds /api/forecast/, etc.
    
    # Dashboard
    path('dashboard/', include('apps.dashboard.urls')),
]