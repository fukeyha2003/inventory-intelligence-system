"""
Dashboard Views - Fashion Inventory Intelligence
Multi-tenant: Each company sees ONLY their own data
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Avg, Count
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.contrib import messages
from datetime import datetime, timedelta
import pandas as pd
import csv
import io

from apps.inventory.models import (
    Product, SalesHistory, InventoryLevel,
    Prediction, RiskAlert, Company, UserProfile
)


# ============================================================================
# HELPER: Get company from logged-in user
# ============================================================================

def get_user_company(request):
    """Get the company of the logged-in user"""
    try:
        return request.user.profile.company
    except Exception:
        return None


# ============================================================================
# HOME PAGE
# ============================================================================

def home(request):
    """Homepage - redirect to dashboard if logged in"""
    if request.user.is_authenticated:
        return redirect('/dashboard/overview/')
    return render(request, 'dashboard/home.html')


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def signup_view(request):
    """Custom signup - redirects to homepage modal if not POST"""
    if request.user.is_authenticated:
        return redirect('/dashboard/overview/')

    if request.method == 'POST':
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        company_name = request.POST.get('company_name')

        from urllib.parse import urlencode

        # Validate
        if not company_name:
            params = urlencode({'show': 'signup', 'error': 'Company name is required.'})
            return redirect(f'/?{params}')

        if not email:
            params = urlencode({'show': 'signup', 'error': 'Email is required.'})
            return redirect(f'/?{params}')

        if password1 != password2:
            params = urlencode({'show': 'signup', 'error': 'Passwords do not match.'})
            return redirect(f'/?{params}')

        if len(password1) < 8:
            params = urlencode({'show': 'signup', 'error': 'Password must be at least 8 characters.'})
            return redirect(f'/?{params}')

        if User.objects.filter(email=email).exists():
            params = urlencode({'show': 'signup', 'error': 'This email is already registered. Please sign in.'})
            return redirect(f'/?{params}')

        try:
            # Create user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password1
            )

            # Create company with unique slug
            base_slug = slugify(company_name)
            slug = base_slug
            counter = 1
            while Company.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            company = Company.objects.create(
                name=company_name,
                slug=slug,
                subscription_plan='free'
            )

            # Create profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'company': company, 'role': 'admin'}
            )
            if not created:
                profile.company = company
                profile.role = 'admin'
                profile.save()

            # Log in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            return redirect('/dashboard/overview/')

        except Exception as e:
            params = urlencode({'show': 'signup', 'error': f'Error: {str(e)}'})
            return redirect(f'/?{params}')

    # GET request → redirect to homepage with modal open
    return redirect('/?show=signup')


def login_view(request):
    """Custom login - redirects to homepage modal if not POST"""
    if request.user.is_authenticated:
        return redirect('/dashboard/overview/')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user:
            login(request, user)
            return redirect('/dashboard/overview/')
        else:
            from urllib.parse import urlencode
            params = urlencode({
                'show': 'login',
                'error': 'Invalid email or password. Please try again.'
            })
            return redirect(f'/?{params}')

    # GET request → redirect to homepage with modal open
    return redirect('/?show=login')


def logout_view(request):
    """Logout and redirect to homepage"""
    logout(request)
    return redirect('/')


# ============================================================================
# DASHBOARD PAGES (All filtered by company!)
# ============================================================================

@login_required
def executive_overview(request):
    """KPI dashboard - filtered by user's company"""
    company = get_user_company(request)

    if not company:
        return redirect('/')

    # Date ranges
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)

    # KPIs - filtered by company
    total_products = Product.objects.filter(company=company).count()

    total_inventory = InventoryLevel.objects.filter(
        product__company=company
    ).aggregate(total=Sum('current_stock'))['total'] or 0

    # Revenue - filtered by company
    recent_sales = SalesHistory.objects.filter(
        product__company=company,
        date__gte=last_30_days
    ).aggregate(
        total_revenue=Sum('revenue'),
        total_units=Sum('units_sold')
    )

    # Risk breakdown - filtered by company
    risk_summary = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False
    ).values('risk_level').annotate(count=Count('id'))

    risk_counts = {'high': 0, 'medium': 0, 'low': 0}
    for item in risk_summary:
        risk_counts[item['risk_level']] = item['count']

    # Velocity breakdown - filtered by company
    velocity_summary = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False
    ).values('velocity').annotate(count=Count('id'))

    velocity_counts = {'fast': 0, 'medium': 0, 'slow': 0}
    for item in velocity_summary:
        velocity_counts[item['velocity']] = item['count']

    # Forecasts - filtered by company
    recent_forecasts = Prediction.objects.filter(
        product__company=company,
        created_at__gte=last_7_days
    ).count()

    avg_confidence = Prediction.objects.filter(
        product__company=company,
        created_at__gte=last_30_days
    ).aggregate(avg=Avg('confidence_score'))['avg'] or 0

    context = {
        'company': company,
        'total_products': total_products,
        'total_inventory': total_inventory,
        'revenue_30d': recent_sales['total_revenue'] or 0,
        'units_sold_30d': recent_sales['total_units'] or 0,
        'high_risk_count': risk_counts['high'],
        'medium_risk_count': risk_counts['medium'],
        'low_risk_count': risk_counts['low'],
        'fast_movers': velocity_counts['fast'],
        'medium_movers': velocity_counts['medium'],
        'slow_movers': velocity_counts['slow'],
        'recent_forecasts_count': recent_forecasts,
        'avg_confidence': round(avg_confidence * 100, 1),
    }

    return render(request, 'dashboard/overview.html', context)


