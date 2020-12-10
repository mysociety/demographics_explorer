import datetime
import os
from collections import Counter

import numpy as np
import pandas as pd
from django.conf import settings
from useful_grid import QuickGrid

from .base import AnalysisRegister, AnalysisType, CollectionType
from .funcs import md5_hash

try:
    from popolo_data.importer import Popolo
except Exception:
    Popolo = None
import calendar

from proj import settings

join = os.path.join

current_year = settings.WTT_CURRENT_YEAR


class wtt_register(AnalysisRegister):
    service = "wtt"


welsh_imds = ["wimd",
              "income",
              "employment",
              "health",
              "education",
              "access_to_services",
              "community_safety",
              "physical_enviroment",
              "housing"]


scottish_imds = ["simd",
                 "income",
                 "employment",
                 "health",
                 "education",
                 "housing",
                 "access",
                 "crime"]


english_imds = ["imd",
                "income",
                "employment",
                "health",
                "crime",
                "education_skills_training",
                "children_young_people",
                "adult_skills",
                "housing_and_services",
                "geographic_barriers",
                "wider_barriers",
                "living_environment",
                "indoors",
                "outdoors"
                ]

name_lookup = {"education_skills_training": "Education Skill and Training",
               "housing_and_services": "Housing and Access to Services",
               "geographic_barriers": "Geo Barriers (Access to Services)",
               "wider_barriers": "Wider Barriers (Housing)",
               "indoors": "Indoors Environment",
               "outdoors": "Outdoors Environment"}


def english_name(v):
    if v in name_lookup:
        return name_lookup[v]
    return v.replace("-", " ").replace("_", " ").title()


def get_slugs(l):
    first = l[0][0]
    if first == "i":
        first = "e"
    return [l[0]] + [first + "_" + x for x in l[1:]]


class WTTCollection(CollectionType):
    source_folder = settings.WTT_EXPLORER_SOURCE
    lookup_folder = join("resources", "wtt")


class WTTAnalysis(AnalysisType):
    source_folder = settings.WTT_EXPLORER_SOURCE
    experiment_folder = join(source_folder, "grid")
    processed_folder = join(source_folder, "processed")
    lookup_folder = join("resources", "wtt")
    pickle_folder = os.path.join(source_folder, "pickle")
    source_file = join(
        source_folder, "merged_points_whole_years.csv")


@wtt_register.register
class YearCollection(WTTCollection):
    name = "Year"
    slug = "year"
    display_in_header = False
    description = "Emails grouped by year"
    time_part = "year"
    require_columns = ["to_timestamp"]

    def create_collection_column(self, df):

        df[self.slug] = df["to_timestamp"].str.slice(stop=4)

    def get_labels(self):
        return [[str(x), ""] for x in range(2005, current_year + 1)]


@wtt_register.register
class RecipientCollection(WTTCollection):
    name = "Recipient Type"
    slug = "type_of_recipient"
    description = "The kind of elected (or not) representative that messages have been sent to."
    default = True
    require_columns = ["recipient_type"]

    def create_collection_column(self, df):
        meta = QuickGrid().open([self.lookup_folder, "type_lookup.xlsx"])
        lookup = {x["short"]: x["combined"] for x in meta}

        df[self.slug] = df["recipient_type"].map(lookup)

        return df

    def get_labels(self):
        df = QuickGrid().open([self.lookup_folder, "type_lookup.xlsx"])
        final = []
        for r in df:
            final.append([r["combined"], r["direct"]])
        return final


class RecipientCollectionLocal(WTTCollection):
    name = "Recipient Type"
    slug = "type_of_recipient"
    default = True
    required_columns = ["recipient_type"]

    def create_collection_column(self, df):
        meta = pd.read_csv(join(self.lookup_folder, "type_lookup.xlsx"))
        lookup = meta.set_index("short")["direct"].to_dict()

        df[self.slug] = df["recipient_type"].map(lookup)

        return df

    def get_labels(self):
        df = QuickGrid().open([self.lookup_folder, "type_lookup.xlsx"])
        final = []
        for r in df:
            final.append([r["direct"], ""])
        return final


