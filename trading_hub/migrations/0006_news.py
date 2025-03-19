# Generated by Django 5.0.13 on 2025-03-19 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading_hub', '0005_asset_rename_expires_paymentmethod_expiry_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField()),
                ('source', models.CharField(max_length=100)),
                ('source_url', models.URLField()),
                ('image_url', models.URLField(blank=True, null=True)),
                ('published_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('categories', models.CharField(blank=True, max_length=255)),
                ('sentiment', models.CharField(choices=[('positive', 'Positive'), ('neutral', 'Neutral'), ('negative', 'Negative')], default='neutral', max_length=10)),
                ('featured', models.BooleanField(default=False)),
                ('related_cryptocurrencies', models.ManyToManyField(blank=True, to='trading_hub.cryptocurrency')),
            ],
            options={
                'verbose_name': 'News Article',
                'verbose_name_plural': 'News Articles',
                'ordering': ['-published_at'],
            },
        ),
    ]
