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
              "physical_environment",
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

uk_imds = ["UK_IMD_E",
           "GB_IMD_E"]

name_lookup = {"education_skills_training": "Education Skill and Training",
               "housing_and_services": "Housing and Access to Services",
               "geographic_barriers": "Geo Barriers (Access to Services)",
               "wider_barriers": "Wider Barriers (Housing)",
               "indoors": "Indoors Environment",
               "outdoors": "Outdoors Environment",
               "UK_IMD_E_rank": "Composite UK rankings"}


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
    name = "Recipient type"
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
    name = "Recipient type"
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
    name = "Representative gender"
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
    name = "Sender gender"
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
    name = "First use"
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
    name = "Got response"
    slug = "got_response"
    display_in_header = False
    description = "Result of survey asking if this is they got a response from their representative."
    require_columns = ["id"]

    def create_collection_column(self, df):

        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_first_time.csv"))
        lookup["answer"] = lookup["answer"].str.title()
        lookup.loc[lookup["answer"] == "Unsatisfactory", "answer"] = "Yes"
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
class AnsweredSurveyCollection(WTTCollection):
    name = "Answered survey"
    slug = "answer_survey"
    display_in_header = False
    description = "Did they receive a response at all. Investigating non-response bias."
    require_columns = ["id"]

    def create_collection_column(self, df):

        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_first_time.csv"))

        df[self.slug] = "No"
        df.loc[df["id"].isin(lookup["message_id"]), self.slug] = "Yes"
        return df

    def restrict_source_df(self, df):
        df = df[df[self.slug].isin(["Yes", "No"])]
        return df

    def get_labels(self):
        options = ["Yes", "No"]
        return [[x, ""] for x in options]


@wtt_register.register
class Gender(WTTAnalysis):

    name = "Messages by gender of sender"
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
    h_label = "First time contacting"
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
class AnsweredSurvey(WTTAnalysis):

    name = "Did the user answer the survey?"
    slug = "answer_survey"
    h_label = "Answered survey"
    description = ""
    group = "Characteristics"
    exclusions = ["first_use", "answer_survey"]
    description = "Did the user answer the survey at all? Used to gauge non-response bias."
    allowed_values = ["yes", "no"]
    verbose_allowed_values = ["Yes", "No"]
    overview = False
    require_columns = ["id"]

    def create_analysis_column(self):
        df = self.source_df

        lookup = pd.read_csv(
            join(self.source_folder, "questionnaire_first_time.csv"))

        df[self.slug] = "No"
        df.loc[df["id"].isin(lookup["message_id"]), self.slug] = "Yes"
        return df


@wtt_register.register
class GotResponse(WTTAnalysis):

    name = "Did they get a response?"
    slug = "response"
    h_label = "Response"
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

    name = "Messages by month"
    slug = "month"
    h_label = "Month"
    description = ""
    time_part = "month"
    description = "Month the message was sent."

    allowed_values = [x for x in range(1, 13)]
    verbose_allowed_values = [calendar.month_name[x][:3] for x in range(1, 13)]


@wtt_register.register
class Year(TimeAnalysis):

    name = "Messages by year"
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

    name = "Messages by hour of day"
    slug = "hour"
    h_label = "Hour"
    description = ""
    time_part = "hour"
    description = "Hour of the day the message was sent."
    overview = True

    allowed_values = [x for x in range(0, 24)]


@wtt_register.register
class Day(TimeAnalysis):

    name = "Messages by day of week"
    slug = "day"
    h_label = "Day of week"
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


@wtt_register.register
class Ruc(WTTAnalysis):
    name = "Messages by composite UK rural/urban classification"
    slug = "uk_ruc"
    h_label = "Composite RUC category"
    group = "UK IMD"
    description = "3 point urban-ruralness division. Urban/Rural matches English RUC definition (settlement > 10,000). 'More Rural' is equiv to Scottish definition (<3000)"
    allowed_values = [x for x in range(0, 3)]
    verbose_allowed_values = ['Urban', 'Rural', 'More Rural']
    require_columns = ["lsoa"]

    def create_analysis_column(self):

        df = self.source_df
        ruc = pd.read_csv(join(self.lookup_folder, "composite_ruc.csv"))
        ruc_map = ruc.set_index("lsoa")["ukruc-3"].to_dict()
        df[self.slug] = df["lsoa"].map(ruc_map)