@login_required
def forecast_explorer(request):
    """Forecast explorer - filtered by company"""
    company = get_user_company(request)

    if not company:
        return redirect('/')

    category = request.GET.get('category')

    # Only show this company's products
    products_query = Product.objects.filter(company=company)

    if category:
        products_query = products_query.filter(category=category)

    products_with_forecasts = products_query.filter(
        predictions__isnull=False
    ).distinct()[:50]

    # Only show categories for this company
    categories = Product.objects.filter(
        company=company
    ).values_list('category', flat=True).distinct()

    # Count products with forecasts
    forecast_count = Product.objects.filter(
        company=company,
        predictions__isnull=False
    ).distinct().count()

    context = {
        'company': company,
        'products': products_with_forecasts,
        'categories': categories,
        'selected_category': category,
        'forecast_count': forecast_count,
    }

    return render(request, 'dashboard/forecasts.html', context)


@login_required
def risk_monitor(request):
    """Risk monitor - filtered by company"""
    company = get_user_company(request)

    if not company:
        return redirect('/')

    risk_level = request.GET.get('risk_level', 'all')
    urgency = request.GET.get('urgency')

    # Only show this company's alerts
    alerts_query = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False
    ).select_related('product').order_by('-overstock_risk_pct')

    if risk_level != 'all':
        alerts_query = alerts_query.filter(risk_level=risk_level)

    if urgency:
        alerts_query = alerts_query.filter(urgency=urgency)

    alerts = alerts_query[:100]

    # Count by urgency
    critical_count = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False,
        urgency='Critical'
    ).count()

    high_risk_count = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False,
        risk_level='high'
    ).count()

    medium_risk_count = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False,
        risk_level='medium'
    ).count()

    low_risk_count = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False,
        risk_level='low'
    ).count()

    context = {
        'company': company,
        'alerts': alerts,
        'critical_count': critical_count,
        'high_risk_count': high_risk_count,
        'medium_risk_count': medium_risk_count,
        'low_risk_count': low_risk_count,
    }

    return render(request, 'dashboard/risk_monitor.html', context)


@login_required
def recommendations(request):
    """Recommendations - filtered by company"""
    company = get_user_company(request)

    if not company:
        return redirect('/')

    # Get ALL alerts first, THEN filter (no slice before filter!)
    base_alerts = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False
    ).select_related('product').order_by('-created_at')

    # Filter BEFORE slicing
    critical_actions = base_alerts.filter(urgency='Critical')[:20]
    high_priority = base_alerts.filter(urgency='High')[:20]
    medium_priority = base_alerts.filter(urgency='Medium')[:20]
    total_recommendations = base_alerts.count()

    context = {
        'company': company,
        'critical_actions': critical_actions,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'total_recommendations': total_recommendations,
    }

    return render(request, 'dashboard/recommendations.html', context)


# ============================================================================
# CSV UPLOAD & DATA MANAGEMENT
# ============================================================================

@login_required
def upload_data(request):
    """CSV upload page for companies to import their data"""
    company = get_user_company(request)

    if not company:
        return redirect('/')

    context = {
        'company': company,
        'products_count': Product.objects.filter(company=company).count(),
        'sales_count': SalesHistory.objects.filter(
            product__company=company
        ).count(),
        'inventory_count': InventoryLevel.objects.filter(
            product__company=company
        ).count(),
    }

    return render(request, 'dashboard/upload.html', context)


