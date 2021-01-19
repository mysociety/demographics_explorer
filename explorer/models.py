import datetime
from collections import Counter, OrderedDict
from itertools import groupby

import altair as alt
import numpy as np
import pandas as pd
from django.db import models
from django.urls import reverse
from django.utils.html import escapejs
from django.utils.safestring import mark_safe
from django.utils.text import slugify as dslugify
from django_sourdough.models import FlexiBulkModel
from markdown import markdown
from research_common.charts import AltairChart, Table, query_to_df
from scipy.stats import chi2_contingency
from scipy.stats.contingency import margins
from useful_grid import QuickGrid


class ObjectsToDataFrame(dict):
    """
    store a series of transformations to convert properties
    of an object into a pandas dataframe
    """

    def apply_objects(self, objects):
        result = {}
        for k, v in self.items():
            result[k] = [v(x) for x in objects]
        return pd.DataFrame(result)


def fix_percentage(v):
    return round(v * 100, 2)


def intcomma(x):
    return "{:,}".format(x)


def fix_label(v):
    v = v.encode('ascii', errors='ignore').decode('ascii')
    v = v.replace("'", "").replace('\n', '')
    v = v.replace("'", "").replace('\r', '')
    v = v.replace("ethnic group", "")  # fix for long lanbels in LA
    return v


def slugify(x):
    return dslugify(x[:40])


sig_cutoff = 2
large_cutoff = 1


def residuals(observed, expected):
    return (observed - expected) / np.sqrt(expected)


def stdres(observed, expected):
    n = observed.sum()
    rsum, csum = margins(observed)
    v = csum * rsum * (n - rsum) * (n - csum) / n**3
    return (observed - expected) / np.sqrt(v)


class Service(FlexiBulkModel):
    """
    A website that stats are being examined for
    e.g. 'fixmystreet'
    """
    name = models.CharField(max_length=255, null=True)
    slug = models.CharField(max_length=255, null=True)
    collective_name = models.CharField(
        max_length=255, null=True, default="Reports")

    def header_types(self):
        return self.collections.filter(display_in_header=True).order_by('name')

    def all_types(self):
        return self.collections.all().order_by('name')

    def all_types_but_default(self):
        return self.collections.filter(default=False).order_by('name')

    def default(self):
        return self.collections.get(default=True)

    @property
    def start_year(self):
        if self.slug != "wdtk":
            return 2007
        else:
            return 2012

    @property
    def end_year(self):
        if self.slug != "wdtk":
            return 2020
        else:
            return 2020


class CollectionType(FlexiBulkModel):
    """
    The kind of values that the analysis is being run against (the 'rows')
    e.g. 'fms categories A' - (but not the actual category items,
    just the idea of categories)
    """
    service = models.ForeignKey(
        Service, related_name="collections", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True)
    slug = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True, blank=True)
    display_in_header = models.BooleanField(default=True)
    default = models.BooleanField(default=False)

    def markdown_description(self):
        if self.description:
            md = markdown(self.description)
            return mark_safe(md)

    def applies_to_superset(self, superset):
        """
        does this superset relate at all to this category
        """
        exists = ComparisonSet.objects.filter(superset=superset,
                                              collectiontype=self
                                              ).exists()
        return exists

    def first(self):
        return self.items.all()[0]

    def create_items(self, model):
        """
        handed a generation model - creates associated items
        """
        items = model().get_labels()
        top_level = set(list(x[0] for x in items))

        for m in top_level:
            CollectionItem(name=m,
                           slug=slugify(m),
                           parent=self).queue()

        CollectionItem.save_queue()

        meta_lookup = {x.name: x.id for x in self.items.all()}

        for r in items:
            if r[1]:
                c = SubCollectionItem(name=r[1],
                                      slug=slugify(r[1]),
                                      parent_id=meta_lookup[r[0]])
                c.queue()

        SubCollectionItem.save_queue()

    def get_table_count(self, year):
        """
        generate table given year
        """
        categories = list(self.items.all())
        categories = [
            x for x in categories if x.units.all().exists()]
        for c in categories:
            c.computed_total = c.total(year)

        grand_total = sum([x.computed_total for x in categories])

        for c in categories:
            if grand_total:
                c.computed_percent = (c.computed_total / float(grand_total))
            else:
                c.computed_percent = 0
        categories.sort(key=lambda x: x.computed_total, reverse=True)
        categories = [x for x in categories if x.computed_total]

        table = Table(name=self.name + " " + str(year))

        odf = ObjectsToDataFrame()
        odf[self.name] = lambda x: x.slug
        odf[self.service.collective_name] = lambda x: x.computed_total
        odf["%"] = lambda x: x.computed_percent

        table.df = odf.apply_objects(categories)

        def get_url(c):
            return reverse('exp_category_view', args=(
                self.service.slug, self.slug, c.slug))

        def get_link(c):
            url = get_url(c)
            name = c.name
            return '<a href="{0}">{1}</a>'.format(url, name)

        category_link = {c.slug: get_link(c) for c in categories}

        table.format[self.name] = category_link.get
        table.format[self.service.collective_name] = intcomma
        table.format["%"] = fix_percentage

        return table, grand_total


