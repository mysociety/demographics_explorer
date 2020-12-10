# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-30 14:36


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0004_auto_20180329_1520'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparisonlabel',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='labels', to='explorer.ComparisonSuperSet'),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sets', to='explorer.ComparisonSuperSet'),
        ),
    ]
