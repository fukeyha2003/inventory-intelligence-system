"""
Load CSV data into Django database (Multi-Tenant Version)
Run: python scripts/load_data_to_db.py
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
from apps.inventory.models import Product, SalesHistory, InventoryLevel, Company

print("="*60)
print("LOADING CSV DATA INTO DATABASE (Multi-Tenant)")
print("="*60)

# Step 0: Create or get default company
print("\n🏢 Setting up company...")
company, created = Company.objects.get_or_create(
    slug='default-company',
    defaults={
        'name': 'Default Company',
        'subscription_plan': 'pro'
    }
)
if created:
    print(f"✓ Created new company: {company.name}")
else:
    print(f"✓ Using existing company: {company.name}")

# Step 1: Load products
print("\n📦 Loading products...")
products_csv = os.path.join(BASE_DIR, 'ml_engine', 'data', 'products.csv')  # ← Fixed path
print(f"Reading from: {products_csv}")

products_df = pd.read_csv(products_csv)

for _, row in products_df.iterrows():
    Product.objects.get_or_create(
        company=company,
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

print(f"✓ Loaded {Product.objects.filter(company=company).count()} products for {company.name}")

# Step 2: Load sales history
print("\n💰 Loading sales history...")
sales_csv = os.path.join(BASE_DIR, 'ml_engine', 'data', 'sales_history.csv')  # ← Fixed path
sales_df = pd.read_csv(sales_csv)

batch_size = 1000
sales_objects = []

for i, row in sales_df.iterrows():
    try:
        product = Product.objects.get(company=company, sku=row['product_id'])
        sales_objects.append(
            SalesHistory(
                product=product,
                date=pd.to_datetime(row['date']).date(),
                units_sold=row['units_sold'],
                revenue=row['revenue'],
                discount_rate=row.get('discount_rate', 0.0)
            )
        )
        
        if len(sales_objects) >= batch_size:
            SalesHistory.objects.bulk_create(sales_objects, ignore_conflicts=True)
            print(f"  Loaded {i+1:,} records...", end='\r')
            sales_objects = []
    except Product.DoesNotExist:
        pass

if sales_objects:
    SalesHistory.objects.bulk_create(sales_objects, ignore_conflicts=True)

print(f"\n✓ Loaded {SalesHistory.objects.count():,} sales records")

# Step 3: Load inventory
print("\n📋 Loading inventory...")
inventory_csv = os.path.join(BASE_DIR, 'ml_engine', 'data', 'inventory.csv')  # ← Fixed path
inventory_df = pd.read_csv(inventory_csv)

for _, row in inventory_df.iterrows():
    try:
        product = Product.objects.get(company=company, sku=row['product_id'])
        InventoryLevel.objects.update_or_create(
            product=product,
            defaults={
                'current_stock': row['current_stock'],
                'warehouse_location': row['warehouse_location'],
                'last_restock_date': pd.to_datetime(row['last_restock_date']).date(),
            }
        )
    except Product.DoesNotExist:
        pass

print(f"✓ Loaded {InventoryLevel.objects.count()} inventory records")

print("\n" + "="*60)
print("✅ DATA LOADING COMPLETE!")
print("="*60)
print(f"\nDatabase Summary:")
print(f"  Company: {company.name}")
print(f"  Products: {Product.objects.filter(company=company).count()}")
print(f"  Sales Records: {SalesHistory.objects.count():,}")
print(f"  Inventory: {InventoryLevel.objects.count()}")
print(f"\n🌐 Visit: http://127.0.0.1:8000/dashboard/overview/")