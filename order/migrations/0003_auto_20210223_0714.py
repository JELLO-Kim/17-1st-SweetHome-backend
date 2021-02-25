# Generated by Django 3.1.6 on 2021-02-23 07:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_auto_20210219_0056'),
        ('order', '0002_auto_20210222_1154'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderproduct',
            name='status',
        ),
        migrations.RemoveField(
            model_name='orderproduct',
            name='user',
        ),
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='order.orderstatus'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='user.user'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='recipient_address',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='recipient_name',
            field=models.CharField(max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='recipient_phone_number',
            field=models.CharField(max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='sender_email',
            field=models.CharField(max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='sender_name',
            field=models.CharField(max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='sender_phone_number',
            field=models.CharField(max_length=45, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_price',
            field=models.DecimalField(decimal_places=2, max_digits=12, null=True),
        ),
    ]
