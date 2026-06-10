# Generated manually for platform escrow & vendor wallet

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0035_siteuser_role_required_phone'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformEscrowTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_ref', models.CharField(max_length=40, unique=True, verbose_name='ID transaction escrow')),
                ('order_source', models.CharField(choices=[('book', 'Commande livre'), ('marketplace', 'Commande marketplace')], max_length=20, verbose_name='Source commande')),
                ('order_id', models.PositiveIntegerField(verbose_name='ID commande')),
                ('order_number', models.CharField(db_index=True, max_length=32, verbose_name='N° commande')),
                ('order_item_id', models.PositiveIntegerField(verbose_name='ID ligne commande')),
                ('buyer_user_id', models.IntegerField(blank=True, null=True, verbose_name='ID acheteur')),
                ('buyer_email', models.EmailField(max_length=254, verbose_name='Email acheteur')),
                ('buyer_name', models.CharField(blank=True, default='', max_length=100, verbose_name='Nom acheteur')),
                ('item_type', models.CharField(choices=[('book', 'Livre'), ('product', 'Boutique'), ('course', 'Cours'), ('supermarket', 'Supermarché')], max_length=20, verbose_name='Type article')),
                ('item_id', models.PositiveIntegerField(verbose_name='ID article')),
                ('item_name', models.CharField(max_length=200, verbose_name='Nom article')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Quantité')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Prix unitaire')),
                ('gross_amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Montant brut')),
                ('commission_rate', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Commission (%)')),
                ('commission_amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Montant commission')),
                ('vendor_payout_amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Net vendeur')),
                ('payment_transaction_id', models.CharField(blank=True, default='', max_length=100, verbose_name='Réf. paiement externe')),
                ('status', models.CharField(choices=[('held', 'En attente (escrow)'), ('releasable', 'Éligible au reversement'), ('released', 'Reversé au vendeur'), ('refunded', 'Remboursé'), ('cancelled', 'Annulé')], default='held', max_length=20, verbose_name='Statut escrow')),
                ('held_at', models.DateTimeField(auto_now_add=True, verbose_name='Date réception plateforme')),
                ('delivered_at', models.DateTimeField(blank=True, null=True, verbose_name='Date livraison confirmée')),
                ('release_eligible_at', models.DateTimeField(blank=True, null=True, verbose_name='Éligible reversement après')),
                ('released_at', models.DateTimeField(blank=True, null=True, verbose_name='Date reversement vendeur')),
                ('notes', models.TextField(blank=True, default='', verbose_name='Notes')),
                ('vendor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='escrow_transactions', to='manager.vendor', verbose_name='Vendeur')),
            ],
            options={
                'verbose_name': 'Transaction escrow',
                'verbose_name_plural': 'Transactions escrow',
                'db_table': 'platform_escrow_transaction',
                'ordering': ['-held_at'],
            },
        ),
        migrations.CreateModel(
            name='VendorWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Solde')),
                ('total_earned', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Total gagné')),
                ('total_paid_out', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Total retiré')),
                ('is_active', models.BooleanField(default=True, verbose_name='Actif')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vendor', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to='manager.vendor', verbose_name='Vendeur')),
            ],
            options={
                'verbose_name': 'Portefeuille vendeur',
                'verbose_name_plural': 'Portefeuilles vendeur',
                'db_table': 'vendor_wallet',
            },
        ),
        migrations.CreateModel(
            name='VendorWalletTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Montant')),
                ('txn_type', models.CharField(choices=[('credit', 'Crédit'), ('debit', 'Débit'), ('payout', 'Retrait')], max_length=20, verbose_name='Type')),
                ('source', models.CharField(choices=[('escrow_release', 'Reversement escrow'), ('admin_adjust', 'Ajustement admin'), ('payout_request', 'Demande retrait')], max_length=30, verbose_name='Source')),
                ('description', models.CharField(blank=True, default='', max_length=255, verbose_name='Description')),
                ('source_id', models.CharField(blank=True, default='', max_length=50, verbose_name='Réf. liée')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_transactions', to='manager.vendor', verbose_name='Vendeur')),
            ],
            options={
                'verbose_name': 'Mouvement portefeuille vendeur',
                'verbose_name_plural': 'Mouvements portefeuille vendeur',
                'db_table': 'vendor_wallet_transaction',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='platformescrowtransaction',
            constraint=models.UniqueConstraint(fields=('order_source', 'order_item_id'), name='uniq_escrow_order_line'),
        ),
        migrations.AddIndex(
            model_name='platformescrowtransaction',
            index=models.Index(fields=['vendor', 'status'], name='platform_es_vendor__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='platformescrowtransaction',
            index=models.Index(fields=['order_number'], name='platform_es_order_n_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='platformescrowtransaction',
            index=models.Index(fields=['buyer_email'], name='platform_es_buyer_e_g7h8i9_idx'),
        ),
    ]
