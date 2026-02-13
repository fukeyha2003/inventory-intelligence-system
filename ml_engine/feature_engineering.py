"""
Fashion Inventory Intelligence - Feature Engineering
Extracts and transforms features for ML models
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class FeatureEngineer:
    """
    Extract and engineer features from raw sales and product data
    """
    
    def __init__(self):
        self.holidays = self._get_holidays()
        self.price_tiers = {
            'budget': (0, 30),
            'mid': (30, 70),
            'premium': (70, 150),
            'luxury': (150, 1000)
        }
    
    def _get_holidays(self):
        """Define major shopping holidays"""
        current_year = datetime.now().year
        holidays = []
        
        # Major retail holidays (approximate dates)
        holiday_dates = [
            # New Year
            f'{current_year}-01-01',
            # Valentine's Day
            f'{current_year}-02-14',
            # Easter (approximate)
            f'{current_year}-04-15',
            # Memorial Day (last Monday of May)
            f'{current_year}-05-29',
            # Independence Day
            f'{current_year}-07-04',
            # Labor Day (first Monday of September)
            f'{current_year}-09-04',
            # Halloween
            f'{current_year}-10-31',
            # Thanksgiving (fourth Thursday of November)
            f'{current_year}-11-23',
            # Black Friday
            f'{current_year}-11-24',
            # Cyber Monday
            f'{current_year}-11-27',
            # Christmas
            f'{current_year}-12-25',
        ]
        
        return [pd.to_datetime(d) for d in holiday_dates]
    
    def extract_temporal_features(self, df, date_column='date'):
        """
        Extract temporal features from date column
        
        Args:
            df: DataFrame with date column
            date_column: Name of date column
            
        Returns:
            DataFrame with added temporal features
        """
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        
        # Basic temporal features
        df['year'] = df[date_column].dt.year
        df['month'] = df[date_column].dt.month
        df['day'] = df[date_column].dt.day
        df['day_of_week'] = df[date_column].dt.dayofweek  # 0=Monday, 6=Sunday
        df['day_of_year'] = df[date_column].dt.dayofyear
        df['week_of_year'] = df[date_column].dt.isocalendar().week
        
        # Weekend indicator
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Month names for readability
        df['month_name'] = df[date_column].dt.month_name()
        
        # Season
        df['season'] = df['month'].apply(self._get_season_from_month)
        
        # Holiday indicators
        df['is_holiday'] = df[date_column].isin(self.holidays).astype(int)
        df['days_to_holiday'] = df[date_column].apply(self._days_to_nearest_holiday)
        df['is_holiday_week'] = (df['days_to_holiday'].abs() <= 7).astype(int)
        
        # Beginning/End of month
        df['is_month_start'] = (df['day'] <= 7).astype(int)
        df['is_month_end'] = (df['day'] >= 23).astype(int)
        
        # Quarter
        df['quarter'] = df[date_column].dt.quarter
        
        return df
    
    def _get_season_from_month(self, month):
        """Map month to season"""
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Fall'
    
    def _days_to_nearest_holiday(self, date):
        """Calculate days to nearest holiday"""
        if not self.holidays:
            return 365
        
        differences = [(date - holiday).days for holiday in self.holidays]
        return min(differences, key=abs)
    
    def encode_product_attributes(self, df, products_df):
        """
        Encode product attributes (category, color, price tier)
        
        Args:
            df: Sales/transaction DataFrame
            products_df: Product catalog DataFrame
            
        Returns:
            DataFrame with encoded product features
        """
        df = df.copy()
        
        # Merge product attributes
        product_cols = ['product_id', 'category', 'subcategory', 'color', 
                       'price', 'season', 'size']
        available_cols = [col for col in product_cols if col in products_df.columns]
        
        df = df.merge(
            products_df[available_cols],
            on='product_id',
            how='left'
        )
        
        # Price tier encoding
        if 'price' in df.columns:
            df['price_tier'] = df['price'].apply(self._get_price_tier)
            
            # Price tier as numeric (for modeling)
            tier_mapping = {'budget': 1, 'mid': 2, 'premium': 3, 'luxury': 4}
            df['price_tier_numeric'] = df['price_tier'].map(tier_mapping)
        
        # Category frequency encoding
        if 'category' in df.columns:
            category_freq = df['category'].value_counts(normalize=True).to_dict()
            df['category_frequency'] = df['category'].map(category_freq)
        
        # Color popularity encoding
        if 'color' in df.columns:
            color_freq = df['color'].value_counts(normalize=True).to_dict()
            df['color_frequency'] = df['color'].map(color_freq)
        
        # One-hot encoding for categorical variables (optional, for tree models)
        # Uncomment if needed:
        # df = pd.get_dummies(df, columns=['category', 'color', 'season'], prefix=['cat', 'col', 'seas'])
        
        return df
    
    def _get_price_tier(self, price):
        """Classify price into tiers"""
        for tier, (min_price, max_price) in self.price_tiers.items():
            if min_price <= price < max_price:
                return tier
        return 'luxury'
    
    def create_lag_features(self, df, value_column='units_sold', 
                           product_id_column='product_id',
                           date_column='date',
                           lags=[7, 14, 30]):
        """
        Create lagged features (past sales)
        
        Args:
            df: Sales DataFrame
            value_column: Column to create lags for
            product_id_column: Product identifier column
            date_column: Date column
            lags: List of lag periods (days)
            
        Returns:
            DataFrame with lag features
        """
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values([product_id_column, date_column])
        
        # Create lag features for each product
        for lag in lags:
            df[f'{value_column}_lag_{lag}d'] = df.groupby(product_id_column)[value_column].shift(lag)
        
        return df
    
    def create_rolling_features(self, df, value_column='units_sold',
                               product_id_column='product_id',
                               date_column='date',
                               windows=[7, 30, 90]):
        """
        Create rolling window features (moving averages, std)
        
        Args:
            df: Sales DataFrame
            value_column: Column to aggregate
            product_id_column: Product identifier
            date_column: Date column
            windows: List of window sizes (days)
            
        Returns:
            DataFrame with rolling features
        """
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values([product_id_column, date_column])
        
        for window in windows:
            # Rolling mean
            df[f'{value_column}_rolling_mean_{window}d'] = df.groupby(
                product_id_column
            )[value_column].transform(lambda x: x.rolling(window=window, min_periods=1).mean())
            
            # Rolling std (volatility)
            df[f'{value_column}_rolling_std_{window}d'] = df.groupby(
                product_id_column
            )[value_column].transform(lambda x: x.rolling(window=window, min_periods=1).std())
            
            # Rolling max
            df[f'{value_column}_rolling_max_{window}d'] = df.groupby(
                product_id_column
            )[value_column].transform(lambda x: x.rolling(window=window, min_periods=1).max())
        
        return df
    
    def create_product_lifecycle_features(self, df, products_df, 
                                         date_column='date'):
        """
        Create features related to product age/lifecycle
        
        Args:
            df: Sales DataFrame
            products_df: Product catalog with launch_date
            date_column: Date column
            
        Returns:
            DataFrame with lifecycle features
        """
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        
        # Merge launch dates
        if 'launch_date' in products_df.columns:
            df = df.merge(
                products_df[['product_id', 'launch_date']],
                on='product_id',
                how='left'
            )
            
            df['launch_date'] = pd.to_datetime(df['launch_date'])
            
            # Days since launch
            df['days_since_launch'] = (df[date_column] - df['launch_date']).dt.days
            
            # Product age category
            df['product_age_category'] = pd.cut(
                df['days_since_launch'],
                bins=[-1, 30, 90, 180, 365, float('inf')],
                labels=['new', 'recent', 'established', 'mature', 'old']
            )
            
            # Lifecycle decay (new products = 1.0, old products = lower)
            df['lifecycle_decay'] = np.exp(-df['days_since_launch'] / 365)
        
        return df
    
    def create_aggregated_features(self, df, value_column='units_sold',
                                  date_column='date'):
        """
        Create aggregated features at different levels
        
        Args:
            df: Sales DataFrame with product attributes
            value_column: Column to aggregate
            date_column: Date column
            
        Returns:
            DataFrame with aggregated features
        """
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        
        # Category-level aggregations
        if 'category' in df.columns:
            category_sales = df.groupby(['category', date_column])[value_column].sum().reset_index()
            category_sales.columns = ['category', date_column, 'category_total_sales']
            df = df.merge(category_sales, on=['category', date_column], how='left')
            
            # Product share within category
            df['category_sales_share'] = df[value_column] / (df['category_total_sales'] + 1)
        
        # Price tier aggregations
        if 'price_tier' in df.columns:
            tier_sales = df.groupby(['price_tier', date_column])[value_column].sum().reset_index()
            tier_sales.columns = ['price_tier', date_column, 'tier_total_sales']
            df = df.merge(tier_sales, on=['price_tier', date_column], how='left')
        
        return df
    
    def create_full_feature_set(self, sales_df, products_df):
        """
        Create complete feature set for ML models
        
        Args:
            sales_df: Sales history DataFrame
            products_df: Product catalog DataFrame
            
        Returns:
            DataFrame with all engineered features
        """
        print("🔧 Engineering features...")
        
        df = sales_df.copy()
        
        # 1. Temporal features
        print("  ⏰ Extracting temporal features...")
        df = self.extract_temporal_features(df, date_column='date')
        
        # 2. Product attributes
        print("  🏷️  Encoding product attributes...")
        df = self.encode_product_attributes(df, products_df)
        
        # 3. Lag features
        print("  📊 Creating lag features...")
        df = self.create_lag_features(df, value_column='units_sold', lags=[7, 14, 30])
        
        # 4. Rolling features
        print("  📈 Creating rolling features...")
        df = self.create_rolling_features(df, value_column='units_sold', windows=[7, 30])
        
        # 5. Lifecycle features
        print("  🔄 Creating lifecycle features...")
        df = self.create_product_lifecycle_features(df, products_df)
        
        # 6. Aggregated features
        print("  📊 Creating aggregated features...")
        df = self.create_aggregated_features(df, value_column='units_sold')
        
        print(f"✓ Feature engineering complete! Created {len(df.columns)} total features")
        
        return df


if __name__ == '__main__':
    print("="*60)
    print("FEATURE ENGINEERING TEST")
    print("="*60)
    
    # Load data
    print("\n📂 Loading data...")
    sales_df = pd.read_csv('data/sales_history.csv')
    products_df = pd.read_csv('data/products.csv')
    
    print(f"✓ Loaded {len(sales_df):,} sales records")
    print(f"✓ Loaded {len(products_df)} products")
    
    # Engineer features
    engineer = FeatureEngineer()
    
    # Test on sample
    sample_sales = sales_df.head(10000)
    print(f"\n🧪 Testing on {len(sample_sales):,} sample records...")
    
    featured_df = engineer.create_full_feature_set(sample_sales, products_df)
    
    # Display results
    print(f"\n{'='*60}")
    print("FEATURE SUMMARY")
    print(f"{'='*60}")
    print(f"Original columns: {len(sales_df.columns)}")
    print(f"Engineered columns: {len(featured_df.columns)}")
    print(f"New features created: {len(featured_df.columns) - len(sales_df.columns)}")
    
    print("\n📋 Sample of engineered features:")
    feature_cols = [col for col in featured_df.columns if col not in sales_df.columns]
    print(f"\nNew features ({len(feature_cols)}):")
    for col in feature_cols[:15]:  # Show first 15
        print(f"  • {col}")
    if len(feature_cols) > 15:
        print(f"  ... and {len(feature_cols) - 15} more")
    
    print("\n📊 Sample data with features:")
    display_cols = ['date', 'product_id', 'units_sold', 'is_weekend', 
                    'season', 'price_tier', 'days_since_launch']
    available_display = [col for col in display_cols if col in featured_df.columns]
    print(featured_df[available_display].head(10).to_string(index=False))
    
    print("\n✅ Feature engineering test completed successfully!")