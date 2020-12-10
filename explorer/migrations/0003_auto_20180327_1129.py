# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0002_auto_20180323_1640'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectiontype',
            name='default',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
