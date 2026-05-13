from django.urls import path
from . import views
from apps.dashboard import billing
app_name = 'dashboard'

urlpatterns = [
    path('overview/', views.executive_overview, name='overview'),
    path('forecasts/', views.forecast_explorer, name='forecasts'),
    path('risk-monitor/', views.risk_monitor, name='risk-monitor'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('upload/', views.upload_data, name='upload'),  # ← NEW

    # Upload endpoints
    path('upload/products/', views.upload_products_csv, name='upload-products'),
    path('upload/sales/', views.upload_sales_csv, name='upload-sales'),
    path('upload/inventory/', views.upload_inventory_csv, name='upload-inventory'),
    path('upload/generate/', views.generate_analysis, name='generate-analysis'),

    # Chart API endpoints
    path('api/revenue-trend/', views.api_revenue_trend, name='api-revenue-trend'),
    path('api/risk-distribution/', views.api_risk_distribution, name='api-risk-distribution'),
    path('api/product-forecast/<str:sku>/', views.api_product_forecast, name='api-product-forecast'),
     # Billing
    path('billing/upgrade/', billing.create_checkout_session, name='billing_upgrade'),
    path('billing/success/', billing.billing_success, name='billing_success'),
    path('billing/cancel/', billing.billing_cancel, name='billing_cancel'),
    path('billing/portal/', billing.customer_portal, name='billing_portal'),
    path('webhooks/stripe/', billing.stripe_webhook, name='stripe_webhook'),
]