@wtt_register.register
class RecipientGender(WTTCollection):
    name = "Rep Gender"
    slug = "gender_of_rep"
    description = "The gender of the representative. For MPs sourced from [everypolitician.org](http://everypolitician.org/), for others is derived from name."
    require_columns = ["recipient_gender"]

    def create_collection_column(self, df):

        df[self.slug] = df["recipient_gender"].str.title() + " Representatives"
        return df

    def restrict_source_df(self, df):
        df = df[df["recipient_gender"].isin(["male", "female"])]
        return df

    def get_labels(self):
        options = ["Male Representatives", "Female Representatives"]
        return [[x, ""] for x in options]


@wtt_register.register
class SenderCollection(WTTCollection):
    name = "Sender Gender"
    slug = "gender_of_sender"
    description = "Gender of sender, derived from name. Where unclear this is ignored so this represents less than the full dataset."
    require_columns = ["sender_gender"]

    def create_collection_column(self, df):
        df[self.slug] = df["sender_gender"].str.title() + " Sender"
        return df

    def restrict_source_df(self, df):
        df = df[df["sender_gender"].isin(["male", "female"])]
        return df

    def get_labels(self):
        options = ["Male Sender", "Female Sender"]
        return [[x, ""] for x in options]


@wtt_register.register
class FirstComm(WTTCollection):
    name = "First Use"
    slug = "first_use"
    display_in_header = False
    description = "Result of survey asking if this is the first time the sender has contacted their representative."
    require_columns = ["id"]

    def create_collection_column(self, df):

        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_first_time.csv"))
        lookup["answer"] = lookup["answer"].str.title()
        lookup = lookup.set_index("message_id")["answer"].to_dict()

        df[self.slug] = df["id"].map(lookup)

        return df

    def restrict_source_df(self, df):
        df = df[df[self.slug].isin(["Yes", "No"])]
        return df

    def get_labels(self):
        options = ["Yes", "No"]
        return [[x, ""] for x in options]


@wtt_register.register
class GotResponseCollection(WTTCollection):
    name = "Got Response"
    slug = "got_response"
    display_in_header = False
    description = "Result of survey asking if this is they got a response from their representative."
    require_columns = ["id"]

    def create_collection_column(self, df):

        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_first_time.csv"))
        lookup["answer"] = lookup["answer"].str.title()
        lookup.loc[df["answer"] == "Unsatisfactory", "answer"] = "Yes"
        lookup = lookup.set_index("message_id")["answer"].to_dict()

        df[self.slug] = df["id"].map(lookup)
        return df

    def restrict_source_df(self, df):
        df = df[df[self.slug].isin(["Yes", "No"])]
        return df

    def get_labels(self):
        options = ["Yes", "No"]
        return [[x, ""] for x in options]


@wtt_register.register
class Gender(WTTAnalysis):

    name = "Reports by Gender of Sender"
    slug = "gender"
    h_label = "Gender"
    description = ""
    group = "Characteristics"
    overview = True
    exclusions = ["gender_of_sender"]
    description = "Gender of sender, derived from name. Where unclear this is ignored so this represents less than the full dataset."

    allowed_values = ["male", "female"]
    verbose_allowed_values = ["Male", "Female"]
    require_columns = ["sender_gender"]

    def create_analysis_column(self):

        df = self.source_df
        allowed = self.__class__.allowed_values
        df["gender"] = df["sender_gender"]
        df.loc[~df["gender"].isin(allowed), "gender"] = ""

        return df


@wtt_register.register
class FirstTime(WTTAnalysis):

    name = "Was this first time contacting?"
    slug = "first_time_contacting"
    h_label = "First Time Contacting"
    description = ""
    group = "Characteristics"
    exclusions = ["first_use"]
    description = "Result of survey asking if this is the first time they've contacted their representative."
    allowed_values = ["yes", "no"]
    verbose_allowed_values = ["Yes", "No"]
    overview = True
    require_columns = ["id"]

    def create_analysis_column(self):

        df = self.source_df

        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_first_time.csv"))
        lookup.loc[lookup["answer"] == "Unsatisfactory", "answer"] = "Yes"
        lookup = lookup.set_index("message_id")["answer"].to_dict()

        df[self.slug] = df["id"].map(lookup)
        return df


