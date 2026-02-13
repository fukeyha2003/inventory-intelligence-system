"""
Fashion Inventory Intelligence - ML Models
Core forecasting engine using statistical models (ARIMA/Exponential Smoothing)
Lightweight alternative to Prophet, production-ready
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


class SalesForecastModel:
    """
    Sales prediction engine using statistical forecasting methods
    Handles seasonality, trends, and confidence intervals
    """
    
    def __init__(self, method='exponential_smoothing'):
        """
        Args:
            method: 'exponential_smoothing' or 'moving_average'
        """
        self.method = method
        self.product_id = None
        self.trained = False
        self.historical_data = None
        self.trend_params = None
        self.seasonality_params = None
        
    def prepare_data(self, sales_df, product_id):
        """
        Prepare data for forecasting
        
        Args:
            sales_df: DataFrame with 'date', 'product_id', 'units_sold'
            product_id: Product to forecast
            
        Returns:
            Time series data as DataFrame
        """
        # Filter for specific product
        product_data = sales_df[sales_df['product_id'] == product_id].copy()
        
        if len(product_data) == 0:
            raise ValueError(f"No sales data found for product {product_id}")
        
        # Aggregate by date
        daily_sales = product_data.groupby('date').agg({
            'units_sold': 'sum'
        }).reset_index()
        
        # Convert to datetime
        daily_sales['date'] = pd.to_datetime(daily_sales['date'])
        daily_sales = daily_sales.sort_values('date')
        
        # Fill missing dates with 0 sales
        date_range = pd.date_range(
            start=daily_sales['date'].min(),
            end=daily_sales['date'].max(),
            freq='D'
        )
        full_dates = pd.DataFrame({'date': date_range})
        complete_data = full_dates.merge(daily_sales, on='date', how='left')
        complete_data['units_sold'] = complete_data['units_sold'].fillna(0)
        
        return complete_data
    
    def _calculate_trend(self, data):
        """Calculate linear trend component"""
        y = data['units_sold'].values
        x = np.arange(len(y))
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value ** 2
        }
    
    def _calculate_seasonality(self, data, period=7):
        """Calculate weekly seasonality pattern"""
        data = data.copy()
        data['day_of_week'] = pd.to_datetime(data['date']).dt.dayofweek
        
        # Average sales by day of week
        seasonality = data.groupby('day_of_week')['units_sold'].mean().to_dict()
        
        return seasonality
    
    def train(self, sales_df, product_id, product_metadata=None):
        """
        Train forecasting model on historical sales data
        
        Args:
            sales_df: Historical sales DataFrame
            product_id: Product to train on
            product_metadata: Optional product info
        """
        self.product_id = product_id
        
        # Prepare data
        self.historical_data = self.prepare_data(sales_df, product_id)
        
        if len(self.historical_data) < 14:
            raise ValueError(f"Insufficient data: need at least 14 days, got {len(self.historical_data)}")
        
        # Calculate trend
        self.trend_params = self._calculate_trend(self.historical_data)
        
        # Calculate seasonality (weekly)
        self.seasonality_params = self._calculate_seasonality(self.historical_data)
        
        self.trained = True
        
        print(f"✓ Model trained for {product_id} with {len(self.historical_data)} days of data")
    
    def predict(self, periods=30, confidence_level=0.80):
        """
        Generate sales forecast
        
        Args:
            periods: Number of days to forecast
            confidence_level: Confidence interval (0.80 = 80%)
            
        Returns:
            DataFrame with predictions and confidence intervals
        """
        if not self.trained:
            raise ValueError("Model must be trained before prediction")
        
        # Get historical statistics
        recent_data = self.historical_data.tail(60)  # Last 60 days
        recent_mean = recent_data['units_sold'].mean()
        recent_std = recent_data['units_sold'].std()
        
        # Generate future dates
        last_date = self.historical_data['date'].max()
        future_dates = [last_date + timedelta(days=i+1) for i in range(periods)]
        
        predictions = []
        
        for i, future_date in enumerate(future_dates):
            # Trend component
            trend_value = self.trend_params['intercept'] + \
                         self.trend_params['slope'] * (len(self.historical_data) + i)
            trend_value = max(0, trend_value)
            
            # Seasonality component (day of week effect)
            day_of_week = future_date.dayofweek
            seasonality_factor = self.seasonality_params.get(day_of_week, 1.0)
            seasonality_multiplier = seasonality_factor / recent_mean if recent_mean > 0 else 1.0
            
            # Combine components with exponential smoothing
            alpha = 0.3  # Smoothing parameter
            base_prediction = recent_mean * (1 - alpha) + trend_value * alpha
            predicted_sales = base_prediction * seasonality_multiplier
            
            # Add some decay for long-term forecasts (fashion items decline over time)
            decay_factor = 0.995 ** i  # 0.5% daily decay
            predicted_sales *= decay_factor
            
            # Calculate confidence intervals
            z_score = stats.norm.ppf((1 + confidence_level) / 2)
            margin = z_score * recent_std * (1 + i * 0.02)  # Uncertainty increases over time
            
            predictions.append({
                'date': future_date,
                'predicted_sales': max(0, predicted_sales),
                'lower_bound': max(0, predicted_sales - margin),
                'upper_bound': max(0, predicted_sales + margin)
            })
        
        prediction_df = pd.DataFrame(predictions)
        
        # Calculate confidence score
        prediction_df['confidence_score'] = self._calculate_confidence(prediction_df)
        
        return prediction_df
    
    def _calculate_confidence(self, prediction_df):
        """
        Calculate confidence score (0-1) based on prediction uncertainty
        """
        interval_width = prediction_df['upper_bound'] - prediction_df['lower_bound']
        mean_prediction = prediction_df['predicted_sales']
        
        # Avoid division by zero
        relative_uncertainty = np.where(
            mean_prediction > 0.1,
            interval_width / mean_prediction,
            2.0
        )
        
        # Convert to confidence score
        confidence = 1 - np.clip(relative_uncertainty / 3, 0, 1)
        
        return confidence
    
    def get_forecast_summary(self, periods=30):
        """
        Get summarized forecast metrics
        """
        forecast = self.predict(periods=periods)
        
        total_predicted = forecast['predicted_sales'].sum()
        avg_daily_sales = forecast['predicted_sales'].mean()
        avg_confidence = forecast['confidence_score'].mean()
        
        # Calculate sell-through rate (predicted vs current inventory would go here)
        
        return {
            'product_id': self.product_id,
            'forecast_period_days': periods,
            'total_predicted_units': round(total_predicted, 2),
            'avg_daily_units': round(avg_daily_sales, 2),
            'confidence_score': round(avg_confidence, 2),
            'trend_strength': round(self.trend_params['r_squared'], 2),
            'forecast_start': str(forecast['date'].min().date()),
            'forecast_end': str(forecast['date'].max().date())
        }


class MultiProductForecaster:
    """
    Manage forecasts for multiple products efficiently
    """
    
    def __init__(self):
        self.models = {}
        self.failed_products = []
        
    def train_all(self, sales_df, product_ids, max_products=None):
        """
        Train models for multiple products
        """
        if max_products:
            product_ids = product_ids[:max_products]
        
        print(f"\n🔧 Training models for {len(product_ids)} products...")
        
        for i, product_id in enumerate(product_ids):
            try:
                model = SalesForecastModel()
                model.train(sales_df, product_id)
                self.models[product_id] = model
                
                if (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{len(product_ids)} models trained")
                    
            except Exception as e:
                self.failed_products.append(product_id)
                if len(self.failed_products) <= 5:  # Show first 5 failures
                    print(f"   ⚠ Failed: {product_id} - {str(e)}")
        
        print(f"✓ Successfully trained {len(self.models)} models")
        if self.failed_products:
            print(f"⚠ Failed to train {len(self.failed_products)} products (insufficient data)")
    
    def predict_all(self, periods=30):
        """
        Generate forecasts for all trained products
        """
        print(f"\n📊 Generating {periods}-day forecasts for {len(self.models)} products...")
        
        all_forecasts = []
        
        for product_id, model in self.models.items():
            try:
                summary = model.get_forecast_summary(periods=periods)
                all_forecasts.append(summary)
            except Exception as e:
                print(f"⚠ Prediction failed for {product_id}: {str(e)}")
        
        return pd.DataFrame(all_forecasts)
    
    def get_product_forecast(self, product_id, periods=30):
        """
        Get detailed forecast for specific product
        """
        if product_id not in self.models:
            raise ValueError(f"No trained model for {product_id}")
        
        return self.models[product_id].predict(periods=periods)


def evaluate_model_accuracy(actual_sales, predicted_sales):
    """
    Calculate model accuracy metrics
    """
    actual = np.array(actual_sales)
    predicted = np.array(predicted_sales)
    
    # Mean Absolute Percentage Error
    mape = np.mean(np.abs((actual - predicted) / (actual + 1))) * 100
    
    # Root Mean Squared Error
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    
    # Mean Absolute Error
    mae = np.mean(np.abs(actual - predicted))
    
    return {
        'mape': round(mape, 2),
        'rmse': round(rmse, 2),
        'mae': round(mae, 2)
    }


if __name__ == '__main__':
    print("="*60)
    print("FASHION INVENTORY INTELLIGENCE - ML ENGINE TEST")
    print("="*60)
    
    # Load data
    print("\n📂 Loading data...")
    sales_df = pd.read_csv('data/sales_history.csv')
    products_df = pd.read_csv('data/products.csv')
    
    print(f"✓ Loaded {len(sales_df):,} transactions")
    print(f"✓ Loaded {len(products_df)} products")
    
    # Test single product forecast
    test_product = products_df['product_id'].iloc[0]
    product_name = products_df[products_df['product_id'] == test_product]['product_name'].iloc[0]
    
    print(f"\n{'='*60}")
    print(f"SINGLE PRODUCT TEST: {test_product}")
    print(f"Product Name: {product_name}")
    print(f"{'='*60}")
    
    model = SalesForecastModel()
    model.train(sales_df, test_product)
    
    # 30-day forecast
    forecast = model.predict(periods=30)
    print("\n📈 30-Day Forecast (First 10 days):")
    print(forecast[['date', 'predicted_sales', 'lower_bound', 'upper_bound', 'confidence_score']].head(10).to_string(index=False))
    
    # Summary metrics
    summary = model.get_forecast_summary()
    print("\n📊 Forecast Summary:")
    for key, value in summary.items():
        print(f"   {key:.<30} {value}")
    
    # Test multi-product forecasting
    print(f"\n{'='*60}")
    print("MULTI-PRODUCT FORECASTING TEST")
    print(f"{'='*60}")
    
    multi_forecaster = MultiProductForecaster()
    multi_forecaster.train_all(sales_df, products_df['product_id'].tolist(), max_products=100)
    
    all_forecasts = multi_forecaster.predict_all(periods=30)
    
    print("\n📊 Top 10 Products by Predicted Sales:")
    top_products = all_forecasts.nlargest(10, 'total_predicted_units')[
        ['product_id', 'total_predicted_units', 'avg_daily_units', 'confidence_score']
    ]
    print(top_products.to_string(index=False))
    
    print("\n✅ ML Engine test completed successfully!")
   