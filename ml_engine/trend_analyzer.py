"""
Fashion Inventory Intelligence - Trend Analysis
Implements trend detection based on PDF Section 3.3
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TrendAnalyzer:
    """
    Analyze product trends with multiple indicators
    Based on PDF Section 3.3: Trend Intelligence Module
    """
    
    def __init__(self):
        # Trend score component weights (from PDF Section 3.3.2)
        self.weights = {
            'sales_acceleration': 0.40,  # 40% weight
            'category_rank_change': 0.25,  # 25% weight
            'newness_factor': 0.20,  # 20% weight
            'external_signal': 0.15  # 15% weight
        }
    
    def calculate_sales_acceleration(self, sales_df, product_id, 
                                    recent_period=7, comparison_period=7):
        """
        Calculate week-over-week growth rate (Sales Velocity Change)
        
        Args:
            sales_df: Sales history DataFrame
            product_id: Product to analyze
            recent_period: Recent period in days (default 7)
            comparison_period: Comparison period in days (default 7)
            
        Returns:
            Acceleration percentage (-100 to +inf)
        """
        product_sales = sales_df[sales_df['product_id'] == product_id].copy()
        product_sales['date'] = pd.to_datetime(product_sales['date'])
        product_sales = product_sales.sort_values('date')
        
        if len(product_sales) < (recent_period + comparison_period):
            return 0.0
        
        # Recent period sales
        recent_cutoff = product_sales['date'].max() - timedelta(days=recent_period)
        recent_sales = product_sales[
            product_sales['date'] > recent_cutoff
        ]['units_sold'].sum()
        
        # Previous period sales
        previous_end = recent_cutoff
        previous_start = previous_end - timedelta(days=comparison_period)
        previous_sales = product_sales[
            (product_sales['date'] > previous_start) & 
            (product_sales['date'] <= previous_end)
        ]['units_sold'].sum()
        
        # Calculate acceleration
        if previous_sales == 0:
            return 100.0 if recent_sales > 0 else 0.0
        
        acceleration = ((recent_sales - previous_sales) / previous_sales) * 100
        
        return round(acceleration, 2)
    
    def calculate_category_rank_change(self, sales_df, products_df, product_id,
                                       recent_period=30):
        """
        Calculate movement within category sales ranking
        
        Args:
            sales_df: Sales history
            products_df: Product catalog
            product_id: Product to analyze
            recent_period: Period for ranking calculation
            
        Returns:
            Rank change (negative = improved ranking)
        """
        # Get product category
        product_info = products_df[products_df['product_id'] == product_id]
        if len(product_info) == 0:
            return 0
        
        category = product_info['category'].iloc[0]
        
        # Get all products in same category
        category_products = products_df[
            products_df['category'] == category
        ]['product_id'].tolist()
        
        # Calculate recent sales for all products in category
        recent_cutoff = pd.to_datetime(sales_df['date']).max() - timedelta(days=recent_period)
        recent_sales = sales_df[
            (pd.to_datetime(sales_df['date']) > recent_cutoff) &
            (sales_df['product_id'].isin(category_products))
        ].groupby('product_id')['units_sold'].sum().reset_index()
        
        recent_sales = recent_sales.sort_values('units_sold', ascending=False)
        recent_sales['recent_rank'] = range(1, len(recent_sales) + 1)
        
        # Calculate previous period sales
        previous_end = recent_cutoff
        previous_start = previous_end - timedelta(days=recent_period)
        previous_sales = sales_df[
            (pd.to_datetime(sales_df['date']) > previous_start) &
            (pd.to_datetime(sales_df['date']) <= previous_end) &
            (sales_df['product_id'].isin(category_products))
        ].groupby('product_id')['units_sold'].sum().reset_index()
        
        previous_sales = previous_sales.sort_values('units_sold', ascending=False)
        previous_sales['previous_rank'] = range(1, len(previous_sales) + 1)
        
        # Merge and calculate change
        rank_changes = recent_sales[['product_id', 'recent_rank']].merge(
            previous_sales[['product_id', 'previous_rank']],
            on='product_id',
            how='left'
        )
        
        product_rank = rank_changes[rank_changes['product_id'] == product_id]
        
        if len(product_rank) == 0:
            return 0
        
        recent_rank = product_rank['recent_rank'].iloc[0]
        previous_rank = product_rank['previous_rank'].iloc[0] if pd.notna(product_rank['previous_rank'].iloc[0]) else recent_rank
        
        # Negative = improved (moved up in ranking)
        rank_change = recent_rank - previous_rank
        
        # Normalize by total products in category
        normalized_change = (rank_change / len(category_products)) * 100
        
        return round(normalized_change, 2)
    
    def calculate_newness_factor(self, products_df, product_id, decay_rate=0.5):
        """
        Calculate newness factor with decay function
        
        Args:
            products_df: Product catalog with launch_date
            product_id: Product to analyze
            decay_rate: Decay rate (0-1, higher = faster decay)
            
        Returns:
            Newness score (0-100, 100 = brand new)
        """
        product = products_df[products_df['product_id'] == product_id]
        
        if len(product) == 0 or 'launch_date' not in products_df.columns:
            return 50.0  # Default for unknown
        
        launch_date = pd.to_datetime(product['launch_date'].iloc[0])
        days_since_launch = (datetime.now() - launch_date).days
        
        # Exponential decay: new products = 100, decays over time
        # At 90 days, score drops to ~50 with decay_rate=0.5
        newness = 100 * np.exp(-decay_rate * (days_since_launch / 90))
        
        return round(newness, 2)
    
    def calculate_external_signal(self, product_id, social_data=None):
        """
        Calculate external signal (social media, search trends)
        
        Args:
            product_id: Product to analyze
            social_data: Optional DataFrame with external signals
            
        Returns:
            External signal score (0-100)
        """
        # Placeholder: In production, integrate with:
        # - Google Trends API
        # - Social media analytics
        # - Search volume data
        
        if social_data is not None and product_id in social_data.index:
            return social_data.loc[product_id, 'signal_score']
        
        # Default: random signal for demo (replace with real data)
        # In production: return actual social/search metrics
        return np.random.uniform(30, 70)
    
    def calculate_trend_score(self, sales_df, products_df, product_id,
                             social_data=None):
        """
        Calculate composite trend score (0-100)
        Based on PDF Section 3.3.2 weighted components
        
        Args:
            sales_df: Sales history
            products_df: Product catalog
            product_id: Product to analyze
            social_data: Optional external signals
            
        Returns:
            Dictionary with component scores and total
        """
        # Calculate each component
        sales_accel = self.calculate_sales_acceleration(sales_df, product_id)
        rank_change = self.calculate_category_rank_change(
            sales_df, products_df, product_id
        )
        newness = self.calculate_newness_factor(products_df, product_id)
        external = self.calculate_external_signal(product_id, social_data)
        
        # Normalize sales acceleration to 0-100 scale
        # Assume -50% to +150% range maps to 0-100
        sales_accel_normalized = np.clip((sales_accel + 50) / 2, 0, 100)
        
        # Normalize rank change (negative is good, so invert)
        # Assume -50 to +50 range
        rank_change_normalized = np.clip(50 - rank_change, 0, 100)
        
        # Calculate weighted score
        trend_score = (
            self.weights['sales_acceleration'] * sales_accel_normalized +
            self.weights['category_rank_change'] * rank_change_normalized +
            self.weights['newness_factor'] * newness +
            self.weights['external_signal'] * external
        )
        
        return {
            'product_id': product_id,
            'trend_score': round(trend_score, 2),
            'sales_acceleration_pct': sales_accel,
            'sales_acceleration_score': round(sales_accel_normalized, 2),
            'category_rank_change': rank_change,
            'rank_change_score': round(rank_change_normalized, 2),
            'newness_factor': newness,
            'external_signal': external
        }
    
    def classify_trend(self, trend_score):
        """
        Classify trend as Emerging/Peak/Declining
        
        Args:
            trend_score: Composite trend score (0-100)
            
        Returns:
            Trend classification string
        """
        if trend_score >= 70:
            return 'Emerging'
        elif trend_score >= 40:
            return 'Peak'
        else:
            return 'Declining'
    
    def generate_trend_insight(self, trend_data, inventory_level=None,
                              predicted_sales=None):
        """
        Generate strategic insight based on trend analysis
        Implements PDF Section 3.3.3: Strategic Insight Generation
        
        Args:
            trend_data: Dictionary from calculate_trend_score()
            inventory_level: Current stock level (optional)
            predicted_sales: Forecasted sales (optional)
            
        Returns:
            Natural language insight and recommendation
        """
        trend_score = trend_data['trend_score']
        sales_accel = trend_data['sales_acceleration_pct']
        trend_class = self.classify_trend(trend_score)
        
        # Base insight
        if trend_class == 'Emerging':
            insight = f"This item shows strong momentum with {abs(sales_accel):.0f}% week-over-week growth."
            
            if inventory_level and predicted_sales:
                if inventory_level < predicted_sales * 2:
                    recommendation = f"Recommendation: Increase inventory allocation by 30-50% and delay planned discounts by 3-4 weeks to maximize margin."
                else:
                    recommendation = "Recommendation: Maintain current inventory and monitor closely. Consider reordering soon."
            else:
                recommendation = "Recommendation: Consider increasing inventory allocation and delaying discounts."
        
        elif trend_class == 'Peak':
            insight = f"This item is at peak performance with steady sales."
            
            if sales_accel > 0:
                recommendation = "Recommendation: Maintain current strategy. Monitor for signs of decline."
            else:
                recommendation = "Recommendation: Prepare gradual discount strategy (10-15%) if sales begin declining."
        
        else:  # Declining
            insight = f"This item shows declining trend with {abs(sales_accel):.0f}% sales drop."
            
            if inventory_level and predicted_sales:
                stock_to_sales_ratio = inventory_level / (predicted_sales + 1)
                
                if stock_to_sales_ratio > 3:
                    recommendation = "Recommendation: Immediate action required. Apply 25-30% discount within 1 week to clear inventory."
                elif stock_to_sales_ratio > 2:
                    recommendation = "Recommendation: Begin progressive discount strategy (15-20%) starting next week."
                else:
                    recommendation = "Recommendation: Monitor closely. Small discount (10%) may be sufficient."
            else:
                recommendation = "Recommendation: Consider discount strategy to accelerate sales."
        
        return {
            'insight': insight,
            'recommendation': recommendation,
            'trend_classification': trend_class,
            'urgency': 'High' if trend_class == 'Declining' else 'Medium' if trend_class == 'Peak' else 'Low'
        }
    
    def analyze_all_products(self, sales_df, products_df, top_n=20):
        """
        Analyze trends for all products
        
        Args:
            sales_df: Sales history
            products_df: Product catalog
            top_n: Number of top trending products to return
            
        Returns:
            DataFrame with trend analysis
        """
        print(f"\n🔍 Analyzing trends for {len(products_df)} products...")
        
        results = []
        
        for i, product_id in enumerate(products_df['product_id']):
            try:
                trend_data = self.calculate_trend_score(
                    sales_df, products_df, product_id
                )
                trend_data['trend_classification'] = self.classify_trend(
                    trend_data['trend_score']
                )
                results.append(trend_data)
                
                if (i + 1) % 100 == 0:
                    print(f"   Processed {i + 1}/{len(products_df)} products")
                    
            except Exception as e:
                print(f"   ⚠ Failed for {product_id}: {str(e)}")
        
        trend_df = pd.DataFrame(results)
        
        # Add product names
        trend_df = trend_df.merge(
            products_df[['product_id', 'product_name', 'category']],
            on='product_id',
            how='left'
        )
        
        print(f"✓ Trend analysis complete for {len(trend_df)} products")
        
        return trend_df.sort_values('trend_score', ascending=False)


if __name__ == '__main__':
    print("="*60)
    print("TREND ANALYSIS TEST")
    print("="*60)
    
    # Load data
    print("\n📂 Loading data...")
    sales_df = pd.read_csv('data/sales_history.csv')
    products_df = pd.read_csv('data/products.csv')
    
    # Initialize analyzer
    analyzer = TrendAnalyzer()
    
    # Test on sample product
    test_product = products_df['product_id'].iloc[10]
    product_name = products_df[products_df['product_id'] == test_product]['product_name'].iloc[0]
    
    print(f"\n🧪 Testing trend analysis on: {test_product} ({product_name})")
    
    # Calculate trend score
    trend_data = analyzer.calculate_trend_score(sales_df, products_df, test_product)
    
    print("\n📊 Trend Components:")
    for key, value in trend_data.items():
        if key != 'product_id':
            print(f"   {key}: {value}")
    
    # Generate insight
    insight = analyzer.generate_trend_insight(trend_data)
    
    print("\n💡 Strategic Insight:")
    print(f"   Classification: {insight['trend_classification']}")
    print(f"   Urgency: {insight['urgency']}")
    print(f"   {insight['insight']}")
    print(f"   {insight['recommendation']}")
    
    # Analyze top products
    print(f"\n{'='*60}")
    print("TOP TRENDING PRODUCTS")
    print(f"{'='*60}")
    
    trend_df = analyzer.analyze_all_products(sales_df, products_df.head(100))
    
    print("\n🔥 Top 10 Emerging Trends:")
    top_emerging = trend_df[trend_df['trend_classification'] == 'Emerging'].head(10)
    print(top_emerging[['product_id', 'product_name', 'trend_score', 
                        'sales_acceleration_pct']].to_string(index=False))
    
    print("\n⚠️ Top 10 Declining Products:")
    top_declining = trend_df[trend_df['trend_classification'] == 'Declining'].head(10)
    print(top_declining[['product_id', 'product_name', 'trend_score',
                         'sales_acceleration_pct']].to_string(index=False))
    
    print("\n✅ Trend analysis test completed successfully!")