# -*- coding: utf-8 -*-

from itertools import groupby
from collections import Counter

from django_sourdough.views import ComboView, postlogic, prelogic

from django.utils.timezone import now

from .models import (large_cutoff, local_negative, local_positive,
                     local_negative_label, local_positive_label,
                     Service, CollectionType, CollectionItem,
                     ComparisonSuperSet, ComparisonSet, ComparisonLabel,
                     ComparisonGroup, ComparisonUnit)

from research_common.views import AnchorChartsMixIn
from django.urls import reverse
from django.conf import settings
from collections import OrderedDict

static_root = "http://research.mysociety.org/static/img"
media_root = "http://research.mysociety.org"

service_query = Service.objects.all()


class GenericSocial(object):
    share_image = static_root + "/mysociety-circles-social.e9fe1879ff6d.png"
    twitter_share_image = share_image
    share_site_name = "mySociety Research"
    share_twitter = "@mysociety"

    def extra_params(self, context):
        params = super(GenericSocial, self).extra_params(context)
        if hasattr(settings, "SITE_ROOT"):
            params["SITE_ROOT"] = settings.SITE_ROOT
        extra = {"social_settings": self.social_settings(params),
                 "page_title": self._page_title(params)}
        params.update(extra)
        return params


class ServiceLogic(AnchorChartsMixIn):
    chart_storage_slug = "explorer"

    @prelogic
    def prep_service(self):
        self.timestamp = now()
        self.service = Service.objects.get(slug=self.service_slug)
        default = self.service.default()
        self.default_collection_type = default.slug
        self.large_cutoff = large_cutoff
        self.local_negative = local_negative
        self.local_positive = local_positive
        self.local_positive_label = local_positive_label
        self.local_negative_label = local_negative_label


class ExplorerView(GenericSocial, ComboView):
    """
    View for page that links to different services
    """
    template = "explorer/explorer_home.html"
    url_patterns = [r'^']
    url_name = "exp_master_view"
    share_title = "mySociety Data Explorer"
    share_description = "Exploring data patterns in mySociety services."

    def logic(self):

        self.services = Service.objects.all().order_by('name')


class ServiceView(GenericSocial, ComboView, ServiceLogic):
    """
    View for homepage
    """
    template = "explorer/home.html"
    url_patterns = [r'^(.*)/']
    url_name = "exp_home_view"
    args = ["service_slug"]
    share_title = "mySociety Data Explorer - {{service.name}}"
    share_description = "Exploring data patterns in {{service.name}} data."

    def bake_args(self, limit_args=None):
        all_services = service_query
        for s in all_services:
            yield [s.slug]


class ExploringOptionsView(GenericSocial, ComboView, ServiceLogic):
    """
    View for homepage
    """
    template = "explorer/exploring.html"
    url_patterns = [r'^(.*)/exploring_options/']
    url_name = "exp_exploring_view"
    args = ["service_slug"]
    share_title = "mySociety Data Explorer - {{service.name}}"
    share_description = "Exploring data patterns in {{service.name}} data."

    def bake_args(self, limit_args=None):
        all_services = service_query
        for s in all_services:
            yield [s.slug]


class AllAnalysisView(GenericSocial, ComboView, ServiceLogic):
    """
    View for displaying the different modes of analysis
    """
    template = "explorer/labels.html"
    url_patterns = [r'^(.*)/analysis/']
    url_name = "exp_labels_view"
    args = ["service_slug"]
    share_title = "{{service.name}} - Analysis options"
    share_description = "Exploring data patterns in {{service.name}} data."

    def logic(self):
        self.sets = ComparisonSuperSet.objects.filter(
            group__service=self.service).order_by('group__order')

    def bake_args(self, limit=None):
        all_services = service_query
        for s in all_services:
            yield [s.slug]


