from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SeaSide_Shop', '0003_order_note_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[('sslcommerz', 'SSLCommerz'), ('cod', 'Cash on Delivery')],
                default='sslcommerz',
                max_length=20,
            ),
        ),
    ]
