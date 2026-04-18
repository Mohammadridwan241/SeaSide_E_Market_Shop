from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SeaSide_Shop', '0007_rename_confirmed_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='shipping_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
