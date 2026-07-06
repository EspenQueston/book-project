# -*- coding: utf-8 -*-
"""Backfill existing AutoReplySettings rows so welcome/away are enabled with the
bilingual FR+EN default messages — but only where the message is blank or still
holds a known old placeholder (Chinese default). Genuinely custom vendor/admin
text is preserved untouched."""
from django.db import migrations

NEW_WELCOME = (
    "Bonjour et bienvenue chez DUNO 360 ! Merci de nous avoir contactés, nous avons bien reçu "
    "votre message et nous vous répondrons très rapidement.\n\n"
    "Hello and welcome to DUNO 360! Thank you for contacting us — we've received your message "
    "and will get back to you very soon."
)
NEW_AWAY = (
    "Bonjour, nous ne sommes pas disponibles pour le moment et répondons généralement sous "
    "10 minutes. Merci de votre patience, nous revenons vers vous très vite !\n\n"
    "Hello, we're currently unavailable and usually reply within 10 minutes. Thank you for "
    "your patience — we'll get back to you shortly!"
)

# Old Chinese placeholder defaults that shipped briefly before the bilingual rewrite.
OLD_ZH_WELCOME = (
    '您好，欢迎光临 DUNO 360！感谢您的咨询，我们已收到您的消息，会尽快为您处理，请稍候片刻。'
)
OLD_ZH_AWAY = (
    '您好，我们暂时不在线，通常会在10分钟内回复您。感谢您的耐心等待，我们会尽快与您联系！'
)


def backfill(apps, schema_editor):
    AutoReplySettings = apps.get_model('manager', 'AutoReplySettings')
    for row in AutoReplySettings.objects.all():
        changed = False
        if (row.welcome_message or '').strip() in ('', OLD_ZH_WELCOME):
            row.welcome_message = NEW_WELCOME
            changed = True
        if (row.away_message or '').strip() in ('', OLD_ZH_AWAY):
            row.away_message = NEW_AWAY
            changed = True
        # Enable both by default (matches the model default); the delay stays as-is.
        if not row.welcome_enabled:
            row.welcome_enabled = True
            changed = True
        if not row.away_enabled:
            row.away_enabled = True
            changed = True
        if not row.away_delay_minutes:
            row.away_delay_minutes = 10
            changed = True
        if changed:
            row.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0055_alter_autoreplysettings_away_enabled_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