class CollectionItem(FlexiBulkModel):
    """

    item in an analysis row - e.g. potholes
    """
    parent = models.ForeignKey(
        CollectionType, related_name="items", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True)
    slug = models.CharField(max_length=255, null=True)

    def total(self, year=None):
        """
        get number of reports in category in year
        """
        parent_is_year = self.parent.slug == "year"
        year_superset = self.units.filter(parent__superset__slug="year")
        month_units = self.units.filter(parent__superset__slug="month")

        if parent_is_year or year_superset.exists() is False:
            if month_units.exists() is False:
                return 1
            else:
                return month_units[0].row_total
        if year:
            try:
                return int(self.units.get(parent__superset__slug="year",
                                          label=year).value)
            except IndexError:
                return 0
        return int(year_superset[0].row_total)

    def sorted_unit(self, slug):
        return self.units.filter(parent__slug=slug).order_by('order')

    def get_set(self, slug, collectiontype):
        set = ComparisonSet.objects.get(superset__slug=slug,
                                        collectiontype=collectiontype)
        if set.units.exists():
            return set
        else:
            return None

    def multi_coordinates(self):

        allowed_comparisons = ["hour",
                               "day",
                               "month",
                               "gender",
                               "first_fms_report",
                               "photo",
                               "e_income",
                               "e_employment",
                               "e_health",
                               "e_crime",
                               "e_education_skills_training",
                               "e_housing_and_services"]

        CU = ComparisonUnit
        ac = allowed_comparisons

        units = CU.objects.filter(collection=self,
                                  parent__superset__slug__in=ac,
                                  ).prefetch_related("parent__superset")

        units = list(units)
        units.sort(key=lambda x: x.order)
        coordinates = []

        for a in allowed_comparisons:
            selected = [x for x in units if x.parent.superset.slug == a]
            total_range = []
            # print self.name, a, selected
            for s in selected:
                total_range += [s.order for x in range(0, int(s.value))]
            if len(total_range) == 0:
                print("missing {0}".format(self.name))
                return None
            a = sum(total_range) / float(len(total_range))
            coordinates.append(a)

        return coordinates

    def distance(self, other):
        """
        get the distance on all values between two collectionitems
        for use in network graph
        """

        def type_sort(v):
            if v.collection == self:
                return 0
            return 1

        allowed_comparisons = ["hour",
                               "day",
                               "month",
                               "gender",
                               "first-report",
                               "photo",
                               "ruc",
                               "e_income",
                               "e_employment",
                               "e_health",
                               "e_crime",
                               "e_education_skills_training",
                               "e_housing_and_services"]

        CU = ComparisonUnit
        ac = allowed_comparisons

        units = CU.objects.filter(collection__in=[self, other],
                                  parent__superset__slug__in=ac)
        units = list(units)
        for u in units:
            u.compound_label = "{0}_{1}".format(u.parent_id, u.label_slug)

        def label_sort(x): return x.compound_label
        units.sort(key=type_sort)
        units.sort(key=label_sort)

        total_distance = 0

        for g, ll in groupby(units, label_sort):
            ll = list(ll)
            if len(ll) < 2:
                continue
            assert len(ll) == 2
            # self unit is first in order but doesn't really matter
            values = [x.as_row_percent for x in ll]
            distance = abs(values[0] - values[1])
            total_distance += distance
        return total_distance


