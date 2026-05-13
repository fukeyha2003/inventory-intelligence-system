"""
Billing & Subscription Management
"""

import stripe
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.inventory.models import Company

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


@login_required
def create_checkout_session(request):
    """Create Stripe Checkout session for Pro upgrade"""
    company = request.user.profile.company
    
    try:
        # Create or retrieve Stripe customer
        if not company.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=company.name,
                metadata={'company_id': company.id}
            )
            company.stripe_customer_id = customer.id
            company.save()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=company.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': 'price_1TT5r3FvYLwbUiezmunfDJfH',  # Your Stripe Price ID
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/dashboard/billing/success/'),
            cancel_url=request.build_absolute_uri('/dashboard/billing/cancel/'),
            subscription_data={
                'trial_period_days': 14,  # 14-day free trial
            },
        )
        
        return redirect(checkout_session.url)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def billing_success(request):
    """Payment successful - redirect to dashboard"""
    from django.contrib import messages
    messages.success(request, '🎉 Welcome to Pro! Your trial has started.')
    return redirect('/dashboard/overview/')


@login_required
def billing_cancel(request):
    """Payment canceled"""
    from django.contrib import messages
    messages.info(request, 'Upgrade canceled. You can upgrade anytime.')
    return redirect('/dashboard/overview/')


@login_required
def customer_portal(request):
    """Redirect to Stripe customer portal for managing subscription"""
    company = request.user.profile.company
    
    if not company.stripe_customer_id:
        return redirect('/dashboard/billing/')
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=company.stripe_customer_id,
            return_url=request.build_absolute_uri('/dashboard/billing/'),
        )
        return redirect(session.url)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.DJSTRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_complete(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_canceled(subscription)
    
    return JsonResponse({'status': 'success'})


def handle_checkout_complete(session):
    """When customer completes checkout"""
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    
    company = Company.objects.filter(stripe_customer_id=customer_id).first()
    if company:
        company.subscription_plan = 'pro'
        company.stripe_subscription_id = subscription_id
        company.subscription_status = 'active'
        company.save()


def handle_subscription_updated(subscription):
    """When subscription is updated (renewed, etc)"""
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    
    company = Company.objects.filter(stripe_customer_id=customer_id).first()
    if company:
        company.subscription_status = status
        company.subscription_current_period_end = subscription.get('current_period_end')
        company.save()


def handle_subscription_canceled(subscription):
    """When subscription is canceled"""
    customer_id = subscription.get('customer')
    
    company = Company.objects.filter(stripe_customer_id=customer_id).first()
    if company:
        company.subscription_plan = 'free'
        company.subscription_status = 'canceled'
        company.save()