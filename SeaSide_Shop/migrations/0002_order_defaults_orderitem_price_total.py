# Generated manually to align required order fields with checkout behavior.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SeaSide_Shop', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='phone',
            field=models.CharField(blank=True, max_length=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('processing', 'Processing'),
                    ('shipped', 'Shipped'),
                    ('delivered', 'Delivered'),
                    ('canceled', 'Canceled'),
                ],
                default='pending',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='transaction_id',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
