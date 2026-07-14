"""Password hashing and account-linking helpers for the custom SiteUser/
Vendor auth system (this project does not use Django's built-in User model).

Passwords are hashed with Django's own make_password/check_password —
PBKDF2 by default, a random salt generated per password, and a tunable
iteration count — instead of a hand-rolled hasher. Accounts created before
this change stored a single hardcoded-salt SHA-256 digest (a fast hash,
with one salt shared by every user, sitting in source control) — those are
verified once via the old method on their next login attempt and
transparently re-hashed with the secure format at that point, so no forced
password reset is needed and no account is left on the weaker hash after
they've successfully logged in even once post-migration.
"""
import hashlib

from django.contrib.auth.hashers import check_password as _django_check_password
from django.contrib.auth.hashers import make_password as _django_make_password
from django.utils import timezone

from manager import models

_LEGACY_SALT = 'book_project_salt_2024'


def _legacy_hash(password):
    return hashlib.sha256(f'{_LEGACY_SALT}{password}'.encode()).hexdigest()


def _is_legacy_hash(value):
    """Legacy hashes are bare 64-char hex SHA-256 digests. Django's
    make_password output always contains '$' (e.g. 'pbkdf2_sha256$...'),
    so the two formats are unambiguous."""
    return bool(value) and '$' not in value and len(value) == 64


def hash_password(password):
    """Hash a NEW password. Always the secure Django hasher — the legacy
    one below exists only to verify passwords hashed before this change."""
    return _django_make_password(password)


def verify_password(raw_password, stored_hash):
    """True if raw_password matches stored_hash, in whichever format it's in."""
    if not stored_hash or not raw_password:
        return False
    if _is_legacy_hash(stored_hash):
        return _legacy_hash(raw_password) == stored_hash
    return _django_check_password(raw_password, stored_hash)


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
    """Return True if password matches SiteUser and/or Vendor; heal
    password drift and transparently upgrade a legacy hash to the secure
    format the moment it's confirmed correct."""
    email_key = normalize_auth_email(email)
    if not email_key or not raw_password:
        return False
    user, vendor = get_linked_site_user_and_vendor(email_key)
    user_ok = bool(user) and verify_password(raw_password, user.password)
    vendor_ok = bool(vendor) and verify_password(raw_password, vendor.password)
    if not (user_ok or vendor_ok):
        return False

    # Re-hash with the secure format now that the password is confirmed
    # correct — a no-op (no rows changed) if it's already on the new
    # format, and a transparent upgrade if it was still the legacy hash.
    sync_password_by_email(email_key, hash_password(raw_password))
    return True


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
