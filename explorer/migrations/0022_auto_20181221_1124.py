# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0021_auto_20181221_1058'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectiontype',
            name='description',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
