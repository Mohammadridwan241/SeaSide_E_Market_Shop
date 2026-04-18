from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SeaSide_Shop', '0005_remove_sslcommerz_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('confirm', 'Confirm'),
                    ('processing', 'Processing'),
                    ('shipped', 'Shipped'),
                    ('delivered', 'Delivered'),
                    ('canceled', 'Canceled'),
                ],
                default='pending',
                max_length=10,
            ),
        ),
    ]
