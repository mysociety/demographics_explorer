# Generated by Django 3.0.4 on 2021-03-19 08:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0030_auto_20210317_1604'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='singular_name',
            field=models.CharField(default='Report', max_length=255, null=True),
        ),
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