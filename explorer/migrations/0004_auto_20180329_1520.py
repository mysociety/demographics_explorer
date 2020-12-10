# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0003_auto_20180327_1129'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectiontype',
            name='display_in_header',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='comparisonsuperset',
            name='description',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
