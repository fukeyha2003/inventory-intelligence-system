"""
Django Models for Fashion Inventory System
Location: apps/inventory/models.py
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


# ============================================================================
# COMPANY & USER MODELS (DEFINE THESE FIRST!)
# ============================================================================

class Company(models.Model):
    """Company/Organization model for multi-tenant support"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Subscription info (optional)
    subscription_plan = models.CharField(
        max_length=50, 
        choices=[('free', 'Free'), ('pro', 'Pro'), ('enterprise', 'Enterprise')],
        default='free'
    )
    
    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'Companies'
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Administrator'),
            ('manager', 'Manager'),
            ('viewer', 'Viewer')
        ],
        default='viewer'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"{self.user.email} - {self.company.name}"


# ============================================================================
# INVENTORY MODELS (NOW Company exists above, so this works!)
# ============================================================================

class Product(models.Model):
    """Product catalog"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')  # ← Now this works!
    sku = models.CharField(max_length=50, db_index=True)  # ← Removed 'unique=True' because of unique_together below
    product_name = models.CharField(max_length=200)
    
    # Product attributes
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=20)
    season = models.CharField(max_length=50)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    launch_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        unique_together = ['company', 'sku']  # SKU unique per company
    
    def __str__(self):
        return f"{self.sku} - {self.product_name}"


class SalesHistory(models.Model):
    """Daily sales transactions"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    date = models.DateField(db_index=True)
    units_sold = models.IntegerField()
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_history'
        ordering = ['-date']
        unique_together = ['product', 'date']
    
    def __str__(self):
        return f"{self.product.sku} - {self.date}: {self.units_sold} units"


class InventoryLevel(models.Model):
    """Current inventory status"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    current_stock = models.IntegerField(default=0)
    warehouse_location = models.CharField(max_length=50)
    last_restock_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_levels'
    
    def __str__(self):
        return f"{self.product.sku}: {self.current_stock} units"
    
    @property
    def days_in_inventory(self):
        return (timezone.now().date() - self.last_restock_date).days


class Prediction(models.Model):
    """ML model predictions"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='predictions')
    forecast_date = models.DateField()
    predicted_units = models.FloatField()
    lower_bound = models.FloatField()
    upper_bound = models.FloatField()
    confidence_score = models.FloatField()
    model_version = models.CharField(max_length=50, default='v1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'predictions'
        ordering = ['-created_at', 'forecast_date']
        unique_together = ['product', 'forecast_date', 'created_at']
    
    def __str__(self):
        return f"{self.product.sku} - {self.forecast_date}: {self.predicted_units:.2f}"


class RiskAlert(models.Model):
    """Inventory risk alerts"""
    RISK_LEVELS = [('high', 'High Risk'), ('medium', 'Medium Risk'), ('low', 'Low Risk')]
    VELOCITY_TYPES = [('fast', 'Fast Mover'), ('medium', 'Medium Mover'), ('slow', 'Slow Mover')]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='risk_alerts')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS)
    overstock_risk_pct = models.FloatField()
    velocity = models.CharField(max_length=10, choices=VELOCITY_TYPES)
    recommended_action = models.TextField()
    urgency = models.CharField(max_length=10)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'risk_alerts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.sku} - {self.risk_level}"