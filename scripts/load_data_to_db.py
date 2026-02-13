"""
Load CSV data into Django database
Run: python manage.py shell < scripts/load_data_to_db.py
"""

import os
import sys
import django
# Add project root to PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)


# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from apps.inventory.models import Product, SalesHistory, InventoryLevel

print("Loading CSV data into database...")

# Load products
print("\n1. Loading products...")
products_df = pd.read_csv('ml_engine/data/products.csv')

for _, row in products_df.iterrows():
    Product.objects.get_or_create(
        sku=row['product_id'],
        defaults={
            'product_name': row['product_name'],
            'category': row['category'],
            'subcategory': row['subcategory'],
            'color': row['color'],
            'size': row['size'],
            'season': row['season'],
            'price': row['price'],
            'cost': row['cost'],
            'launch_date': pd.to_datetime(row['launch_date']).date(),
        }
    )

print(f"✓ Loaded {Product.objects.count()} products")

# Load sales history (in batches for performance)
print("\n2. Loading sales history...")
sales_df = pd.read_csv('ml_engine/data/sales_history.csv')

batch_size = 1000
sales_objects = []

for i, row in sales_df.iterrows():
    try:
        product = Product.objects.get(sku=row['product_id'])
        sales_objects.append(
            SalesHistory(
                product=product,
                date=pd.to_datetime(row['date']).date(),
                units_sold=row['units_sold'],
                revenue=row['revenue'],
                discount_rate=row.get('discount_rate', 0.0)
            )
        )
        
        # Bulk create in batches
        if len(sales_objects) >= batch_size:
            SalesHistory.objects.bulk_create(sales_objects, ignore_conflicts=True)
            print(f"  Loaded {i+1} records...")
            sales_objects = []
    except Product.DoesNotExist:
        print(f"  Warning: Product {row['product_id']} not found")

# Create remaining
if sales_objects:
    SalesHistory.objects.bulk_create(sales_objects, ignore_conflicts=True)

print(f"✓ Loaded {SalesHistory.objects.count()} sales records")

# Load inventory
print("\n3. Loading inventory...")
inventory_df = pd.read_csv('ml_engine/data/inventory.csv')

for _, row in inventory_df.iterrows():
    try:
        product = Product.objects.get(sku=row['product_id'])
        InventoryLevel.objects.update_or_create(
            product=product,
            defaults={
                'current_stock': row['current_stock'],
                'warehouse_location': row['warehouse_location'],
                'last_restock_date': pd.to_datetime(row['last_restock_date']).date(),
            }
        )
    except Product.DoesNotExist:
        print(f"  Warning: Product {row['product_id']} not found")

print(f"✓ Loaded {InventoryLevel.objects.count()} inventory records")

print("\n✅ Data loading complete!")
print(f"\nDatabase Summary:")
print(f"  Products: {Product.objects.count()}")
print(f"  Sales Records: {SalesHistory.objects.count()}")
print(f"  Inventory: {InventoryLevel.objects.count()}")