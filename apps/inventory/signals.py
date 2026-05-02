from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Company
from django.utils.text import slugify

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create user profile when user is created"""
    if created:
        # Create company if it doesn't exist (from signup form)
        company_name = getattr(instance, '_company_name', f"{instance.email}'s Company")
        company, _ = Company.objects.get_or_create(
            slug=slugify(company_name),
            defaults={'name': company_name}
        )
        
        # Create profile
        UserProfile.objects.create(
            user=instance,
            company=company,
            role='admin'  # First user is admin
        )