@wtt_register.register
class Ruc(WTTAnalysis):
    name = "Messages by English rural/urban classification"
    slug = "ruc"
    h_label = "Composite RUC category"
    group = "English IMD"
    priority = 2
    description = "7 point urban-ruralness division - A1 (Major Urban), E2(Rural village - dispersed) "
    allowed_values = [x for x in range(1, 9)]
    verbose_allowed_values = ['A1',
                              'B1',
                              'C1',
                              'C2',
                              'D1',
                              'D2',
                              'E1',
                              'E2']
    require_columns = ["lsoa"]

    def create_analysis_column(self):

        df = self.source_df
        repeat = pd.read_csv(join(self.lookup_folder, "ruc_2011.csv"))
        repeat = repeat.set_index("lsoa")["ruralness"].to_dict()
        df[self.slug] = df["lsoa"].map(repeat)


@wtt_register.register
class DensityDeciles(WTTAnalysis):
    name = "Messages by population density"
    slug = "density_deciles"
    h_label = "Density deciles"
    group = "UK IMD"
    allowed_values = [x for x in range(1, 11)]
    description = "Reports sorted into ten deciles by how densely populated an area is. 1 is highest density, and 10 is lowest."
    require_columns = ["lsoa"]

    def create_analysis_column(self):
        df = self.source_df
        imd = pd.read_csv(join(self.lookup_folder, "composite_ruc.csv"))
        index_lookup = imd.set_index(
            "lsoa")["density_pop_decile"].to_dict()
        df[self.slug] = df["lsoa"].map(index_lookup)


for i in welsh_imds:
    # generate seperate classes for each w_imd

    nice_i = i.replace("_", " ").replace("-", " ").title()

    class GenericWIMD(WTTAnalysis):
        if i == "wimd":
            overview = True
            name = "Messages by Welsh index of multiple deprivation"
            slug = i
            h_label = "WIMD deciles"
            priority = 1
        else:
            overview = False
            name = "Messages by " + \
                nice_i.lower() + \
                " deprivation subdomain (Wales)"
            slug = "w_" + i
            h_label = "{0} deciles".format(nice_i)
        exclusions = ["mp_gender"]
        group = "Welsh IMD"
        column = i
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the Welsh Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "imd", "wimd2019.csv"))
            imd = imd[:-2]
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

    nice_i = i.replace("_", " ").replace("-", " ").title()

    class GenericEIMD(WTTAnalysis):
        if i == "imd":
            overview = True
            name = "Messages by English index of multiple deprivation"
            slug = i
            h_label = "IMD deciles"
            priority = 2
        else:
            overview = False
            name = "Messages by " + \
                english_name(nice_i).lower() + \
                " deprivation subdomain (England)"
            slug = "e_" + i
            h_label = "{0} deciles".format(nice_i)
        column = i
        exclusions = ["mp_gender"]
        group = "English IMD"
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the English Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "imd", "imd2019.csv"))
            index_lookup = imd.set_index(
                "lsoa")[self.__class__.column + "_decile"].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericEIMD.__name__ = GenericEIMD.slug
    wtt_register.register(GenericEIMD)

for i in uk_imds:

    class GenericUKIMD(WTTAnalysis):
        if i == "UK_IMD_E":
            overview = True
            name = "Messages by composite UK index of multiple deprivation"
            priority = 3
        if i == "GB_IMD_E":
            overview = False
            name = "Messages by composite GB index of multiple deprivation"
            priority = 2
        slug = i
        column = i
        exclusions = ["mp_gender"]
        h_label = "Composite UK deprivation deciles"
        group = "UK IMD"
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the composite Index of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure. This measure excludes NI."
        require_columns = ["lsoa"]

        def create_analysis_column(self):
            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "imd", f"{self.slug}.csv"))
            index_lookup = imd.set_index(
                "lsoa")[f"{self.slug}_pop_decile"].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericUKIMD.__name__ = GenericUKIMD.slug
    wtt_register.register(GenericUKIMD)

for i in scottish_imds:

    nice_i = i.replace("_", " ").replace("-", " ").title()

    class GenericSIMD(WTTAnalysis):
        if i == "simd":
            overview = True
            name = "Messages by Scottish index of multiple deprivation"
            slug = i
            h_label = "SIMD deciles"
            priority = 1
        else:
            overview = False
            name = "Messages by " + \
                nice_i.lower() + \
                " deprivation subdomain (Scotland)"
            slug = "s_" + i
            h_label = "{0} deciles".format(nice_i)
        column = i
        exclusions = ["mp_gender"]
        group = "Scottish IMD"
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the English Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "imd", "simd2020.csv"))
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