class SubCollectionItem(FlexiBulkModel):
    """
    not really that important, where a collectionitem represents
    something abstract and rolled up from lesser categories
    e.g. categories going to a metacategory

    no analysis on this level, but is displayed
    """
    name = models.CharField(max_length=255, null=True)
    slug = models.CharField(max_length=255, null=True)
    parent = models.ForeignKey(
        CollectionItem, related_name="children", on_delete=models.CASCADE)


class ComparisonGroup(FlexiBulkModel):
    """
    different kinds of analysis are grouped into words like
    'time', 'characteristics'
    """
    service = models.ForeignKey(
        Service, related_name="groups", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True)
    slug = models.CharField(max_length=255, null=True)
    order = models.IntegerField(default=0, null=True)

    @classmethod
    def get_all(cls, service, collection_item):

        def has_items(x):
            sets = ComparisonSet.objects.filter(superset__group=x)
            q = ComparisonUnit.objects.filter(parent__in=sets,
                                              collection=collection_item)
            q = q.exclude(value=0)
            return q.exists()

        groups = list(cls.objects.filter(service=service).order_by('order'))

        groups = [x for x in groups if has_items(x)]

        overview = cls(name="Overview", slug="overview", service=service)
        all = cls(name="All", slug="all", service=service)

        return [all, overview] + groups

    def get_sets(self, collection):

        query = ComparisonSet.objects.filter(collectiontype=collection)
        if self.slug == "overview":
            return query.filter(superset__overview=True)
        elif self.slug == "all":
            return query.order_by('superset__group__order')
        else:
            return query.filter(superset__group=self)


class ComparisonSuperSet(FlexiBulkModel):
    """
    relation between a mode of analysis and a comparisongroup
    (and hence service)
    e.g. 'gender', 'e_imd'
    """
    name = models.CharField(max_length=255, null=True)
    slug = models.CharField(max_length=255, null=True)
    h_label = models.CharField(max_length=255, null=True)
    description = models.TextField(default="")
    group = models.ForeignKey(
        ComparisonGroup, related_name="sets", null=True,
        on_delete=models.CASCADE)
    overview = models.BooleanField(default=False)

    def ordered_labels(self):
        return self.labels.all().order_by('order')

    def markdown_description(self):
        if self.description:
            md = markdown(self.description)
            return mark_safe(md)


