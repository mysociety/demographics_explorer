# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0016_auto_20180629_1022'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