class GroupedAnalysisChartView(GenericSocial, ComboView, ServiceLogic):
    """
    View for displaying overall charts for different sections
    """
    template = "explorer/labels_charts.html"
    url_patterns = [r'^(.*)/analysis/charts/(.*)/']
    url_name = "expo_labels_charts"
    args = ["service_slug", "group_slug"]
    share_title = "{{service.name}} - {{group.name}}"
    share_description = "Overall charts for {{group.name}}."

    def logic(self):
        self.group = self.service.groups.get(slug=self.group_slug)
        self.groups = self.service.groups.all().order_by("order")
        self.sets = ComparisonSuperSet.objects.filter(
            group=self.group).order_by('-priority')
        for s in self.sets:
            label = s.labels.first()
            set = s.sets.first()
            s.chart = set.get_grand_total_chart(label, summary=True)
            self.chart_collection.register(s.chart)

    def bake_args(self, limit=None):
        all_services = service_query
        for s in all_services:
            for g in s.groups.all():
                yield [s.slug, g.slug]


class AnalysisView(GenericSocial, ComboView, ServiceLogic):
    """
    View for displaying summary of a mode of analysis
    """
    template = "explorer/label.html"
    url_patterns = [r'^(.*)/analysis/(.*)/(.*)/(.*)/']
    url_name = "exp_label_view"
    args = ("service_slug", "parent_slug", "label_slug", "collectiontype_slug")
    share_title = "{{service.name}} - {{label.parent.h_label}} - {{label.name}}"
    share_description = "Exploring data patterns in {{service.name}} data."

    def logic(self):
        CSS = ComparisonSuperSet
        CT = CollectionType
        self.superset = CSS.objects.get(group__service=self.service,
                                        slug=self.parent_slug)
        labels = self.superset.labels.all()
        self.alt_options = labels.exclude(slug=self.label_slug)

        self.collection_type = CT.objects.get(service=self.service,
                                              slug=self.collectiontype_slug)

        cts = CollectionType.objects.filter(
            service=self.service)

        cts = [x for x in cts if x.applies_to_superset(self.superset)]

        self.collection_types = cts

        CL = ComparisonLabel

        self.label = CL.objects.get(parent__slug=self.parent_slug,
                                    parent__group__service=self.service,
                                    slug=self.label_slug
                                    )

        ordered_units = self.label.ordered_units(self.collectiontype_slug)

        CS = ComparisonSet

        self.local_set = CS.objects.get(superset=self.superset,
                                        collectiontype=self.collection_type)

        self.table = self.label.label_table(
            self.collection_type, self.superset)
        self.chart = self.local_set.get_grand_total_chart(self.label)

    def bake_args(self):
        for s in service_query:
            all_types = CollectionType.objects.filter(service=s)
            CL = ComparisonLabel
            for label in CL.objects.filter(parent__group__service=s):
                superset = label.parent
                types = [
                    x for x in all_types if x.applies_to_superset(superset)]
                for t in types:
                    yield [s.slug, label.parent.slug, label.slug, t.slug]


class CollectionTypeView(GenericSocial, ComboView, ServiceLogic):
    """
    CollectionType level view
    """
    template = "explorer/categories.html"
    url_patterns = [r'^(.*)/(.*)/']
    url_name = "exp_categories_view"
    args = ["service_slug", "collection_slug", ("period", 'all')]
    share_title = "{{service.name}} - {{collection.name}}"
    share_description = "Exploring data patterns in {{service.name}} data."

    def logic(self):
        start_year = self.service.start_year
        end_year = self.service.end_year
        self.collection = CollectionType.objects.get(
            slug=self.collection_slug, service=self.service)
        self.year = self.period
        self.allowed_years = [str(x)
                              for x in range(start_year, end_year+1)][::-1]

        # can't show year by year if the collection is year
        if self.collection_slug == "year":
            self.allowed_years = []

        CT = CollectionType
        this_year_collection = CT.objects.filter(
            service=self.service, slug="year")

        if this_year_collection.exists() is False:
            self.allowed_years = []

        if self.year != "all":
            sort_year = int(self.year)
        else:
            sort_year = 0

        self.table, self.grand_total = self.collection.get_table_count(
            sort_year)

    def bake_args(self, limit_args=None):

        all_services = service_query

        for s in all_services:
            for t in s.collections.all():
                yield [s.slug, t.slug, "all"]


class CollectionTypeViewYear(CollectionTypeView):
    """
    Same, but selects view by year
    """
    url_patterns = [r'^(.*)/(.*)/(.*)/']

    def bake_args(self, limit_args=None):

        all_services = service_query
        for s in all_services:
            start_year = s.start_year
            end_year = s.end_year
            for t in s.collections.all():
                for year in range(start_year, end_year + 1):
                    yield [s.slug, t.slug, year]


