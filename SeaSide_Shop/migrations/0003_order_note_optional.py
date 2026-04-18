from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SeaSide_Shop', '0002_order_defaults_orderitem_price_total'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='note',
            field=models.TextField(blank=True),
        ),
    ]
