# Generated by Django 3.1.6 on 2021-02-18 01:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
        ('posting', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='posting',
            name='like_user',
            field=models.ManyToManyField(related_name='posting_like_user', through='posting.PostingLike', to='user.User'),
        ),
    ]