class CollectionItemView(GenericSocial, ComboView, ServiceLogic):
    """
    view stats reversed by looking at a particular row
    e.g. potholes
    """
    template = "explorer/category.html"
    url_patterns = [r'^(.*)/(.*)/item/(.*)/']
    url_name = "exp_category_view"
    args = ["service_slug", "collection_slug",
            'slug', ("group_slug", "overview")]
    share_title = "{{collection.name}} - {{category.name}}"
    share_description = "Exploring data patterns in {{service.name}} data."

    def logic(self):
        self.collection = CollectionType.objects.get(
            slug=self.collection_slug, service=self.service)
        self.category = CollectionItem.objects.get(
            slug=self.slug, parent=self.collection)
        self.groups = ComparisonGroup.get_all(self.service, self.category)
        self.group = [x for x in self.groups if x.slug == self.group_slug][0]
        set_slugs = [
            x.superset.slug for x in self.group.get_sets(self.collection)]

        def set_is_populated(set):
            q = ComparisonUnit.objects.filter(parent=set,
                                              collection=self.category)
            q = q.exclude(value=0)
            return q.exists()

        self.sets = [self.category.get_set(
            s, self.collection) for s in set_slugs]
        self.sets = [x for x in self.sets if x and set_is_populated(x)]
        self.sets.sort(key=lambda x: x.superset.name.lower())
        self.sets.sort(key=lambda x: x.superset.priority, reverse=True)

        for s in self.sets:
            s.chart = s.get_chart(self.category)
            self.chart_collection.register(s.chart)

    def bake_args(self, limit_args=None):
        services = service_query
        for s in services:
            collection_types = CollectionType.objects.filter(service=s)
            for t in collection_types.prefetch_related('items'):
                for i in t.items.all():
                    yield [s.slug, t.slug, i.slug]


class ComparisonSetView(GenericSocial, ComboView, ServiceLogic):
    """
    view stats reversed by looking at a particular row
    e.g. potholes
    """
    template = "explorer/comparison.html"
    url_patterns = [r'^(.*)/(.*)/item/(.*)/comparison/(.*)/']
    url_name = "exp_comparison_view"
    args = ["service_slug", "collection_slug",
            'category_slug', "superset_slug"]
    share_title = "{{superset.name}} - {{category.name}}"
    share_description = "Exploring data patterns in {{service.name}} data."

    def logic(self):
        # kind of categories
        self.collection = CollectionType.objects.get(
            slug=self.collection_slug, service=self.service)

        # specific category
        self.category = CollectionItem.objects.get(
            slug=self.category_slug, parent=self.collection)

        # link to from analysis to comparisonset
        self.superset = ComparisonSuperSet.objects.get(
            slug=self.superset_slug, group__service=self.service)

        # what we're actually interested in
        self.comparison_set = self.category.get_set(self.superset.slug,
                                                    self.collection)

        cs = self.comparison_set

        self.chart = cs.get_chart(self.category)
        self.tidy_chart = cs.get_chart(self.category, tidy=True)
        self.tidy_percent_chart = cs.get_chart(
            self.category, tidy=True, percentage=True)
        self.expected_chart = cs.get_expected_comparison_chart(
            self.category)
        self.percentage_diff = cs.get_comparison_chart(
            self.category, True)
        self.absolute_diff = cs.get_comparison_chart(
            self.category, False)
        self.table = cs.get_table(self.category)

    def bake_args(self, limit_args=None):
        comparison_sets = ComparisonSet.objects.all()
        all_services = service_query
        for c in comparison_sets:
            superset = c.superset
            collection_type = c.collectiontype
            service = superset.group.service
            if service in all_services:
                for cat in collection_type.items.all():
                    yield [service.slug,
                           collection_type.slug,
                           cat.slug,
                           superset.slug
                           ]


class CollectionItemViewGroups(CollectionItemView):
    url_patterns = [r'^(.*)/(.*)/item/(.*)/(.*)/']

    def bake_args(self, limit_args=None):
        services = service_query
        for s in services:
            collections = CollectionType.objects.filter(service=s)
            for t in collections.prefetch_related('items'):
                for i in t.items.all():
                    groups = ComparisonGroup.get_all(s, i)
                    for g in groups:
                        yield [s.slug, t.slug, i.slug, g.slug]
