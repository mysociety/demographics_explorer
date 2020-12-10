# -*- coding: utf-8 -*-


from django.db import migrations, models
import django_sourdough.models.mixins

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CollectionItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='CollectionType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='ComparisonGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
                ('order', models.IntegerField(default=0, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='ComparisonLabel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('order', models.IntegerField(default=0, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='ComparisonSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('source_file', models.CharField(max_length=255, null=True)),
                ('grand_total', models.FloatField(default=0, null=True)),
                ('collectiontype', models.ForeignKey(related_name='sets', to='explorer.CollectionType', null=True, on_delete=models.PROTECT)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='ComparisonSuperset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
                ('h_label', models.CharField(max_length=255, null=True)),
                ('overview', models.BooleanField(default=False)),
                ('group', models.ForeignKey(related_name='sets', to='explorer.ComparisonGroup', null=True, on_delete=models.PROTECT)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='ComparisonUnit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('order', models.IntegerField(default=0, null=True)),
                ('label', models.CharField(max_length=255, null=True)),
                ('label_slug', models.CharField(max_length=255, null=True)),
                ('value', models.FloatField(default=0, null=True)),
                ('expected_value', models.FloatField(default=0, null=True)),
                ('row_total', models.FloatField(default=0, null=True)),
                ('column_total', models.FloatField(default=0, null=True)),
                ('chi_value', models.FloatField(default=0, null=True)),
                ('collection', models.ForeignKey(related_name='units', blank=True, to='explorer.CollectionItem', null=True, on_delete=models.PROTECT)),
                ('parent', models.ForeignKey(related_name='units', to='explorer.ComparisonSet', on_delete=models.PROTECT)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.CreateModel(
            name='SubCollectionItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_time', models.DateTimeField(null=True, editable=False, blank=True)),
                ('batch_id', models.IntegerField(null=True, editable=False, blank=True)),
                ('name', models.CharField(max_length=255, null=True)),
                ('slug', models.CharField(max_length=255, null=True)),
                ('parent', models.ForeignKey(related_name='children', to='explorer.CollectionItem', on_delete=models.PROTECT)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, django_sourdough.models.mixins.StockModelHelpers),
        ),
        migrations.AddField(
            model_name='comparisonset',
            name='superset',
            field=models.ForeignKey(related_name='sets', to='explorer.ComparisonSuperset', null=True, on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='comparisonlabel',
            name='parent',
            field=models.ForeignKey(related_name='labels', to='explorer.ComparisonSet', on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='comparisongroup',
            name='service',
            field=models.ForeignKey(related_name='groups', to='explorer.Service', on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='collectiontype',
            name='service',
            field=models.ForeignKey(related_name='collections', to='explorer.Service', on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='collectionitem',
            name='parent',
            field=models.ForeignKey(related_name='items', to='explorer.CollectionType', on_delete=models.PROTECT),
        ),
    ]
