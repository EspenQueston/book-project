"""
Delete DirectMessage records older than 3 months and prune empty Conversations.

Run periodically via cron:
    python manage.py cleanup_old_messages
    python manage.py cleanup_old_messages --days 60   # custom retention
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from manager import models


class Command(BaseCommand):
    help = "Delete direct messages older than 3 months and prune empty conversations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Retention period in days (default: 90).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        dry = options["dry_run"]

        old_msgs = models.DirectMessage.objects.filter(created_at__lt=cutoff)
        msg_count = old_msgs.count()

        if dry:
            self.stdout.write(f"[DRY RUN] Would delete {msg_count} messages older than {cutoff.date()}")
        else:
            old_msgs.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {msg_count} messages older than {cutoff.date()}"))

        empty_convos = models.Conversation.objects.filter(direct_messages__isnull=True)
        convo_count = empty_convos.count()

        if dry:
            self.stdout.write(f"[DRY RUN] Would prune {convo_count} empty conversations")
        else:
            empty_convos.delete()
            self.stdout.write(self.style.SUCCESS(f"Pruned {convo_count} empty conversations"))
