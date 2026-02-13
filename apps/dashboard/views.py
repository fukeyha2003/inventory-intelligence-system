"""
Dashboard Views - Fashion Inventory Intelligence
Real-time KPIs, forecasts, risk monitoring, and recommendations
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, Q
from datetime import datetime, timedelta
import pandas as pd

from apps.inventory.models import (
    Product, SalesHistory, InventoryLevel, 
    Prediction, RiskAlert
)


# ============================================================================
# HOME PAGE (Keep this - it's your homepage!)
# ============================================================================

def home(request):
    """Homepage with system overview"""
    context = {
        'total_products': Product.objects.count(),
        'total_sales': SalesHistory.objects.count(),
        'total_predictions': Prediction.objects.count(),
        'high_risk_alerts': RiskAlert.objects.filter(
            risk_level='high', 
            is_resolved=False
        ).count(),
    }
    return render(request, 'dashboard/home.html', context)


# ============================================================================
# DASHBOARD PAGES (New functions - add these!)
# ============================================================================

def executive_overview(request):
    """
    KPI dashboard with charts
    Shows: Revenue trends, inventory health, forecast accuracy, alerts
    """
    # Date ranges
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # KPI calculations
    total_products = Product.objects.count()
    total_inventory = InventoryLevel.objects.aggregate(
        total=Sum('current_stock')
    )['total'] or 0
    
    # Recent sales
    recent_sales = SalesHistory.objects.filter(
        date__gte=last_30_days
    ).aggregate(
        total_revenue=Sum('revenue'),
        total_units=Sum('units_sold')
    )
    
    # Risk breakdown
    risk_summary = RiskAlert.objects.filter(
        is_resolved=False
    ).values('risk_level').annotate(
        count=Count('id')
    )
    
    risk_counts = {
        'high': 0,
        'medium': 0,
        'low': 0
    }
    for item in risk_summary:
        risk_counts[item['risk_level']] = item['count']
    
    # Velocity breakdown
    velocity_summary = RiskAlert.objects.filter(
        is_resolved=False
    ).values('velocity').annotate(
        count=Count('id')
    )
    
    velocity_counts = {
        'fast': 0,
        'medium': 0,
        'slow': 0
    }
    for item in velocity_summary:
        velocity_counts[item['velocity']] = item['count']
    
    # Recent predictions
    recent_forecasts = Prediction.objects.filter(
        created_at__gte=last_7_days
    ).count()
    
    # Forecast confidence
    avg_confidence = Prediction.objects.filter(
        created_at__gte=last_30_days
    ).aggregate(
        avg=Avg('confidence_score')
    )['avg'] or 0
    
    context = {
        'total_products': total_products,
        'total_inventory': total_inventory,
        'revenue_30d': recent_sales['total_revenue'] or 0,
        'units_sold_30d': recent_sales['total_units'] or 0,
        'high_risk_count': risk_counts['high'],
        'medium_risk_count': risk_counts['medium'],
        'low_risk_count': risk_counts['low'],
        'fast_movers': velocity_counts['fast'],
        'slow_movers': velocity_counts['slow'],
        'recent_forecasts': recent_forecasts,
        'avg_confidence': round(avg_confidence * 100, 1),
    }
    
    return render(request, 'dashboard/overview.html', context)


def forecast_explorer(request):
    """Interactive forecast visualization"""
    category = request.GET.get('category')
    product_id = request.GET.get('product_id')
    
    products_query = Product.objects.all()
    
    if category:
        products_query = products_query.filter(category=category)
    
    products_with_forecasts = products_query.filter(
        predictions__isnull=False
    ).distinct()[:50]
    
    categories = Product.objects.values_list('category', flat=True).distinct()
    
    context = {
        'products': products_with_forecasts,
        'categories': categories,
        'selected_category': category,
        'selected_product': product_id,
    }
    
    return render(request, 'dashboard/forecasts.html', context)


def risk_monitor(request):
    """Real-time risk assessment board"""
    risk_level = request.GET.get('risk_level', 'all')
    urgency = request.GET.get('urgency')
    
    alerts_query = RiskAlert.objects.filter(
        is_resolved=False
    ).select_related('product').order_by('-overstock_risk_pct')
    
    if risk_level != 'all':
        alerts_query = alerts_query.filter(risk_level=risk_level)
    
    if urgency:
        alerts_query = alerts_query.filter(urgency=urgency)
    
    alerts = alerts_query[:100]
    
    total_alerts = alerts_query.count()
    critical_alerts = alerts_query.filter(urgency='Critical').count()
    high_urgency = alerts_query.filter(urgency='High').count()
    
    category_risks = alerts_query.values(
        'product__category'
    ).annotate(
        count=Count('id'),
        avg_risk=Avg('overstock_risk_pct')
    ).order_by('-avg_risk')[:10]
    
    context = {
        'alerts': alerts,
        'total_alerts': total_alerts,
        'critical_alerts': critical_alerts,
        'high_urgency': high_urgency,
        'category_risks': category_risks,
        'selected_risk_level': risk_level,
        'selected_urgency': urgency,
    }
    
    return render(request, 'dashboard/risk_monitor.html', context)


def recommendations(request):
    """Action recommendations dashboard"""
    alerts_qs = (
        RiskAlert.objects
        .filter(is_resolved=False)
        .select_related('product')
        .order_by('-created_at')
    )

    critical_actions = alerts_qs.filter(urgency='Critical')
    high_priority = alerts_qs.filter(urgency='High')
    medium_priority = alerts_qs.filter(urgency='Medium')

    context = {
        'critical_actions': critical_actions,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'total_recommendations': alerts_qs.count(),
    }

    return render(request, 'dashboard/recommendations.html', context)



# ============================================================================
# AJAX API ENDPOINTS FOR CHARTS
# ============================================================================

def api_revenue_trend(request):
    """Revenue trend data for Chart.js"""
    days = int(request.GET.get('days', 30))
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    daily_data = SalesHistory.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).values('date').annotate(
        revenue=Sum('revenue'),
        units=Sum('units_sold')
    ).order_by('date')
    
    labels = [str(item['date']) for item in daily_data]
    revenue_data = [float(item['revenue']) for item in daily_data]
    units_data = [item['units'] for item in daily_data]
    
    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Revenue ($)',
                'data': revenue_data,
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            },
            {
                'label': 'Units Sold',
                'data': units_data,
                'borderColor': 'rgb(153, 102, 255)',
                'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                'yAxisID': 'y1',
            }
        ]
    })


def api_product_forecast(request, sku):
    """Forecast data for specific product"""
    try:
        product = Product.objects.get(sku=sku)
        
        forecasts = Prediction.objects.filter(
            product=product,
            forecast_date__gte=datetime.now().date()
        ).order_by('forecast_date')[:30]
        
        if not forecasts:
            return JsonResponse({'error': 'No forecasts found'}, status=404)
        
        labels = [str(f.forecast_date) for f in forecasts]
        predicted = [f.predicted_units for f in forecasts]
        lower = [f.lower_bound for f in forecasts]
        upper = [f.upper_bound for f in forecasts]
        
        return JsonResponse({
            'product_name': product.product_name,
            'labels': labels,
            'datasets': [
                {
                    'label': 'Predicted Sales',
                    'data': predicted,
                    'borderColor': 'rgb(54, 162, 235)',
                    'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                    'fill': False,
                },
                {
                    'label': 'Upper Bound',
                    'data': upper,
                    'borderColor': 'rgba(54, 162, 235, 0.3)',
                    'borderDash': [5, 5],
                    'fill': '+1',
                    'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                },
                {
                    'label': 'Lower Bound',
                    'data': lower,
                    'borderColor': 'rgba(54, 162, 235, 0.3)',
                    'borderDash': [5, 5],
                    'fill': False,
                }
            ]
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


def api_risk_distribution(request):
    """Risk distribution by category for pie chart"""
    category_data = RiskAlert.objects.filter(
        is_resolved=False,
        risk_level='high'
    ).values('product__category').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    labels = [item['product__category'] for item in category_data]
    data = [item['count'] for item in category_data]
    
    colors = [
        'rgb(255, 99, 132)',
        'rgb(54, 162, 235)',
        'rgb(255, 206, 86)',
        'rgb(75, 192, 192)',
        'rgb(153, 102, 255)',
        'rgb(255, 159, 64)',
        'rgb(199, 199, 199)',
        'rgb(83, 102, 255)',
        'rgb(255, 99, 255)',
        'rgb(99, 255, 132)',
    ]
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors[:len(data)],
        }]
    })
def api_documentation(request):
    """API documentation page"""
    return render(request, 'dashboard/api_docs.html')