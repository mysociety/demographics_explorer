# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0020_auto_20180702_1506'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='collective_name',
            field=models.CharField(default=b'Reports', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperSet', null=True, on_delete=models.PROTECT),
        ),
    ]
