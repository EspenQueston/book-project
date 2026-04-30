from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0029_book_is_active_bookcategory_book_category_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFollowedVendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('followed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followed_vendors', to='manager.siteuser', verbose_name='用户')),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followers', to='manager.vendor', verbose_name='卖家')),
            ],
            options={
                'verbose_name': '关注的卖家',
                'verbose_name_plural': '关注的卖家',
                'db_table': 'user_followed_vendor',
                'ordering': ['-followed_at'],
                'unique_together': {('user', 'vendor')},
            },
        ),
    ]
