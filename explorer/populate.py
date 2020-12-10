"""
populate script
generates chi square grids using objects in the 
generate folder

Then creates the django objects associated with them. 

"""
import os
import datetime
from itertools import groupby

from .models import Service, ComparisonSuperSet, CollectionType, CollectionItem, ComparisonSet, ComparisonUnit, ComparisonLabel, ComparisonGroup

from .views import CollectionTypeView, ServiceView, ExploringOptionsView, AnalysisView, CollectionItemViewGroups

from .generate.fms import fms_register, fms_no_cobrands, year_clones
from .generate.wtt import wtt_register, wtt_mp_only, wtt_year_clones

from .generate.wdtk import wdtk_register
from django.utils.text import slugify as dslugify


def slugify(x): return dslugify(x[:40])


def populate_fms_service(service, register):
    # create service

    # create comparison groups

    ComparisonGroup.objects.filter(service=service).delete()

    ComparisonGroup(name="Categories",
                    slug=slugify("Categories"),
                    service=service,
                    order=6).queue()
    ComparisonGroup(name="Scottish IMD",
                    slug=slugify("Scottish IMD"),
                    service=service,
                    order=4).queue()
    ComparisonGroup(name="Welsh IMD",
                    slug=slugify("Welsh IMD"),
                    service=service,
                    order=5).queue()
    ComparisonGroup(name="English IMD",
                    slug=slugify("English IMD"),
                    service=service,
                    order=3).queue()
    ComparisonGroup(name="Characteristics",
                    slug=slugify("Characteristics"),
                    service=service,
                    order=2).queue()
    ComparisonGroup(name="Time",
                    slug=slugify("Time"),
                    service=service,
                    order=1).queue()

    ComparisonGroup.save_queue()

    populate_service(service, register)


def populate_fms_plain():

    service, new = Service.objects.get_or_create(name="FixMyStreet",
                                                 collective_name="Reports",
                                                 slug="fms")

    register = fms_register
    populate_fms_service(service, register)


def populate_fms_no_cobrand():

    Service.objects.filter(slug="fms_no_cobrands").delete()

    service, new = Service.objects.get_or_create(name="FMS (No Cobrands)",
                                                 collective_name="Reports",
                                                 slug="fms_no_cobrands")

    register = fms_no_cobrands
    populate_fms_service(service, register)


def populate_fms_year(register):

    year = register.year

    slug = "fms_{0}".format(year)

    Service.objects.filter(slug=slug).delete()

    service, new = Service.objects.get_or_create(name="FMS ({0})".format(year),
                                                 collective_name="Reports",
                                                 slug=slug)

    register = register
    populate_fms_service(service, register)


def populate_wtt_restriction(slug, name, register):
    Service.objects.filter(slug=slug).delete()
    service, new = Service.objects.get_or_create(
        name=name, slug=slug, collective_name="Messages")
    populate_wtt_groups(service, register)


def populate_wtt():
    populate_wtt_restriction("wtt", "WriteToThem", wtt_register)


def populate_wtt_year(service):
    year = service.year
    populate_wtt_restriction("wtt_{0}".format(
        year), "WTT ({0})".format(year), service)

def populate_wtt_sub_groups():
    populate_wtt_restriction("wtt-mps", "WTT (MPs)", wtt_mp_only)


def populate_wtt_groups(service, register):

    ComparisonGroup.objects.filter(service=service).delete()
    # create comparison groups
    ComparisonGroup(name="Scottish IMD",
                    slug=slugify("Scottish IMD"),
                    service=service,
                    order=4).queue()
    ComparisonGroup(name="Welsh IMD",
                    slug=slugify("Welsh IMD"),
                    service=service,
                    order=5).queue()
    ComparisonGroup(name="English IMD",
                    slug=slugify("English IMD"),
                    service=service,
                    order=3).queue()
    ComparisonGroup(name="Characteristics",
                    slug=slugify("Characteristics"),
                    service=service,
                    order=2).queue()
    ComparisonGroup(name="Time",
                    slug=slugify("Time"),
                    service=service,
                    order=1).queue()

    ComparisonGroup.save_queue()

    populate_service(service, register)


def populate_service(service, register):
    ComparisonSet.objects.filter(collectiontype__service=service).delete()
    CollectionType.objects.filter(service=service).delete()
    types = []
    for c in register.collections_stored:
        collectiontype, new = CollectionType.objects.get_or_create(service=service,
                                                                   name=c.name,
                                                                   slug=c.slug,
                                                                   description=c.description,
                                                                   display_in_header=c.display_in_header,
                                                                   default=c.default)
        collectiontype.create_items(c)
        collectiontype.model = c
        types.append(collectiontype)

    """
    create analysis
    """
    groups = service.groups.all()
    group_lookup = {x.name: x for x in groups}

    analysis = register.analysis_stored

    def key(x): return x.group

    analysis.sort(key=key)

    for g, ll in groupby(analysis, key):
        parent_group = group_lookup[g]
        parent_group.sets.all().delete()
        for item in ll:
            group, new = ComparisonSuperSet.objects.get_or_create(name=item.name,
                                                                  slug=item.slug,
                                                                  h_label=item.h_label,
                                                                  description=item.description,
                                                                  overview=item.overview,
                                                                  group=parent_group)
            # create a set for each comparison type
            for t in types:
                if t.slug not in item.exclusions:
                    combo = item(t.model)
                    comboset, created = ComparisonSet.objects.get_or_create(superset=group,
                                                                            collectiontype=t,
                                                                            source_file=combo.final_location)
                    if os.path.exists(comboset.source_file) == False:
                        combo.process()
                    comboset.generate(save=False)
            ComparisonUnit.save_queue()
    # populate comparison sets from classes

    ComparisonLabel.generate(service)


def populate_wdtk():


    wdtk_register.run_all()
    name = "WhatDoTheyKnow Survey"
    slug = ("wdtk")
    service, new = Service.objects.get_or_create(
        name=name, slug=slug, collective_name="Requests")

    ComparisonGroup.objects.filter(service=service).delete()
    # create comparison groups
    ComparisonGroup(name="Request",
                    slug=slugify("Request"),
                    service=service,
                    order=0).queue()
    ComparisonGroup(name="Demographics",
                    slug=slugify("Demographics"),
                    service=service,
                    order=1).queue()
    ComparisonGroup(name="Participation",
                    slug=slugify("Participation"),
                    service=service,
                    order=2).queue()
    ComparisonGroup(name="WDTK",
                    slug=slugify("WDTK"),
                    service=service,
                    order=3).queue()

    ComparisonGroup.save_queue()

    populate_service(service, wdtk_register)


def populate_all_fms():

    fms_register.run_all()
    fms_no_cobrands.run_all()
    for y in year_clones:
        y.run_all()

    populate_fms_plain()
    populate_fms_no_cobrand()
    for y in year_clones:
        populate_fms_year(y)


def populate_all_wtt():

    wtt_register.run_all()
    wtt_mp_only.run_all()
    for y in wtt_year_clones:
        y.run_all()

    populate_wtt()
    populate_wtt_sub_groups()
    for y in wtt_year_clones:
        populate_wtt_year(y)


def populate():
    populate_all_fms()
    populate_all_wtt()
    populate_wdtk()