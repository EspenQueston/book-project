"""
Management command: hash_manager_passwords
Migrates existing plaintext passwords in the Manager table to
PBKDF2-SHA256 hashes (Django default).

Usage:
    python manage.py hash_manager_passwords

Safe to run multiple times — already-hashed entries are skipped.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password, is_password_usable


class Command(BaseCommand):
    help = "Hash all plaintext passwords in the Manager table."

    def handle(self, *args, **options):
        from manager.models import Manager

        managers = Manager.objects.all()
        updated = 0
        skipped = 0

        for mgr in managers:
            # is_password_usable returns False for unusable markers ("!…")
            # and True for valid hashes AND for plaintext strings.
            # We detect plaintext by checking that it does NOT start with a
            # known Django hasher prefix (pbkdf2_, argon2, bcrypt, sha1$, md5$).
            known_prefixes = (
                "pbkdf2_", "argon2", "bcrypt", "sha1$", "md5$", "crypt$",
            )
            if mgr.password.startswith(known_prefixes):
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"  SKIP  {mgr.number!r} — already hashed")
                )
                continue

            # Hash the plaintext password
            hashed = make_password(mgr.password)
            Manager.objects.filter(pk=mgr.pk).update(password=hashed)
            updated += 1
            self.stdout.write(
                self.style.SUCCESS(f"  HASH  {mgr.number!r} — password hashed")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {updated} password(s) hashed, {skipped} already hashed."
            )
        )
