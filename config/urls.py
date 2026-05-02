from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from apps.dashboard import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),

    # Auth - use our custom views
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # If anyone hits allauth URLs, redirect to homepage with modal
    path('accounts/login/', lambda r: redirect('/?show=login'), name='account_login'),
    path('accounts/signup/', lambda r: redirect('/?show=signup'), name='account_signup'),
    path('accounts/', include('allauth.urls')),  # Keep for other allauth features

    # API
    path('api/', views.api_documentation, name='api-docs'),
    path('', include('apps.forecasting.urls')),

    # Dashboard
    path('dashboard/', include('apps.dashboard.urls')),
]