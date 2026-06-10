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

    vendor = Vendor.objects.filter(is_official=True).first()
    created = False
    if not vendor:
        vendor = Vendor.objects.filter(company_name=OFFICIAL_STORE_NAME).first()
        if vendor:
            vendor.is_official = True
            vendor.status = 'approved'
            vendor.is_active = True
            vendor.description = OFFICIAL_STORE_DESCRIPTION
            vendor.save()
        else:
            vendor = Vendor.objects.create(
                company_name=OFFICIAL_STORE_NAME,
                contact_name='Duno360',
                email=OFFICIAL_STORE_EMAIL,
                phone='',
                password=make_password(secrets.token_urlsafe(24)),
                description=OFFICIAL_STORE_DESCRIPTION,
                status='approved',
                is_active=True,
                is_official=True,
            )
            created = True

    if backfill:
        Product.objects.filter(vendor__isnull=True).update(vendor=vendor)
        Course.objects.filter(vendor__isnull=True).update(vendor=vendor)
        SupermarketItem.objects.filter(vendor__isnull=True).update(vendor=vendor)

        existing_book_ids = set(
            VendorBook.objects.filter(vendor=vendor).values_list('book_id', flat=True)
        )
        for book in Book.objects.exclude(id__in=existing_book_ids).iterator():
            VendorBook.objects.get_or_create(
                vendor=vendor,
                book=book,
                defaults={
                    'vendor_price': book.price,
                    'is_active': True,
                },
            )

    return vendor, created


def assign_official_vendor(instance):
    """Assign official vendor to a marketplace model instance before save."""
    vendor = get_official_vendor(create=True)
    if vendor and getattr(instance, 'vendor_id', None) is None:
        instance.vendor = vendor
    return instance
