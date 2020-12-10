# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0023_auto_20190107_1546'),
    ]

    operations = [
        migrations.AddField(
            model_name='comparisonset',
            name='chi2',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='comparisonset',
            name='dof',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='comparisonset',
            name='p',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
