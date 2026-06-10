import hashlib

from django.utils import timezone

from manager import models


def hash_password(password):
    salt = 'book_project_salt_2024'
    return hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()


def normalize_auth_email(email):
    return (email or '').strip().lower()


def get_linked_site_user_and_vendor(email):
    """Return (site_user, vendor) for an email, including user↔vendor FK links."""
    email_key = normalize_auth_email(email)
    if not email_key:
        return None, None
    user = models.SiteUser.objects.filter(email__iexact=email_key, is_active=True).first()
    vendor = models.Vendor.objects.filter(email__iexact=email_key, is_active=True).first()
    if user and not vendor:
        vendor = models.Vendor.objects.filter(user_id=user.id, is_active=True).first()
    if vendor and not user and vendor.user_id:
        user = models.SiteUser.objects.filter(id=vendor.user_id, is_active=True).first()
    return user, vendor


def sync_password_by_email(email, hashed_password):
    """Keep SiteUser and Vendor password hashes aligned for dual-role accounts."""
    email_key = normalize_auth_email(email)
    if not email_key or not hashed_password:
        return 0
    user, vendor = get_linked_site_user_and_vendor(email_key)
    user_ids = set(models.SiteUser.objects.filter(email__iexact=email_key).values_list('id', flat=True))
    vendor_ids = set(models.Vendor.objects.filter(email__iexact=email_key).values_list('id', flat=True))
    if user:
        user_ids.add(user.id)
        vendor_ids.update(
            models.Vendor.objects.filter(user_id=user.id).values_list('id', flat=True)
        )
    if vendor:
        vendor_ids.add(vendor.id)
        if vendor.user_id:
            user_ids.add(vendor.user_id)
    updated = models.SiteUser.objects.filter(
        id__in=user_ids, is_active=True,
    ).exclude(password=hashed_password).update(password=hashed_password, updated_at=timezone.now())
    updated += models.Vendor.objects.filter(
        id__in=vendor_ids, is_active=True,
    ).exclude(password=hashed_password).update(password=hashed_password, updated_at=timezone.now())
    return updated


def set_unified_password(email, raw_password):
    hashed = hash_password(raw_password)
    sync_password_by_email(email, hashed)
    return hashed


def check_email_password(email, raw_password):
    """Return True if password matches SiteUser and/or Vendor; heal password drift."""
    email_key = normalize_auth_email(email)
    if not email_key or not raw_password:
        return False
    hashed = hash_password(raw_password)
    user, vendor = get_linked_site_user_and_vendor(email_key)
    user_ok = user and user.password == hashed
    vendor_ok = vendor and vendor.password == hashed
    if user_ok or vendor_ok:
        sync_password_by_email(email_key, hashed)
        return True
    return False


def link_dual_accounts_by_email(email):
    """Link Vendor.user when emails match and promote buyer to seller."""
    email_key = normalize_auth_email(email)
    user, vendor = get_linked_site_user_and_vendor(email_key)
    if not user or not vendor:
        return
    changed = []
    if vendor.user_id != user.id:
        vendor.user = user
        changed.append('user')
    if vendor.password != user.password:
        vendor.password = user.password
        changed.append('password')
    if changed:
        vendor.save(update_fields=changed + ['updated_at'])
    user.promote_to_seller()
