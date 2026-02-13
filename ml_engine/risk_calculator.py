"""
Fashion Inventory Intelligence - Risk Calculator
Overstock detection and inventory health analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class InventoryRiskCalculator:
    """
    Calculate overstock risk, aging risk, and product velocity
    Based on formulas from the PDF documentation
    """
    
    def __init__(self):
        self.risk_thresholds = {
            'high': 40,      # > 40% = High Risk
            'medium': 15,    # 15-40% = Medium Risk
            'low': 0         # < 15% = Low Risk
        }
    
    def calculate_overstock_risk(self, current_stock, predicted_sales, safety_buffer_pct=0.20):
        """
        Calculate overstock risk percentage
        
        Formula: OverstockRisk = (CurrentStock - (PredictedSales + SafetyBuffer)) / CurrentStock * 100
        
        Args:
            current_stock: Current inventory units
            predicted_sales: Forecasted sales for period
            safety_buffer_pct: Safety buffer as percentage (default 20%)
            
        Returns:
            Risk percentage (0-100+)
        """
        if current_stock == 0:
            return 0.0
        
        safety_buffer = predicted_sales * safety_buffer_pct
        excess_inventory = current_stock - (predicted_sales + safety_buffer)
        
        risk_pct = (excess_inventory / current_stock) * 100
        
        return max(0.0, risk_pct)
    
    def calculate_aging_risk(self, days_in_inventory, category_avg_turnover=60, 
                            seasonality_factor=1.0):
        """
        Calculate inventory aging risk
        
        Formula: AgingRisk = (DaysInInventory / CategoryAvgTurnover) * SeasonalityFactor
        
        Args:
            days_in_inventory: Days since product arrived in stock
            category_avg_turnover: Average turnover period for category (days)
            seasonality_factor: Multiplier for seasonal relevance (1.0 = normal, >1.0 = declining season)
            
        Returns:
            Aging risk score (0-2+, where >1 means over average turnover period)
        """
        aging_risk = (days_in_inventory / category_avg_turnover) * seasonality_factor
        
        return aging_risk
    
    def classify_risk_level(self, risk_score):
        """
        Classify risk into High/Medium/Low
        
        Args:
            risk_score: Risk percentage (0-100+)
            
        Returns:
            Risk classification string
        """
        if risk_score >= self.risk_thresholds['high']:
            return 'High Risk'
        elif risk_score >= self.risk_thresholds['medium']:
            return 'Medium Risk'
        else:
            return 'Low Risk'
    
    def calculate_velocity(self, recent_sales, historical_avg_sales):
        """
        Calculate sales velocity classification
        
        Args:
            recent_sales: Recent period sales (e.g., last 30 days)
            historical_avg_sales: Historical average for same period
            
        Returns:
            Velocity classification: 'Fast Mover', 'Medium Mover', 'Slow Mover'
        """
        if historical_avg_sales == 0:
            velocity_ratio = 0
        else:
            velocity_ratio = recent_sales / historical_avg_sales
        
        if velocity_ratio >= 1.2:  # 20% above average
            return 'Fast Mover'
        elif velocity_ratio >= 0.8:  # Within 20% of average
            return 'Medium Mover'
        else:
            return 'Slow Mover'
    
    def get_recommended_action(self, risk_level, velocity, days_to_end_of_season=None):
        """
        Generate recommended action based on risk and velocity
        
        Args:
            risk_level: 'High Risk', 'Medium Risk', or 'Low Risk'
            velocity: 'Fast Mover', 'Medium Mover', or 'Slow Mover'
            days_to_end_of_season: Optional days until season ends
            
        Returns:
            Dictionary with recommended action
        """
        actions = {
            ('High Risk', 'Slow Mover'): {
                'action': 'Immediate aggressive discount (25-40%)',
                'urgency': 'Critical',
                'timeline': 'Within 1 week',
                'reason': 'High overstock with slow sales velocity'
            },
            ('High Risk', 'Medium Mover'): {
                'action': 'Moderate discount (15-25%) and promotional campaign',
                'urgency': 'High',
                'timeline': 'Within 2 weeks',
                'reason': 'Overstock risk despite moderate sales'
            },
            ('High Risk', 'Fast Mover'): {
                'action': 'Monitor closely, small discount (10-15%) if needed',
                'urgency': 'Medium',
                'timeline': 'Within 3-4 weeks',
                'reason': 'High stock but good sales velocity'
            },
            ('Medium Risk', 'Slow Mover'): {
                'action': 'Progressive discount strategy (15-25%)',
                'urgency': 'Medium',
                'timeline': 'Within 3-4 weeks',
                'reason': 'Moderate overstock with declining sales'
            },
            ('Medium Risk', 'Medium Mover'): {
                'action': 'Monitor inventory, prepare discount if needed',
                'urgency': 'Low',
                'timeline': 'Within 4-6 weeks',
                'reason': 'Manageable risk with stable sales'
            },
            ('Medium Risk', 'Fast Mover'): {
                'action': 'Maintain current strategy, consider reordering',
                'urgency': 'Low',
                'timeline': 'No immediate action',
                'reason': 'Stock levels appropriate for sales velocity'
            },
            ('Low Risk', 'Slow Mover'): {
                'action': 'Monitor sales trend, no discount needed yet',
                'urgency': 'Low',
                'timeline': 'Review in 4-6 weeks',
                'reason': 'Low overstock risk despite slow sales'
            },
            ('Low Risk', 'Medium Mover'): {
                'action': 'Optimal inventory level, maintain strategy',
                'urgency': 'None',
                'timeline': 'No action needed',
                'reason': 'Healthy inventory-to-sales ratio'
            },
            ('Low Risk', 'Fast Mover'): {
                'action': 'Consider increasing inventory allocation',
                'urgency': 'None',
                'timeline': 'Reorder within 2-3 weeks',
                'reason': 'Strong sales with low risk of overstock'
            }
        }
        
        return actions.get((risk_level, velocity), {
            'action': 'Review inventory strategy',
            'urgency': 'Medium',
            'timeline': 'Within 2 weeks',
            'reason': 'Standard monitoring required'
        })


class InventoryHealthAnalyzer:
    """
    Comprehensive inventory health analysis for entire catalog
    """
    
    def __init__(self):
        self.risk_calculator = InventoryRiskCalculator()
    
    def analyze_inventory(self, inventory_df, sales_df, forecast_df, products_df):
        """
        Perform complete inventory health analysis
        
        Args:
            inventory_df: Current inventory levels
            sales_df: Historical sales data
            forecast_df: Forecasted sales from ML model
            products_df: Product metadata
            
        Returns:
            DataFrame with risk analysis for all products
        """
        results = []
        
        for _, inv_row in inventory_df.iterrows():
            product_id = inv_row['product_id']
            current_stock = inv_row['current_stock']
            
            # Get forecast for this product
            product_forecast = forecast_df[forecast_df['product_id'] == product_id]
            
            if len(product_forecast) == 0:
                continue
            
            predicted_sales = product_forecast['total_predicted_units'].iloc[0]
            
            # Calculate days in inventory
            last_restock = pd.to_datetime(inv_row['last_restock_date'])
            days_in_inventory = (datetime.now() - last_restock).days
            
            # Get product metadata
            product_info = products_df[products_df['product_id'] == product_id]
            if len(product_info) == 0:
                continue
            
            category = product_info['category'].iloc[0]
            season = product_info['season'].iloc[0]
            
            # Calculate recent sales (last 30 days)
            recent_sales_df = sales_df[
                (sales_df['product_id'] == product_id) & 
                (pd.to_datetime(sales_df['date']) >= datetime.now() - timedelta(days=30))
            ]
            recent_sales = recent_sales_df['units_sold'].sum()
            
            # Calculate historical average (30-60 days ago)
            historical_sales_df = sales_df[
                (sales_df['product_id'] == product_id) & 
                (pd.to_datetime(sales_df['date']) >= datetime.now() - timedelta(days=60)) &
                (pd.to_datetime(sales_df['date']) < datetime.now() - timedelta(days=30))
            ]
            historical_avg = historical_sales_df['units_sold'].sum()
            
            # Calculate risk metrics
            overstock_risk = self.risk_calculator.calculate_overstock_risk(
                current_stock, predicted_sales
            )
            
            # Seasonality factor (higher if out of season)
            current_month = datetime.now().month
            season_match = self._check_season_match(season, current_month)
            seasonality_factor = 1.0 if season_match else 1.5
            
            aging_risk = self.risk_calculator.calculate_aging_risk(
                days_in_inventory, 
                category_avg_turnover=60,
                seasonality_factor=seasonality_factor
            )
            
            risk_level = self.risk_calculator.classify_risk_level(overstock_risk)
            
            velocity = self.risk_calculator.calculate_velocity(
                recent_sales, historical_avg if historical_avg > 0 else recent_sales
            )
            
            # Get recommended action
            recommendation = self.risk_calculator.get_recommended_action(
                risk_level, velocity
            )
            
            # Calculate sell-through rate
            sell_through_rate = (predicted_sales / current_stock * 100) if current_stock > 0 else 0
            
            results.append({
                'product_id': product_id,
                'product_name': product_info['product_name'].iloc[0],
                'category': category,
                'season': season,
                'current_stock': current_stock,
                'predicted_sales_30d': round(predicted_sales, 2),
                'recent_sales_30d': recent_sales,
                'overstock_risk_pct': round(overstock_risk, 2),
                'risk_level': risk_level,
                'aging_risk_score': round(aging_risk, 2),
                'velocity': velocity,
                'sell_through_rate_pct': round(sell_through_rate, 2),
                'days_in_inventory': days_in_inventory,
                'recommended_action': recommendation['action'],
                'urgency': recommendation['urgency'],
                'timeline': recommendation['timeline']
            })
        
        return pd.DataFrame(results)
    
    def _check_season_match(self, season, current_month):
        """Check if current month matches product season"""
        season_months = {
            'Winter': [11, 12, 1, 2],
            'Spring': [3, 4, 5],
            'Summer': [6, 7, 8],
            'Fall': [9, 10, 11]
        }
        
        return current_month in season_months.get(season, [])
    
    def get_risk_summary(self, analysis_df):
        """
        Get high-level summary of inventory risks
        
        Returns:
            Dictionary with summary statistics
        """
        total_products = len(analysis_df)
        high_risk = len(analysis_df[analysis_df['risk_level'] == 'High Risk'])
        medium_risk = len(analysis_df[analysis_df['risk_level'] == 'Medium Risk'])
        low_risk = len(analysis_df[analysis_df['risk_level'] == 'Low Risk'])
        
        fast_movers = len(analysis_df[analysis_df['velocity'] == 'Fast Mover'])
        slow_movers = len(analysis_df[analysis_df['velocity'] == 'Slow Mover'])
        
        total_stock_value = (analysis_df['current_stock'] * 
                             analysis_df['predicted_sales_30d']).sum()
        
        return {
            'total_products': total_products,
            'high_risk_products': high_risk,
            'medium_risk_products': medium_risk,
            'low_risk_products': low_risk,
            'high_risk_percentage': round(high_risk / total_products * 100, 2) if total_products > 0 else 0,
            'fast_movers_count': fast_movers,
            'slow_movers_count': slow_movers,
            'avg_sell_through_rate': round(analysis_df['sell_through_rate_pct'].mean(), 2),
            'products_requiring_immediate_action': high_risk
        }


if __name__ == '__main__':
    print("="*60)
    print("INVENTORY RISK ANALYSIS TEST")
    print("="*60)
    
    # Load data
    print("\n📂 Loading data...")
    sales_df = pd.read_csv('data/sales_history.csv')
    products_df = pd.read_csv('data/products.csv')
    inventory_df = pd.read_csv('data/inventory.csv')
    
    # Load forecasts (we need to generate these first)
    print("📊 Generating forecasts...")
    from models import MultiProductForecaster
    
    forecaster = MultiProductForecaster()
    forecaster.train_all(sales_df, products_df['product_id'].tolist()[:100], max_products=100)
    forecast_df = forecaster.predict_all(periods=30)
    
    # Analyze inventory
    print("\n🔍 Analyzing inventory health...")
    analyzer = InventoryHealthAnalyzer()
    analysis = analyzer.analyze_inventory(
        inventory_df.head(100),  # Analyze first 100 products
        sales_df,
        forecast_df,
        products_df
    )
    
    # Risk summary
    summary = analyzer.get_risk_summary(analysis)
    print("\n📊 INVENTORY HEALTH SUMMARY:")
    print(f"   Total Products Analyzed: {summary['total_products']}")
    print(f"   High Risk Products: {summary['high_risk_products']} ({summary['high_risk_percentage']}%)")
    print(f"   Medium Risk Products: {summary['medium_risk_products']}")
    print(f"   Low Risk Products: {summary['low_risk_products']}")
    print(f"   Fast Movers: {summary['fast_movers_count']}")
    print(f"   Slow Movers: {summary['slow_movers_count']}")
    print(f"   Avg Sell-Through Rate: {summary['avg_sell_through_rate']}%")
    
    # Show high-risk products
    print("\n🚨 HIGH RISK PRODUCTS (Top 10):")
    high_risk = analysis[analysis['risk_level'] == 'High Risk'].nlargest(10, 'overstock_risk_pct')
    print(high_risk[['product_id', 'product_name', 'overstock_risk_pct', 
                     'velocity', 'recommended_action']].to_string(index=False))
    
    # Show fast movers
    print("\n🚀 FAST MOVING PRODUCTS (Top 10):")
    fast_movers = analysis[analysis['velocity'] == 'Fast Mover'].nlargest(10, 'recent_sales_30d')
    print(fast_movers[['product_id', 'product_name', 'recent_sales_30d', 
                       'current_stock', 'risk_level']].to_string(index=False))
    
    print("\n✅ Risk analysis completed successfully!")