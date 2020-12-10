# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparisonlabel',
            name='parent',
            field=models.ForeignKey(related_name='labels', to='explorer.ComparisonSuperSet', on_delete=models.PROTECT),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
