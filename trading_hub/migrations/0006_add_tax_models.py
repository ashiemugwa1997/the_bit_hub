from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trading_hub', '0005_asset_rename_expires_paymentmethod_expiry_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tax_year', models.IntegerField()),
                ('report_format', models.CharField(choices=[('csv', 'CSV'), ('pdf', 'PDF'), ('turbotax', 'TurboTax'), ('cointracker', 'CoinTracker')], default='csv', max_length=20)),
                ('include_unrealized_gains', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('report_file', models.FileField(blank=True, null=True, upload_to='tax_reports/')),
                ('error_message', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tax_reports', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TaxTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost_basis', models.DecimalField(blank=True, decimal_places=8, max_digits=24, null=True)),
                ('gain_loss', models.DecimalField(blank=True, decimal_places=8, max_digits=24, null=True)),
                ('is_long_term', models.BooleanField(blank=True, null=True)),
                ('tax_year', models.IntegerField()),
                ('tax_category', models.CharField(blank=True, max_length=50, null=True)),
                ('transaction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tax_info', to='trading_hub.transaction')),
            ],
        ),
    ]
