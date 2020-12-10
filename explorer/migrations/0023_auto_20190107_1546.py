# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0022_auto_20181221_1124'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