@wtt_register.register
class GotResponse(WTTAnalysis):

    name = "Did they get a response?"
    slug = "response"
    h_label = "Did they get a response?"
    description = ""
    group = "Characteristics"
    description = "Result of survey asking if they got a response."
    allowed_values = ["yes", "no"]
    exclusions = ["got_response"]
    verbose_allowed_values = ["Yes", "No"]
    overview = True
    require_columns = ["id"]

    def create_analysis_column(self):

        df = self.source_df
        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_get_response.csv"))
        lookup.loc[lookup["answer"] == "Unsatisfactory", "answer"] = "Yes"
        lookup = lookup.set_index("message_id")["answer"].to_dict()
        df[self.slug] = df["id"].map(lookup)
        return df


class TimeAnalysis(WTTAnalysis):
    group = "Time"
    time_part = ""
    require_columns = ["to_timestamp"]

    def create_analysis_column(self):
        """
        add column based on time
        """
        df = self.source_df
        print("creating column: {0}".format(self.slug))
        dt = pd.to_datetime(df['to_timestamp'], format='%Y-%m-%d %H:%M:%S.%f')
        df[self.slug] = getattr(dt.dt, self.__class__.time_part)


@wtt_register.register
class Month(TimeAnalysis):

    name = "Reports by Month"
    slug = "month"
    h_label = "Month of Year"
    description = ""
    time_part = "month"
    description = "Month the message was sent."

    allowed_values = [x for x in range(1, 13)]
    verbose_allowed_values = [calendar.month_name[x][:3] for x in range(1, 13)]


@wtt_register.register
class Year(TimeAnalysis):

    name = "Reports by Year"
    slug = "year"
    h_label = "Year"
    description = ""
    time_part = "year"
    description = "Year the message was sent."
    exclusions = ["year"]

    allowed_values = [x for x in range(2005, current_year + 1)]
    overview = True


@wtt_register.register
class Hour(TimeAnalysis):

    name = "Reports by Hour of Day"
    slug = "hour"
    h_label = "Time of Day"
    description = ""
    time_part = "hour"
    description = "Hour of the day the message was sent."
    overview = True

    allowed_values = [x for x in range(0, 24)]


@wtt_register.register
class Day(TimeAnalysis):

    name = "Reports by Day of Week"
    slug = "day"
    h_label = "Day of Week"
    description = ""
    time_part = "dayofweek"
    description = "Day of the week the message was sent."

    allowed_values = [x for x in range(0, 7)]
    verbose_allowed_values = ['Monday',
                              'Tuesday',
                              'Wednesday',
                              'Thursday',
                              'Friday',
                              'Saturday',
                              'Sunday']


# generate seperate classes for each w_imd

for i in welsh_imds:

    class GenericWIMD(WTTAnalysis):
        if i == "wimd":
            overview = True
            name = "Reports by Welsh Index of Multiple Deprivation"
            slug = i
        else:
            overview = False
            name = "Reports by " + \
                i.replace("-", " ").replace("_", " ").title() + \
                " Deprivation Subdomain (Wales)"
            slug = "w_" + i
        exclusions = ["mp_gender"]
        h_label = "{0} deciles".format(i)
        group = "Welsh IMD"
        column = i
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the Welsh Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "w_imd.csv"))
            # convert score to index
            imd[self.__class__.column] = (
                imd[self.__class__.column] / (1909 / 10)) + 1
            imd[self.__class__.column] = imd[self.__class__.column].apply(
                np.floor)
            imd[self.__class__.column] = imd[self.__class__.column].astype(
                "int")
            index_lookup = imd.set_index(
                "lsoa")[self.__class__.column].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericWIMD.__name__ = GenericWIMD.slug
    wtt_register.register(GenericWIMD)

for i in english_imds:

    class GenericEIMD(WTTAnalysis):
        if i == "imd":
            overview = True
            name = "Reports by Index of Multiple Deprivation"
            slug = i
        else:
            overview = False
            name = "Reports by " + \
                english_name(i) + \
                " Deprivation Subdomain (England)"
            slug = "e_" + i
        column = i
        exclusions = ["mp_gender"]
        h_label = "{0} deciles".format(i)
        group = "English IMD"
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the English Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "imd2019.csv"))
            index_lookup = imd.set_index(
                "lsoa")[self.__class__.column + "_decile"].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericEIMD.__name__ = GenericEIMD.slug
    wtt_register.register(GenericEIMD)