@login_required
def upload_products_csv(request):
    """Handle products CSV upload"""
    company = get_user_company(request)

    if request.method != 'POST':
        return redirect('/dashboard/upload/')

    if 'file' not in request.FILES:
        messages.error(request, 'No file uploaded')
        return redirect('/dashboard/upload/')

    csv_file = request.FILES['file']

    # Validate file type
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file')
        return redirect('/dashboard/upload/')

    try:
        # Read CSV
        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        reader = csv.DictReader(io_string)

        created_count = 0
        updated_count = 0
        error_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                # Clean row data
                row = {k.strip(): v.strip() for k, v in row.items()}

                # Required fields check
                required = ['product_id', 'product_name', 'category', 'price']
                missing = [f for f in required if not row.get(f)]
                if missing:
                    errors.append(f"Row {row_num}: Missing fields: {missing}")
                    error_count += 1
                    continue

                # Create or update product
                product, created = Product.objects.update_or_create(
                    company=company,
                    sku=row['product_id'],
                    defaults={
                        'product_name': row.get('product_name', ''),
                        'category': row.get('category', 'General'),
                        'subcategory': row.get('subcategory', 'General'),
                        'color': row.get('color', 'N/A'),
                        'size': row.get('size', 'N/A'),
                        'season': row.get('season', 'All Season'),
                        'price': float(row.get('price', 0)),
                        'cost': float(row.get('cost', 0)),
                        'launch_date': pd.to_datetime(
                            row.get('launch_date', '2024-01-01')
                        ).date(),
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Row {row_num}: {str(e)}")

        # Success message
        messages.success(
            request,
            f'✅ Products uploaded! '
            f'{created_count} created, '
            f'{updated_count} updated, '
            f'{error_count} errors'
        )

        if errors[:5]:  # Show first 5 errors
            for error in errors[:5]:
                messages.warning(request, error)

    except Exception as e:
        messages.error(request, f'Error reading file: {str(e)}')

    return redirect('/dashboard/upload/')


@login_required
def upload_sales_csv(request):
    """Handle sales history CSV upload"""
    company = get_user_company(request)

    if request.method != 'POST':
        return redirect('/dashboard/upload/')

    if 'file' not in request.FILES:
        messages.error(request, 'No file uploaded')
        return redirect('/dashboard/upload/')

    csv_file = request.FILES['file']

    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file')
        return redirect('/dashboard/upload/')

    try:
        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        reader = csv.DictReader(io_string)

        batch = []
        created_count = 0
        error_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v.strip() for k, v in row.items()}

                # Get product - must belong to this company
                product = Product.objects.get(
                    company=company,
                    sku=row['product_id']
                )

                batch.append(SalesHistory(
                    product=product,
                    date=pd.to_datetime(row['date']).date(),
                    units_sold=int(row.get('units_sold', 0)),
                    revenue=float(row.get('revenue', 0)),
                    discount_rate=float(row.get('discount_rate', 0))
                ))

                created_count += 1

                # Bulk create every 1000 records
                if len(batch) >= 1000:
                    SalesHistory.objects.bulk_create(
                        batch,
                        ignore_conflicts=True
                    )
                    batch = []

            except Product.DoesNotExist:
                error_count += 1
                errors.append(
                    f"Row {row_num}: Product {row.get('product_id')} not found. "
                    f"Upload products first!"
                )
            except Exception as e:
                error_count += 1
                errors.append(f"Row {row_num}: {str(e)}")

        # Create remaining records
        if batch:
            SalesHistory.objects.bulk_create(batch, ignore_conflicts=True)

        messages.success(
            request,
            f'✅ Sales data uploaded! '
            f'{created_count} records processed, '
            f'{error_count} errors'
        )

        if errors[:5]:
            for error in errors[:5]:
                messages.warning(request, error)

    except Exception as e:
        messages.error(request, f'Error reading file: {str(e)}')

    return redirect('/dashboard/upload/')


@login_required
def upload_inventory_csv(request):
    """Handle inventory CSV upload"""
    company = get_user_company(request)

    if request.method != 'POST':
        return redirect('/dashboard/upload/')

    if 'file' not in request.FILES:
        messages.error(request, 'No file uploaded')
        return redirect('/dashboard/upload/')

    csv_file = request.FILES['file']

    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file')
        return redirect('/dashboard/upload/')

    try:
        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        reader = csv.DictReader(io_string)

        created_count = 0
        error_count = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                row = {k.strip(): v.strip() for k, v in row.items()}

                product = Product.objects.get(
                    company=company,
                    sku=row['product_id']
                )

                InventoryLevel.objects.update_or_create(
                    product=product,
                    defaults={
                        'current_stock': int(row.get('current_stock', 0)),
                        'warehouse_location': row.get(
                            'warehouse_location', 'Main Warehouse'
                        ),
                        'last_restock_date': pd.to_datetime(
                            row.get('last_restock_date', '2024-01-01')
                        ).date(),
                    }
                )
                created_count += 1

            except Product.DoesNotExist:
                error_count += 1
            except Exception as e:
                error_count += 1

        messages.success(
            request,
            f'✅ Inventory uploaded! '
            f'{created_count} records updated, '
            f'{error_count} errors'
        )

    except Exception as e:
        messages.error(request, f'Error reading file: {str(e)}')

    return redirect('/dashboard/upload/')


@login_required
def generate_analysis(request):
    """Generate forecasts and risk analysis for company's data"""
    company = get_user_company(request)

    if request.method != 'POST':
        return redirect('/dashboard/upload/')

    try:
        from ml_engine.models import MultiProductForecaster
        from ml_engine.risk_calculator import InventoryHealthAnalyzer

        # ── 1. Check data exists ──────────────────────────────────
        products_count = Product.objects.filter(company=company).count()
        sales_count = SalesHistory.objects.filter(
            product__company=company
        ).count()

        if products_count == 0:
            messages.error(request, '❌ No products found! Upload products CSV first.')
            return redirect('/dashboard/upload/')

        if sales_count == 0:
            messages.error(request, '❌ No sales data found! Upload sales history CSV first.')
            return redirect('/dashboard/upload/')

        # ── 2. Load data ──────────────────────────────────────────
        sales_df = pd.DataFrame(
            SalesHistory.objects.filter(
                product__company=company
            ).values('date', 'product__sku', 'units_sold')
        )
        sales_df.rename(
            columns={'product__sku': 'product_id'},
            inplace=True
        )

        inventory_df = pd.DataFrame(
            InventoryLevel.objects.filter(
                product__company=company
            ).values('product__sku', 'current_stock', 'last_restock_date')
        )
        inventory_df.rename(
            columns={'product__sku': 'product_id'},
            inplace=True
        )

        products_df = pd.DataFrame(
            Product.objects.filter(company=company).values(
                'sku', 'product_name', 'category',
                'season', 'subcategory', 'price'
            )
        )
        products_df.rename(columns={'sku': 'product_id'}, inplace=True)
        product_ids = products_df['product_id'].tolist()

        # ── 3. Generate forecasts ─────────────────────────────────
        forecaster = MultiProductForecaster()
        forecaster.train_all(sales_df, product_ids)
        forecast_df = forecaster.predict_all(periods=30)

        # ── 4. Save predictions to database ──────────────────────
        # Delete old predictions for this company
        Prediction.objects.filter(
            product__company=company
        ).delete()

        pred_saved = 0

        for _, frow in forecast_df.iterrows():
            try:
                product = Product.objects.get(
                    company=company,
                    sku=frow['product_id']
                )

                # Generate daily predictions
                today = datetime.now().date()
                avg_daily = frow['total_predicted_units'] / 30

                for day in range(30):
                    forecast_date = today + timedelta(days=day+1)
                    variation = avg_daily * 0.1

                    Prediction.objects.update_or_create(
                        product=product,
                        forecast_date=forecast_date,
                        defaults={
                            'predicted_units': max(0, round(avg_daily, 2)),
                            'lower_bound': max(0, round(avg_daily - variation, 2)),
                            'upper_bound': round(avg_daily + variation, 2),
                            'confidence_score': round(
                                frow.get('confidence_score', 0.65), 2
                            ),
                            'model_version': 'v1.0'
                        }
                    )
                    pred_saved += 1

            except Exception as e:
                pass

        # ── 5. Analyze risks ──────────────────────────────────────
        analyzer = InventoryHealthAnalyzer()
        analysis = analyzer.analyze_inventory(
            inventory_df, sales_df, forecast_df, products_df
        )

        # ── 6. Save risk alerts ───────────────────────────────────
        # Delete old alerts for this company
        RiskAlert.objects.filter(
            product__company=company
        ).delete()

        risk_map = {
            'High Risk': 'high',
            'Medium Risk': 'medium',
            'Low Risk': 'low'
        }
        vel_map = {
            'Fast Mover': 'fast',
            'Medium Mover': 'medium',
            'Slow Mover': 'slow'
        }

        alert_count = 0
        high_risk = 0

        for _, row in analysis.iterrows():
            try:
                product = Product.objects.get(
                    company=company,
                    sku=row['product_id']
                )
                risk_level = risk_map.get(row['risk_level'], 'low')

                RiskAlert.objects.create(
                    product=product,
                    risk_level=risk_level,
                    overstock_risk_pct=row['overstock_risk_pct'],
                    velocity=vel_map.get(row['velocity'], 'medium'),
                    recommended_action=row['recommended_action'],
                    urgency=row['urgency']
                )
                alert_count += 1

                if risk_level == 'high':
                    high_risk += 1

            except Exception as e:
                pass

        # ── 7. Success message ────────────────────────────────────
        messages.success(
            request,
            f'✅ Analysis complete for {company.name}! '
            f'{pred_saved} forecasts saved, '
            f'{alert_count} risk alerts generated '
            f'({high_risk} high risk products found)'
        )

    except Exception as e:
        messages.error(
            request,
            f'❌ Error generating analysis: {str(e)}. '
            f'Make sure you have uploaded products and sales data.'
        )

    return redirect('/dashboard/upload/')


# ============================================================================
# API ENDPOINTS FOR CHARTS (All filtered by company!)
# ============================================================================


@login_required
@require_http_methods(["GET"])
def api_revenue_trend(request):
    """Revenue trend - Gets most recent 30 days of available sales data"""
    company = get_user_company(request)

    if not company:
        return JsonResponse({'labels': [], 'revenue': [], 'units': []})

    # Get the most recent sales date for this company
    latest_sale = SalesHistory.objects.filter(
        product__company=company
    ).order_by('-date').first()

    if not latest_sale:
        # No sales data at all
        return JsonResponse({'labels': [], 'revenue': [], 'units': []})

    # Use the latest sale date as end date (not today's date)
    end_date = latest_sale.date
    start_date = end_date - timedelta(days=29)  # 30 days total

    daily_data = SalesHistory.objects.filter(
        product__company=company,
        date__gte=start_date,
        date__lte=end_date
    ).values('date').annotate(
        revenue=Sum('revenue'),
        units=Sum('units_sold')
    ).order_by('date')

    # Create complete date range (fill gaps with zeros)
    date_range = [start_date + timedelta(days=x) for x in range(30)]
    sales_dict = {item['date']: item for item in daily_data}

    labels = [d.strftime('%b %d') for d in date_range]
    revenue = [float(sales_dict.get(d, {}).get('revenue', 0) or 0) for d in date_range]
    units = [int(sales_dict.get(d, {}).get('units', 0) or 0) for d in date_range]

    return JsonResponse({
        'labels': labels,
        'revenue': revenue,
        'units': units
    })


@login_required
@require_http_methods(["GET"])
def api_risk_distribution(request):
    """Risk level distribution - high/medium/low counts - FIXED"""
    company = get_user_company(request)

    if not company:
        return JsonResponse({'high': 0, 'medium': 0, 'low': 0})

    risk_counts = RiskAlert.objects.filter(
        product__company=company,
        is_resolved=False
    ).values('risk_level').annotate(count=Count('id'))

    result = {'high': 0, 'medium': 0, 'low': 0}
    for r in risk_counts:
        result[r['risk_level']] = r['count']

    return JsonResponse(result)

@login_required
@require_http_methods(["GET"])
def api_product_forecast(request, sku):
    """Forecast for specific product - FIXED FORMAT"""
    company = get_user_company(request)

    if not company:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    product = Product.objects.filter(company=company, sku=sku).first()
    
    if not product:
        return JsonResponse({'error': 'Product not found'}, status=404)

    # Simply get the latest 30 forecasts, ordered by date
    forecasts = Prediction.objects.filter(
        product=product
    ).order_by('forecast_date')[:30]

    if not forecasts:
        return JsonResponse({'error': 'No forecasts available'}, status=404)

    labels = [f.forecast_date.strftime('%b %d') for f in forecasts]
    predicted = [float(f.predicted_units) for f in forecasts]
    upper = [float(f.upper_bound) for f in forecasts]
    lower = [float(f.lower_bound) for f in forecasts]
    
    avg_confidence = sum(f.confidence_score for f in forecasts) / len(forecasts) if forecasts else 0

    return JsonResponse({
        'product_name': product.product_name,
        'labels': labels,
        'predicted': predicted,
        'upper': upper,
        'lower': lower,
        'confidence': avg_confidence
    })

# ============================================================================
# API DOCUMENTATION
# ============================================================================

def api_documentation(request):
    """API documentation page"""
    return render(request, 'dashboard/api_docs.html')