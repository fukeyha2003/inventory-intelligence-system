"""
Synthetic H&M-style Fashion Data Generator
This creates realistic fashion retail data for testing the ML engine.
Replace with actual H&M dataset when available.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

class FashionDataGenerator:
    """Generate synthetic fashion retail data mimicking H&M structure"""
    
    def __init__(self, seed=42):
        np.random.seed(seed)
        random.seed(seed)
        
        # Fashion categories and attributes
        self.categories = ['Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Accessories', 'Shoes']
        self.subcategories = {
            'Tops': ['T-shirts', 'Blouses', 'Sweaters', 'Shirts'],
            'Bottoms': ['Jeans', 'Trousers', 'Skirts', 'Shorts'],
            'Dresses': ['Casual Dresses', 'Evening Dresses', 'Summer Dresses'],
            'Outerwear': ['Jackets', 'Coats', 'Blazers'],
            'Accessories': ['Bags', 'Scarves', 'Belts', 'Jewelry'],
            'Shoes': ['Sneakers', 'Boots', 'Sandals', 'Heels']
        }
        self.colors = ['Black', 'White', 'Blue', 'Red', 'Green', 'Grey', 'Brown', 'Pink']
        self.sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        self.seasons = ['Spring', 'Summer', 'Fall', 'Winter']
        
    def generate_products(self, n_products=500):
        """Generate product catalog"""
        products = []
        
        for i in range(n_products):
            category = random.choice(self.categories)
            subcategory = random.choice(self.subcategories[category])
            
            product = {
                'product_id': f'SKU{i:05d}',
                'product_name': f'{random.choice(self.colors)} {subcategory}',
                'category': category,
                'subcategory': subcategory,
                'color': random.choice(self.colors),
                'size': random.choice(self.sizes),
                'price': round(random.uniform(15, 150), 2),
                'cost': 0,  # Will calculate as 40-60% of price
                'season': random.choice(self.seasons),
                'launch_date': datetime.now() - timedelta(days=random.randint(400, 730))
            }
            # Cost is 40-60% of price
            product['cost'] = round(product['price'] * random.uniform(0.4, 0.6), 2)
            products.append(product)
        
        df = pd.DataFrame(products)
        return df
    
    def generate_sales_history(self, products_df, days=365, start_date=None):
        """Generate realistic sales transactions with seasonality and trends"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=days)
        
        transactions = []
        
        for _, product in products_df.iterrows():
            # Base daily sales (varies by category and price)
            if product['category'] in ['Tops', 'Accessories']:
                base_sales = random.uniform(3, 8)
            elif product['category'] in ['Bottoms', 'Shoes']:
                base_sales = random.uniform(2, 6)
            else:
                base_sales = random.uniform(1, 4)
            
            # Price elasticity (higher price = lower volume)
            price_factor = max(0.3, 1 - (product['price'] / 200))
            base_sales *= price_factor
            
            for day in range(days):
                current_date = start_date + timedelta(days=day)
                
                # Seasonal multiplier
                month = current_date.month
                if product['season'] == 'Winter' and month in [11, 12, 1, 2]:
                    seasonal_mult = 1.5
                elif product['season'] == 'Spring' and month in [3, 4, 5]:
                    seasonal_mult = 1.5
                elif product['season'] == 'Summer' and month in [6, 7, 8]:
                    seasonal_mult = 1.5
                elif product['season'] == 'Fall' and month in [9, 10, 11]:
                    seasonal_mult = 1.5
                else:
                    seasonal_mult = 0.6
                
                # Weekend boost
                weekday_mult = 1.3 if current_date.weekday() in [5, 6] else 1.0
                
                # Product age decay (new products sell better)
                days_since_launch = (current_date - product['launch_date']).days
                age_mult = max(0.3, 1 - (days_since_launch / 365) * 0.4)
                
                # Add random variation
                random_mult = random.uniform(0.7, 1.3)
                
                # Calculate daily sales
                expected_sales = base_sales * seasonal_mult * weekday_mult * age_mult * random_mult
                actual_sales = max(0, int(np.random.poisson(expected_sales)))
                
                if actual_sales > 0:
                    transactions.append({
                        'date': current_date.strftime('%Y-%m-%d'),
                        'product_id': product['product_id'],
                        'units_sold': actual_sales,
                        'revenue': actual_sales * product['price'],
                        'discount_rate': 0.0 if random.random() > 0.2 else random.uniform(0.1, 0.3)
                    })
        
        df = pd.DataFrame(transactions)
        return df
    
    def generate_current_inventory(self, products_df, sales_df):
        """Generate current inventory levels based on sales patterns"""
        
        inventory = []
        
        for _, product in products_df.iterrows():
            # Get recent sales (last 30 days)
            product_sales = sales_df[sales_df['product_id'] == product['product_id']]
            recent_sales = product_sales[
                pd.to_datetime(product_sales['date']) >= (datetime.now() - timedelta(days=30))
            ]['units_sold'].sum()
            
            # Average daily sales
            avg_daily_sales = recent_sales / 30 if recent_sales > 0 else 1
            
            # Current stock: 30-90 days worth of inventory (realistic variance)
            days_of_stock = random.uniform(30, 90)
            current_stock = int(avg_daily_sales * days_of_stock * random.uniform(0.8, 1.5))
            
            inventory.append({
                'product_id': product['product_id'],
                'current_stock': max(0, current_stock),
                'warehouse_location': random.choice(['WH_A', 'WH_B', 'WH_C']),
                'last_restock_date': (datetime.now() - timedelta(days=random.randint(10, 60))).strftime('%Y-%m-%d')
            })
        
        df = pd.DataFrame(inventory)
        return df
    
    def save_datasets(self, output_dir='data'):
        """Generate and save all datasets"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        print("Generating products dataset...")
        products = self.generate_products(n_products=500)
        products.to_csv(f'{output_dir}/products.csv', index=False)
        print(f"✓ Created {len(products)} products")
        
        print("Generating sales history (365 days)...")
        sales = self.generate_sales_history(products, days=365)
        sales.to_csv(f'{output_dir}/sales_history.csv', index=False)
        print(f"✓ Created {len(sales)} transactions")
        
        print("Generating current inventory...")
        inventory = self.generate_current_inventory(products, sales)
        inventory.to_csv(f'{output_dir}/inventory.csv', index=False)
        print(f"✓ Created inventory for {len(inventory)} products")
        
        return products, sales, inventory


if __name__ == '__main__':
    generator = FashionDataGenerator()
    products, sales, inventory = generator.save_datasets()
    
    print("\n📊 Dataset Summary:")
    print(f"Products: {len(products)}")
    print(f"Transactions: {len(sales)}")
    print(f"Inventory Items: {len(inventory)}")
    print(f"\nTotal Revenue: ${sales['revenue'].sum():,.2f}")
    print(f"Date Range: {sales['date'].min()} to {sales['date'].max()}")