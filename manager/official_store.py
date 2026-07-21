"""Duno360 Official Store — platform-owned vendor for admin inventory."""
from __future__ import annotations

import secrets

from django.contrib.auth.hashers import make_password
from django.db import transaction

OFFICIAL_STORE_NAME = 'Duno360 Official Store'
OFFICIAL_STORE_EMAIL = 'store@duno360.com'
OFFICIAL_STORE_DESCRIPTION = (
    'Duno360 官方直营店，汇集平台自营图书、商品、课程与超市精选。'
    '品质保障，官方售后，值得信赖。'
)


def _get_platform_admin_identity():
    """Return the administrator identity used to own the official platform store."""
    from manager.models import Manager

    admin = Manager.objects.filter(is_admin=True).order_by('id').first()
    if not admin:
        return 'Duno360 Admin', 'admin@duno360.com'
    label = admin.name or admin.number or 'Duno360 Admin'
    email = admin.email or OFFICIAL_STORE_EMAIL
    return label, email


def get_official_vendor(*, create: bool = False):
    """Return the platform official vendor, optionally creating it."""
    from manager.models import Vendor

    vendor = Vendor.objects.filter(is_official=True, is_active=True).first()
    if vendor:
        return vendor
    vendor = Vendor.objects.filter(company_name=OFFICIAL_STORE_NAME).first()
    if vendor:
        if not vendor.is_official:
            vendor.is_official = True
            vendor.status = 'approved'
            vendor.is_active = True
            vendor.save(update_fields=['is_official', 'status', 'is_active'])
        return vendor
    if create:
        return ensure_official_store()
    return None


def resolve_listing_vendor(vendor):
    """Use official store when listing has no vendor assigned."""
    if vendor:
        return vendor
    return get_official_vendor(create=True)


@transaction.atomic
def ensure_official_store(*, backfill: bool = True):
    """
    Create or update Duno360 Official Store and optionally backfill orphan listings.
    Returns (vendor, created_bool).
    """
    from manager.models import Vendor, VendorBook, Book
    from marketplace.models import Product, Course, SupermarketItem

    admin_name, admin_email = _get_platform_admin_identity()
    vendor = Vendor.objects.filter(is_official=True).first()
    created = False
    if not vendor:
        vendor = Vendor.objects.filter(company_name=OFFICIAL_STORE_NAME).first()
        if vendor:
            vendor.is_official = True
            vendor.status = 'approved'
            vendor.is_active = True
            vendor.description = OFFICIAL_STORE_DESCRIPTION
            created = False
        else:
            vendor = Vendor.objects.create(
                company_name=OFFICIAL_STORE_NAME,
                contact_name=admin_name,
                email=admin_email,
                phone='',
                password=make_password(secrets.token_urlsafe(24)),
                description=OFFICIAL_STORE_DESCRIPTION,
                status='approved',
                is_active=True,
                is_official=True,
            )
            created = True
    vendor.company_name = OFFICIAL_STORE_NAME
    vendor.contact_name = admin_name
    vendor.email = admin_email
    vendor.status = 'approved'
    vendor.is_active = True
    vendor.is_official = True
    vendor.is_certified = False
    vendor.certified_at = None
    vendor.description = OFFICIAL_STORE_DESCRIPTION
    vendor.user = None
    vendor.save()

    if backfill:
        Product.objects.filter(vendor__isnull=True).update(vendor=vendor)
        Course.objects.filter(vendor__isnull=True).update(vendor=vendor)
        SupermarketItem.objects.filter(vendor__isnull=True).update(vendor=vendor)

        # Only truly orphaned books (no vendor link at all) should be
        # attached to the official store. Previously this checked only
        # "not yet linked to the official vendor", which wrongly attached
        # the official store to books that already belonged to a real
        # vendor — making vendor-created books show up as admin/official
        # inventory. Books already owned by any vendor must be left alone.
        linked_book_ids = set(
            VendorBook.objects.values_list('book_id', flat=True)
        )
        for book in Book.objects.exclude(id__in=linked_book_ids).iterator():
            VendorBook.objects.get_or_create(
                vendor=vendor,
                book=book,
                defaults={'is_active': True},
            )

        fix_official_book_duplicates(vendor)

    return vendor, created


def fix_official_book_duplicates(vendor=None):
    """
    Remove stray official-store VendorBook links for books that already
    belong to a real (non-official) vendor.

    A previous version of the backfill above mistakenly linked every book
    "not yet linked to the official vendor" to the official store, even if
    the book already belonged to a real vendor — making vendor-created
    books incorrectly show up in the admin panel's official inventory.
    This repairs any data left over from that bug. Returns the number of
    stray links removed.
    """
    from manager.models import VendorBook, Vendor

    if vendor is None:
        vendor = Vendor.objects.filter(is_official=True).first()
    if not vendor:
        return 0

    real_vendor_book_ids = set(
        VendorBook.objects.exclude(vendor=vendor).values_list('book_id', flat=True)
    )
    stray = VendorBook.objects.filter(vendor=vendor, book_id__in=real_vendor_book_ids)
    count = stray.count()
    if count:
        stray.delete()
    return count


def assign_official_vendor(instance):
    """Assign official vendor to a marketplace model instance before save."""
    vendor = get_official_vendor(create=True)
    if vendor and getattr(instance, 'vendor_id', None) is None:
        instance.vendor = vendor
    return instance
