# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0005_auto_20180430_1536'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
