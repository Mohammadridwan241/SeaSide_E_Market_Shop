from django.db import migrations, models


def migrate_payment_methods_to_cod(apps, schema_editor):
    Order = apps.get_model('SeaSide_Shop', 'Order')
    Order.objects.filter(payment_method='sslcommerz').update(payment_method='cod')


class Migration(migrations.Migration):

    dependencies = [
        ('SeaSide_Shop', '0004_order_payment_method'),
    ]

    operations = [
        migrations.RunPython(migrate_payment_methods_to_cod, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[('cod', 'Cash on Delivery')],
                default='cod',
                max_length=20,
            ),
        ),
    ]