class ComparisonSet(FlexiBulkModel):
    """
    relation between a mode of analysis (column)
    and collectiontype(set of rows)
    the "table" level - essentially
    """
    superset = models.ForeignKey(
        ComparisonSuperSet, related_name="sets", null=True,
        on_delete=models.CASCADE)
    collectiontype = models.ForeignKey(
        CollectionType, related_name="sets", null=True,
        on_delete=models.CASCADE)
    source_file = models.CharField(max_length=255, null=True)
    grand_total = models.FloatField(default=0, null=True)
    chi2 = models.FloatField(default=0)
    p = models.FloatField(default=0)
    dof = models.FloatField(default=0)

    def get_units(self, collection_item):
        """
        get the rows associated with this combination of set
        and collection item
        """
        return self.units.filter(collection=collection_item).order_by("order")

    def get_grand_total_chart(self, label):
        """
        generates chart showing the grand total for the rows in question
        """

        service = self.superset.group.service

        possible_collection_types = self.collectiontype.items.all()
        for ct in possible_collection_types:
            if self.units.filter(collection=ct).exists():
                break

        default_collection = ct
        column_totals = self.units.filter(collection=default_collection)

        column_totals = column_totals.order_by('order')

        avg_length = 0
        if column_totals:
            avg_length = sum([len(m.label)
                              for m in column_totals])/len(column_totals)


        def make_url(row):
            return reverse('exp_label_view', args=(service.slug,
                                                   label.parent.slug,
                                                   row["label_slug"],
                                                   self.collectiontype.slug))

        odf = ObjectsToDataFrame()
        odf["label_slug"] = lambda x: x.label_slug
        odf["label"] = lambda x: fix_label(x.label)
        odf["report"] = lambda x: x.column_total
        df = odf.apply_objects(column_totals)

        df["percent"] = (df["report"] / df["report"].sum() * 100).round(2)
        df["url"] = df.apply(make_url, axis="columns")
        df["color"] = "#E2DFD9"
        df.loc[df["label_slug"] == label.slug, "color"] = "#6C6B68"

        name = " ".join(
            [self.superset.name, self.collectiontype.name, label.name])

        switch = avg_length > 10
        if switch:
            xx = "report"
            yy = alt.Y("label", sort=None, axis=alt.Axis(title=""))
        else:
            xx = alt.X("label", sort=None, axis=alt.Axis(title=""))
            yy = "report"

        chart = AltairChart(df, name=name, chart_type="bar")
        chart.set_options(x=xx,
                          y=yy,
                          color=alt.Color("color", scale=None),
                          href="url",
                          tooltip=["label",
                                   alt.Tooltip("report", format=',.2r'),
                                   "percent"])

        return chart

    def get_table(self, collection_item):
        """
        table showing distribution of comparison set
        """

        stored_units = self.get_units(collection_item)

        name = " ".join([self.collectiontype.name,
                         collection_item.name, self.superset.name])
        table = Table(name=name)

        odf = ObjectsToDataFrame()
        odf["item"] = lambda x: x.label
        odf["%"] = lambda m: m.as_row_percent
        odf["Count"] = lambda m: int(m.value)
        odf["Expected"] = lambda x: x.expected
        odf["Expected Diff%"] = lambda x: x.diff_percent
        odf["Std. Res."] = lambda x: x.round_chi

        table.df = odf.apply_objects(stored_units)

        def get_url(x):
            group_service_slug = self.superset.group.service.slug
            u = reverse('exp_label_view', args=(group_service_slug,
                                                self.superset.slug,
                                                x.label_slug,
                                                self.collectiontype.slug))
            return u

        def format_url(x):
            f = '<a href="{1}">{0}</a>'
            return f.format(fix_label(x.label), get_url(x))

        def highlight_sig(row):
            not_sig = ""
            sig_less_than_expected = '#E04B4B'
            sig_more_than_expected = '#62B356'

            diff = row["Expected Diff%"]
            chi = row["Std. Res."]

            if chi > sig_cutoff:
                if diff < large_cutoff:
                    return not_sig
                else:
                    return sig_more_than_expected
            elif chi < (0-sig_cutoff):
                if diff < large_cutoff:
                    return not_sig
                else:
                    return sig_less_than_expected
            else:
                return not_sig

        label_lookup = {x.label: format_url(x) for x in stored_units}
        table.format["item"] = label_lookup.get
        table.style_on_row["Expected Diff%"] = highlight_sig
        table.style_on_row["Std. Res."] = highlight_sig

        return table

    def get_expected_comparison_chart(self, collection_item):
        """
        chart showing distribution of comparison set
        """
        name = " ".join(["comparison", self.superset.name,
                         self.collectiontype.name, collection_item.name])
        collective_name = self.collectiontype.service.collective_name

        units = self.get_units(collection_item)

        odf = ObjectsToDataFrame()
        odf["item"] = lambda x: fix_label(x.label)
        odf[collective_name] = lambda x: x.int_value
        odf["tooltip"] = lambda x: "Actual: {0}".format(x.int_value)
        odf["style"] = lambda x: x.cell_style()

        actual = odf.apply_objects(units)
        actual["series"] = "Actual"
        actual["opacity"] = 0.8

        odf = ObjectsToDataFrame()
        odf["item"] = lambda x: fix_label(x.label)
        odf[collective_name] = lambda x: x.expected
        odf["tooltip"] = lambda x: "Expected: {0}".format(x.expected)

        expected = odf.apply_objects(units)
        expected["series"] = "Expected"
        expected["opacity"] = 0.4
        expected["style"] = '#6C6B68'

        df = pd.concat([actual, expected])

        chart = AltairChart(df, name=name, chart_type="bar")

        chart.set_options(x=alt.X("item", sort=None, axis=alt.Axis(
            title="", labelAngle=0)),
            y=alt.Y(collective_name, stack=None),
            tooltip="tooltip",
            color=alt.Color("style", scale=None),
            opacity=alt.Opacity("opacity", scale=None))

        return chart

    def get_comparison_chart(self, collection_item, percentage=False):
        """
        chart showing expected differences in comparison set
        """
        name = " ".join(["differences", self.superset.name,
                         self.collectiontype.name])

        def make_tooltip(m):
            if percentage:
                comparison = m.diff_percent_rel
            else:
                comparison = m.expected_diff
            tooltip = OrderedDict()
            tooltip["Group"] = fix_label(m.label)
            tooltip["Count"] = m.int_value
            tooltip["%"] = str(m.as_row_percent) + "%"
            tooltip["Expected"] = m.expected
            tooltip["Diff"] = str(m.diff_percent) + "%"
            tooltip["Std. Res"] = m.round_chi
            tooltip_str = "Difference: {0}".format(comparison)

            return tooltip_str

        collective_name = self.collectiontype.service.collective_name

        odf = ObjectsToDataFrame()
        odf["Item"] = lambda m: fix_label(m.label)
        odf["style"] = lambda m: m.cell_style()
        if percentage:
            label = "Percentage"
            odf[label] = lambda m: m.diff_percent_rel
        else:
            label = collective_name
            odf[label] = lambda m: m.expected_diff
        odf["tooltip"] = make_tooltip

        units = self.get_units(collection_item)
        df = odf.apply_objects(units)

        chart = AltairChart(df, name=name, chart_type="bar")

        chart.set_options(x=alt.X("Item", sort=None, axis=alt.Axis(title="", labelAngle=0)),
                          y=label,
                          tooltip="tooltip",
                          color=alt.Color("style", scale=None))

        return chart

    def get_chart(self, collection_item):
        """
        chart showing distribution of comparison set
        """

        stored_units = self.get_units(collection_item)
        avg_length = 0
        if stored_units:
            avg_length = sum([len(m.label)
                              for m in stored_units])/len(stored_units)

        name = " ".join(["comparison", self.superset.name,
                         self.collectiontype.name])

        def get_url(x):
            group_service_slug = self.superset.group.service.slug
            return reverse('exp_label_view', args=(group_service_slug,
                                                   self.superset.slug,
                                                   x.label_slug,
                                                   self.collectiontype.slug))

        collective_name = self.collectiontype.service.collective_name

        odf = ObjectsToDataFrame()
        odf["Group"] = lambda m: fix_label(m.label)
        odf[collective_name] = lambda m: m.value
        odf["style"] = lambda m: m.cell_style()
        odf["%"] = lambda m: str(m.as_row_percent) + "%"
        odf["Expected"] = lambda m: m.expected
        odf["Diff"] = lambda m: str(m.diff_percent) + "%"
        odf["Std. Res"] = lambda m: m.round_chi
        odf["url"] = get_url

        stored_units = self.get_units(collection_item)

        df = odf.apply_objects(stored_units)

        # make things that look better as ints into ints
        try:
            df["Group"] = df["Group"].astype(
                'float').astype("int").astype("str")
        except Exception:
            pass

        # if long text in description, switch the axis
        switch = avg_length > 10

        if switch:
            xx = alt.X(collective_name)
            yy = alt.Y("Group", sort=None, axis=alt.Axis(
                title="", labelAngle=0))
        else:
            xx = alt.X("Group", sort=None, axis=alt.Axis(
                title="", labelAngle=0))
            yy = alt.Y(collective_name)

        chart = AltairChart(df=df, name=name, chart_type="bar")
        chart.set_options(x=xx,
                          y=yy,
                          tooltip=["Group", collective_name, "%",
                                   "Expected", "Diff", "Std. Res"],
                          color=alt.Color("style", scale=None),
                          href="url")

        return chart

    def generate(self, save=True):
        """
        digest source - assuming categories as row labels
        """
        self.units.all().delete()

        meta_lookup = {x.name: x.id for x in CollectionItem.objects.filter(
            parent=self.collectiontype)}

        qg = QuickGrid().open(self.source_file)

        qg.data = [x for x in qg.data if x[0]]

        def float_or_zero(v):
            if v:
                return float(v)
            else:
                return 0

        reduced = [[float_or_zero(y) for y in x[1:]] for x in qg.data]

        obs = np.array(reduced)

        chi2, p, dof, expected = chi2_contingency(obs)
        resid = residuals(obs, expected)
        grand_total = 0
        # print meta_lookup

        def win_safe_slug(v):
            slug = slugify(v)
            if slug.upper() in ["CON"]:
                return "_" + slug
            else:
                return slug

        for n, resid_row in enumerate(resid):
            expected_row = expected[n]
            grid_row = qg.data[n]
            row_total = sum([float_or_zero(x) for x in grid_row[1:]])
            grand_total += row_total
            category_id = meta_lookup[grid_row[0]]
            order = 0
            for y, head in enumerate(qg.header[1:]):
                column_total = sum([float_or_zero(x[y + 1]) for x in qg.data])
                order += 1
                cu = ComparisonUnit(parent=self,
                                    collection_id=category_id,
                                    order=order,
                                    label=head,
                                    label_slug=win_safe_slug(head),
                                    value=float_or_zero(grid_row[y + 1]),
                                    row_total=row_total,
                                    column_total=column_total,
                                    chi_value=resid_row[y],
                                    expected_value=expected_row[y]
                                    )
                cu.queue()
        if save:
            ComparisonUnit.save_queue()
        self.grand_total = grand_total
        self.chi2 = chi2
        self.dof = dof
        self.p = p
        self.save()


