"""
Fashion Inventory Intelligence - API Views
Connects ML engine to Django REST endpoints
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import pandas as pd
import sys
import os

# Add ml_engine to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE_DIR, 'ml_engine'))

from ml_engine.models import SalesForecastModel, MultiProductForecaster
from ml_engine.risk_calculator import InventoryHealthAnalyzer
from ml_engine.trend_analyzer import TrendAnalyzer

from apps.inventory.models import (
    Product, SalesHistory, InventoryLevel, 
    Prediction, RiskAlert
)


@api_view(['POST'])
def generate_forecast(request):
    """
    Generate sales forecast for specified product(s)
    
    POST /api/forecast/
    Body: {
        "product_id": "SKU00001",  // or
        "product_ids": ["SKU00001", "SKU00002"],  // for multiple
        "periods": 30  // optional, defaults to 30
    }
    
    Returns:
        {
            "status": "success",
            "forecasts": [
                {
                    "product_id": "SKU00001",
                    "total_predicted_units": 120.5,
                    "avg_daily_units": 4.02,
                    "confidence_score": 0.75,
                    "forecast_start": "2026-01-30",
                    "forecast_end": "2026-02-28",
                    "daily_forecast": [...]
                }
            ]
        }
    """
    try:
        # Get parameters
        product_id = request.data.get('product_id')
        product_ids = request.data.get('product_ids', [])
        periods = request.data.get('periods', 30)
        
        # Determine which products to forecast
        if product_id:
            product_ids = [product_id]
        
        if not product_ids:
            return Response({
                'status': 'error',
                'message': 'Please provide product_id or product_ids'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get sales data from database
        sales_data = SalesHistory.objects.filter(
            product__sku__in=product_ids
        ).values('date', 'product__sku', 'units_sold')
        
        if not sales_data:
            return Response({
                'status': 'error',
                'message': 'No sales data found for specified products'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Convert to DataFrame
        df = pd.DataFrame(sales_data)
        df.rename(columns={'product__sku': 'product_id'}, inplace=True)
        
        # Generate forecasts
        forecasts = []
        
        for sku in product_ids:
            try:
                # Train model
                model = SalesForecastModel()
                model.train(df, sku)
                
                # Get forecast
                forecast = model.predict(periods=periods)
                summary = model.get_forecast_summary(periods=periods)
                
                # Save predictions to database
                product = Product.objects.get(sku=sku)
                for _, row in forecast.iterrows():
                    Prediction.objects.update_or_create(
                        product=product,
                        forecast_date=row['date'],
                        defaults={
                            'predicted_units': row['predicted_sales'],
                            'lower_bound': row['lower_bound'],
                            'upper_bound': row['upper_bound'],
                            'confidence_score': row['confidence_score'],
                            'model_version': 'v1.0'
                        }
                    )
                
                forecasts.append({
                    'product_id': sku,
                    'product_name': product.product_name,
                    **summary,
                    'daily_forecast': forecast.to_dict('records')
                })
                
            except Exception as e:
                forecasts.append({
                    'product_id': sku,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return Response({
            'status': 'success',
            'count': len(forecasts),
            'forecasts': forecasts
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_risk_analysis(request):
    """
    Get inventory risk analysis for products
    
    GET /api/risk-analysis/?category=Tops&risk_level=high
    
    Query Parameters:
        - category: Filter by product category
        - risk_level: Filter by risk level (high/medium/low)
        - limit: Number of results (default: 100)
    
    Returns:
        {
            "status": "success",
            "summary": {
                "total_products": 100,
                "high_risk_products": 20,
                "high_risk_percentage": 20.0,
                ...
            },
            "products": [...]
        }
    """
    try:
        # Get query parameters
        category = request.GET.get('category')
        risk_level = request.GET.get('risk_level')
        limit = int(request.GET.get('limit', 100))
        
        # Get data from database
        products_df = pd.DataFrame(
            Product.objects.all().values(
                'sku', 'product_name', 'category', 'season', 
                'subcategory', 'price'
            )
        )
        products_df.rename(columns={'sku': 'product_id'}, inplace=True)
        
        sales_df = pd.DataFrame(
            SalesHistory.objects.all().values('date', 'product__sku', 'units_sold')
        )
        sales_df.rename(columns={'product__sku': 'product_id'}, inplace=True)
        
        inventory_df = pd.DataFrame(
            InventoryLevel.objects.all().values(
                'product__sku', 'current_stock', 'last_restock_date'
            )
        )
        inventory_df.rename(columns={'product__sku': 'product_id'}, inplace=True)
        
        # Generate forecasts
        forecaster = MultiProductForecaster()
        forecaster.train_all(sales_df, products_df['product_id'].tolist()[:limit])
        forecast_df = forecaster.predict_all(periods=30)
        
        # Analyze inventory health
        analyzer = InventoryHealthAnalyzer()
        analysis = analyzer.analyze_inventory(
            inventory_df, sales_df, forecast_df, products_df
        )
        
        # Apply filters
        if category:
            analysis = analysis[analysis['category'] == category]
        
        if risk_level:
            level_map = {
                'high': 'High Risk',
                'medium': 'Medium Risk',
                'low': 'Low Risk'
            }
            analysis = analysis[analysis['risk_level'] == level_map.get(risk_level.lower())]
        
        # Save risk alerts to database
        for _, row in analysis.iterrows():
            try:
                product = Product.objects.get(sku=row['product_id'])
                
                # Map risk level
                risk_level_map = {
                    'High Risk': 'high',
                    'Medium Risk': 'medium',
                    'Low Risk': 'low'
                }
                
                velocity_map = {
                    'Fast Mover': 'fast',
                    'Medium Mover': 'medium',
                    'Slow Mover': 'slow'
                }
                
                RiskAlert.objects.create(
                    product=product,
                    risk_level=risk_level_map.get(row['risk_level'], 'low'),
                    overstock_risk_pct=row['overstock_risk_pct'],
                    velocity=velocity_map.get(row['velocity'], 'medium'),
                    recommended_action=row['recommended_action'],
                    urgency=row['urgency']
                )
            except Exception as e:
                print(f"Error saving risk alert for {row['product_id']}: {e}")
        
        # Get summary
        summary = analyzer.get_risk_summary(analysis)
        
        return Response({
            'status': 'success',
            'summary': summary,
            'count': len(analysis),
            'products': analysis.to_dict('records')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_recommendations(request):
    """
    Get action recommendations based on trends and risk
    
    GET /api/recommendations/?type=emerging
    
    Query Parameters:
        - type: emerging/declining/all (default: all)
        - limit: Number of results (default: 20)
    
    Returns:
        {
            "status": "success",
            "emerging_trends": [...],
            "declining_products": [...],
            "high_risk_alerts": [...]
        }
    """
    try:
        rec_type = request.GET.get('type', 'all')
        limit = int(request.GET.get('limit', 20))
        
        # Get data
        products_df = pd.DataFrame(
            Product.objects.all().values(
                'sku', 'product_name', 'category', 'season', 'launch_date'
            )
        )
        products_df.rename(columns={'sku': 'product_id'}, inplace=True)
        
        sales_df = pd.DataFrame(
            SalesHistory.objects.all().values('date', 'product__sku', 'units_sold')
        )
        sales_df.rename(columns={'product__sku': 'product_id'}, inplace=True)
        
        # Analyze trends
        analyzer = TrendAnalyzer()
        trend_df = analyzer.analyze_all_products(sales_df, products_df[:100])
        
        # Get recommendations
        recommendations = {
            'emerging_trends': [],
            'declining_products': [],
            'high_risk_alerts': []
        }
        
        if rec_type in ['emerging', 'all']:
            emerging = trend_df[
                trend_df['trend_classification'] == 'Emerging'
            ].head(limit)
            
            for _, row in emerging.iterrows():
                insight = analyzer.generate_trend_insight({
                    'trend_score': row['trend_score'],
                    'sales_acceleration_pct': row['sales_acceleration_pct']
                })
                
                recommendations['emerging_trends'].append({
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'trend_score': row['trend_score'],
                    'sales_growth': f"{row['sales_acceleration_pct']:.1f}%",
                    'recommendation': insight['recommendation'],
                    'urgency': insight['urgency']
                })
        
        if rec_type in ['declining', 'all']:
            declining = trend_df[
                trend_df['trend_classification'] == 'Declining'
            ].head(limit)
            
            for _, row in declining.iterrows():
                insight = analyzer.generate_trend_insight({
                    'trend_score': row['trend_score'],
                    'sales_acceleration_pct': row['sales_acceleration_pct']
                })
                
                recommendations['declining_products'].append({
                    'product_id': row['product_id'],
                    'product_name': row['product_name'],
                    'trend_score': row['trend_score'],
                    'sales_change': f"{row['sales_acceleration_pct']:.1f}%",
                    'recommendation': insight['recommendation'],
                    'urgency': insight['urgency']
                })
        
        # Get high-risk alerts from database
        if rec_type == 'all':
            recent_alerts = RiskAlert.objects.filter(
                is_resolved=False,
                risk_level='high'
            ).select_related('product')[:limit]
            
            for alert in recent_alerts:
                recommendations['high_risk_alerts'].append({
                    'product_id': alert.product.sku,
                    'product_name': alert.product.product_name,
                    'risk_level': alert.risk_level,
                    'overstock_risk': f"{alert.overstock_risk_pct:.1f}%",
                    'velocity': alert.velocity,
                    'recommendation': alert.recommended_action,
                    'urgency': alert.urgency
                })
        
        return Response({
            'status': 'success',
            'recommendations': recommendations
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_product_details(request, sku):
    """
    Get complete intelligence for a single product
    
    GET /api/product/<sku>/
    
    Returns:
        Complete product intelligence including forecast, risk, and trends
    """
    try:
        product = get_object_or_404(Product, sku=sku)
        
        # Get latest forecast
        latest_forecast = Prediction.objects.filter(
            product=product
        ).order_by('-created_at')[:30]
        
        # Get risk alerts
        latest_alert = RiskAlert.objects.filter(
            product=product
        ).order_by('-created_at').first()
        
        # Get sales history (last 90 days)
        recent_sales = SalesHistory.objects.filter(
            product=product
        ).order_by('-date')[:90]
        
        # Get inventory
        inventory = InventoryLevel.objects.filter(product=product).first()
        
        return Response({
            'status': 'success',
            'product': {
                'sku': product.sku,
                'name': product.product_name,
                'category': product.category,
                'price': float(product.price),
                'season': product.season
            },
            'inventory': {
                'current_stock': inventory.current_stock if inventory else 0,
                'warehouse': inventory.warehouse_location if inventory else None,
                'days_in_inventory': inventory.days_in_inventory if inventory else None
            },
            'forecast': [
                {
                    'date': str(f.forecast_date),
                    'predicted_units': f.predicted_units,
                    'confidence': f.confidence_score
                }
                for f in latest_forecast
            ],
            'risk': {
                'level': latest_alert.risk_level if latest_alert else 'unknown',
                'overstock_pct': latest_alert.overstock_risk_pct if latest_alert else 0,
                'velocity': latest_alert.velocity if latest_alert else 'unknown',
                'recommendation': latest_alert.recommended_action if latest_alert else None
            } if latest_alert else None,
            'recent_sales': [
                {
                    'date': str(s.date),
                    'units_sold': s.units_sold,
                    'revenue': float(s.revenue)
                }
                for s in recent_sales
            ]
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)