for i in scottish_imds:

    class GenericSIMD(WTTAnalysis):
        if i == "simd":
            overview = True
            name = "Reports by Scottish Index of Multiple Deprivation"
            slug = i
        else:
            overview = False
            name = "Reports by " + \
                i.replace("-", " ").replace("_", " ").title() + \
                " Deprivation Subdomain (Scotland)"
            slug = "s_" + i
        h_label = "{0} deciles".format(i)
        column = i
        exclusions = ["mp_gender"]
        group = "Scottish IMD"
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the English Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "s_imd_domains.csv"))
            # convert score to index
            imd[self.__class__.column] = (
                imd[self.__class__.column] / (6976 / 10)) + 1
            imd[self.__class__.column] = imd[self.__class__.column].apply(
                np.floor)
            index_lookup = imd.set_index(
                "lsoa")[self.__class__.column].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericSIMD.__name__ = GenericSIMD.slug
    wtt_register.register(GenericSIMD)


class wtt_subset(AnalysisRegister):

    allowed = set([])
    require_columns = ["recipient_type"]

    def get_restriction_function(self):

        allowed = self.__class__.allowed

        def inner(df):
            df = df[df["recipient_type"].isin(allowed)]
            return df

        return inner


class wtt_year_base(AnalysisRegister):
    """
    base function for analysis by recent year
    """
    service = ""
    year = 0
    require_columns = ["to_timestamp"]

    def __init__(self):
        super().__init__()
        self.index_cache = None

    def get_restriction_function(self):

        def inner(df):
            if self.index_cache is None:
                analysis_year = str(self.__class__.year)
                year = df["to_timestamp"].str.slice(stop=4)
                index = year == analysis_year
                self.index_cache = index
            else:
                index = self.index_cache

            df = df[index]
            return df

        return inner


wtt_year_clones = []

for y in range(2019, current_year + 1):

    class indiv_year(wtt_year_base):
        service = "wtt_{0}".format(y)
        year = y

    indiv_year.__name__ == indiv_year.service

    indiv_year.clone(wtt_register, exclude=[
        "YearCollection", "Year"])
    wtt_year_clones.append(indiv_year)


class wtt_mp_only(wtt_subset):
    service = "wtt-mp"
    allowed = ["WMC"]


wtt_mp_only.clone(wtt_register, exclude=[
                  "RecipientCollection", "RecipientGender"])

# need to set a new default collection


@wtt_mp_only.register
class MpRecipientGender(RecipientGender):
    default = True


"""

Decommissioned because EP won't be updated this year, using generic version instead
bad_mp_ids = set(['2000005', '2000100'])


@wtt_mp_only.register
class RecipientGenderMP(WTTCollection):
    name = "Rep Gender"
    slug = "rep_gender"
    default = True
    description = "MP Gender sourced from EveryPolitician."
    require_columns = ["recipient_id"]

    def create_collection_column(self, df):

        lookup = QuickGrid().open([self.lookup_folder, "wtt_id_to_ep.csv"])
        lookup = {x["id"]: x["ep_id"] for x in lookup}

        pop = Popolo.from_filename(join(
            self.lookup_folder, "ep-popolo-v1.0.json"))
        gender_lookup = {x.id: x.gender for x in pop.persons}

        extra = {'78966': 'female',
                 '84459': 'female',
                 '78867': 'male',
                 '84331': 'female'}

        def get_gender(v):
            if v in bad_mp_ids:
                return ""
            if v in extra:
                return extra[v]
            else:
                return gender_lookup[lookup[v]].title() + " MPs"

        df["ep_id"] = df["recipient_id"].map(lookup)
        df[self.slug] = df["ep_id"].map(gender_lookup)

        col = df.col_to_location("recipient_type")
        df.generate_col(self.slug, lambda x: get_gender(x["recipient_id"]))

        return df

    def get_labels(self):
        options = ["Male MPs", "Female MPs"]
        return [[x, ""] for x in options]
"""