class ComparisonLabel(FlexiBulkModel):
    """
    abstracted label for a row e.g. 'Potholes'
    Used to find all rows in different chi tables that
    connect to that value
    """
    parent = models.ForeignKey(
        ComparisonSuperSet, related_name="labels", on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True)
    order = models.IntegerField(default=0, null=True)
    slug = models.CharField(max_length=255, null=True)

    def units(self, collection_slug):
        return ComparisonUnit.objects.filter(parent__superset_id=self.parent_id,
                                             parent__collectiontype__slug=collection_slug,
                                             label_slug=self.slug)

    def ordered_units(self, collection_slug):
        units = list(self.units(collection_slug).order_by('-chi_value'))

        units.sort(key=lambda x: x.diff_percent_rel, reverse=True)

        def sort_by_both(v):
            c = v.chi_value
            d = v.diff_percent
            if c >= sig_cutoff:
                c = 1
            elif c <= 0 - sig_cutoff:
                c = -1
            else:
                c = 0

            if d < large_cutoff:
                c = 0
            va = v.int_value
            if va == 0:
                c = 0
            return c

        units.sort(key=sort_by_both, reverse=True)

        return units

    def label_table(self, collection_type, superset):
        """
        define google table that shows the chi table of collection type
        vs label
        """
        ordered_units = self.ordered_units(collection_type.slug)

        name = " ".join([self.name, superset.name, collection_type.name])

        table = Table(name=name)

        odf = ObjectsToDataFrame()
        odf["Category"] = lambda x: x.collection.name
        odf["Reports"] = lambda x: int(x.value)
        odf["%"] = lambda x: x.as_row_percent
        odf["Expected"] = lambda x: x.expected
        odf["Expected Diff%"] = lambda x: x.diff_percent
        odf["Std. Res."] = lambda x: x.chi_value

        table.df = odf.apply_objects(ordered_units)

        def get_url(slug, name):

            url = reverse('exp_category_view', args=(collection_type.service.slug,
                                                     collection_type.slug,
                                                     slug))

            item_url = reverse('exp_comparison_view', args=(collection_type.service.slug,
                                                            collection_type.slug,
                                                            slug,
                                                            superset.slug))
            return '<a href="{0}">{1}</a> (<a href="{2}">Direct</a>)'.format(url,
                                                                             name,
                                                                             item_url)

        def highlight_sig(row):
            not_sig = ""
            sig_less_than_expected = 'background-color: #E04B4B;'
            sig_more_than_expected = 'background-color: #62B356'

            diff = row["Expected Diff%"]
            chi = row["Std. Res."]

            if chi > sig_cutoff:
                if diff < large_cutoff:
                    return not_sig
                else:
                    return sig_more_than_expected
            elif chi < (0-sig_cutoff):
                if diff < large_cutoff:
                    return not_sig
                else:
                    return sig_less_than_expected
            else:
                return not_sig

        url_lookup = {x.collection.name: get_url(
            x.collection.slug, x.collection.name) for x in ordered_units}

        table.format["Category"] = url_lookup.get
        table.format["Reports"] = intcomma
        table.format["Expected"] = intcomma
        #table.format["%"] = fix_percentage
        table.format["Std. Res."] = lambda x: round(x, 2)
        table.style_on_row["Expected Diff%"] = highlight_sig
        table.style_on_row["Std. Res."] = highlight_sig

        return table

    @ classmethod
    def generate(cls, service, save=True):
        """
        extract labels from comparison units that have been popualted
        """
        cls.objects.filter(parent__group__service=service).delete()

        done = []

        for c in ComparisonUnit.objects.filter(parent__superset__group__service=service):
            parent_id = c.parent.superset_id
            key = "{0}{1}".format(parent_id, c.label_slug)
            if key not in done:
                cls(parent_id=parent_id,
                    name=c.label,
                    slug=c.label_slug,
                    order=c.order).queue()
            done.append(key)
        if save:
            cls.save_queue()


