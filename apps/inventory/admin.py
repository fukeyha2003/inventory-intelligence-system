from django.contrib import admin
from .models import Product, SalesHistory, InventoryLevel, Prediction, RiskAlert

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'product_name', 'category', 'price', 'season']
    search_fields = ['sku', 'product_name']
    list_filter = ['category', 'season']

@admin.register(SalesHistory)
class SalesHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'date', 'units_sold', 'revenue']
    list_filter = ['date']
    date_hierarchy = 'date'

@admin.register(InventoryLevel)
class InventoryLevelAdmin(admin.ModelAdmin):
    list_display = ['product', 'current_stock', 'warehouse_location', 'days_in_inventory']

admin.site.register(Prediction)
admin.site.register(RiskAlert)