class ComparisonUnit(FlexiBulkModel):
    """
    'cell' of the sheet - what a value is, 
    and if it's expected or not given overall distributions
    """

    parent = models.ForeignKey(
        ComparisonSet, related_name="units", on_delete=models.CASCADE)
    collection = models.ForeignKey(
        CollectionItem, blank=True, null=True, related_name="units", on_delete=models.CASCADE)
    order = models.IntegerField(default=0, null=True)
    label = models.CharField(max_length=255, null=True)
    label_slug = models.CharField(max_length=255, null=True)
    value = models.FloatField(default=0, null=True)
    expected_value = models.FloatField(default=0, null=True)
    row_total = models.FloatField(default=0, null=True)
    column_total = models.FloatField(default=0, null=True)
    chi_value = models.FloatField(default=0, null=True)

    def cell_style(self):
        not_sig = '#6C6B68'  # grey

        sig_less_than_expected_large = '#E04B4B'
        sig_less_than_expected_small = not_sig
        sig_more_than_expected_small = not_sig

        sig_more_than_expected_large = '#62B356'

        upper = sig_cutoff
        lower = 0 - upper

        diff = self.diff_percent

        if self.chi_value > upper:
            if diff < large_cutoff:
                return sig_more_than_expected_small
            else:
                return sig_more_than_expected_large
        elif self.chi_value < lower:
            if diff < large_cutoff:
                return sig_less_than_expected_small
            else:
                return sig_less_than_expected_large
        else:
            return not_sig

    @property
    def as_row_percent(self):
        return round((self.value / float(self.row_total)) * 100, 2)

    @property
    def round_chi(self):
        return round(self.chi_value, 2)

    @property
    def expected(self):
        return int(self.expected_value)

    @property
    def expected_diff(self):
        return int(self.value - self.expected)

    @property
    def int_value(self):
        return int(self.value)

    @property
    def diff_percent_rel(self):
        ed = self.expected_diff
        if self.expected:
            return round((ed / float(self.expected)) * 100, 2)
        else:
            if ed > 0:
                return 100
            else:
                return -100

    @property
    def diff_percent(self):
        """
        does not allow negative percentages
        """
        ed = self.expected_diff
        if ed < 0:
            ed = 0 - ed
        if self.expected:
            return round((ed / float(self.expected)) * 100, 2)
        else:
            return 100