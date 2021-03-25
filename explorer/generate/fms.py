import calendar
import datetime
import os
from collections import Counter

import numpy as np
import pandas as pd
from django.conf import settings
from useful_grid import QuickGrid

from .base import AnalysisRegister, AnalysisType, CollectionType
from .funcs import md5_hash

join = os.path.join

current_year = settings.FMS_CURRENT_YEAR

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

uk_imds = ["UK_IMD_E", "GB_IMD_E"]

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


class fms_register(AnalysisRegister):
    service = "fms"


class FMSCollection(CollectionType):
    source_folder = settings.FMS_EXPLORER_SOURCE
    lookup_folder = os.path.join(settings.FMS_EXPLORER_SOURCE, "lookups")


class FMSAnalysis(AnalysisType):
    source_folder = settings.FMS_EXPLORER_SOURCE
    lookup_folder = os.path.join("resources", "fms")
    experiment_folder = os.path.join(source_folder, "grid")
    processed_folder = os.path.join(source_folder, "processed")
    pickle_folder = os.path.join(source_folder, "pickle")
    source_file = os.path.join(source_folder, "merged_points_whole_years.csv")


@fms_register.register
class RepeatUse(FMSCollection):
    name = "Repeat use"
    slug = "repeat_use"
    display_in_header = False
    description = "First vs subsequent reports by this user on FMS"
    require_columns = ["id", "first_report_by_user"]

    def create_collection_column(self, df):
        map = {True: "First Report",
               False: "Reported Before"}
        df[self.slug] = df["first_report_by_user"].map(map)

    def get_labels(self):
        return [[str(x), ""] for x in ["First Report", "Reported Before"]]


@fms_register.register
class RepeatUse(FMSCollection):
    name = "Answered survey"
    slug = "answered_survey"
    display_in_header = False
    description = "Answered the survey. Checking for non-response bias."
    require_columns = ["id"]

    def create_collection_column(self, df):

        survey_responses = pd.read_csv(
            join(settings.FMS_EXPLORER_SOURCE, "survey_response.csv"))

        df[self.slug] = "No"
        df.loc[df["id"].isin(survey_responses["id"]), self.slug] = "Yes"

        return df

    def get_labels(self):
        return [[str(x), ""] for x in ["Yes", "No"]]


@fms_register.register
class YearCollection(FMSCollection):
    name = "Year"
    slug = "year"
    display_in_header = False
    description = "Shows counts and distributions of variables on a yearly basis."
    time_part = "year"
    require_columns = ["created"]

    def create_collection_column(self, df):

        df[self.slug] = df["created"].str.slice(stop=4).as_type('float')

    def get_labels(self):
        return [[str(x), ""] for x in range(2007, current_year + 1)]


@fms_register.register
class ACategories(FMSCollection):
    name = "A categories"
    slug = "SHEF_A"
    display_in_header = False
    description = ("Grouping of FixMyStreet Categories into 94 A Categories "
                   "- [More Info](https://github.com/mysociety/fms_meta_categories).")
    require_columns = [slug]

    def get_labels(self):
        lookup = self.__class__.slug
        df = pd.read_csv(join("resources", "fms", lookup + ".csv"))
        final = []
        for n, r in df.iterrows():
            final.append([r[self.__class__.slug], r["category"]])
        return final


@fms_register.register
class BCategories(ACategories):
    name = "B categories"
    slug = "SHEF_B"
    default = True
    display_in_header = False
    description = ("Grouping of FixMyStreet Categories into 29 B Categories "
                   "- [More Info](https://github.com/mysociety/fms_meta_categories).")
    require_columns = [slug]


@fms_register.register
class CCategories(ACategories):
    name = "C categories"
    slug = "SHEF_C"
    display_in_header = True
    description = ("Grouping of FixMyStreet Categories into 8 C Categories"
                   " - [More Info](https://github.com/mysociety/fms_meta_categories).")
    require_columns = [slug]


@fms_register.register
class ReportedFixed(FMSCollection):
    name = "Status"
    slug = "status"
    lookup = None
    md5_lookup = None
    display_in_header = False
    description = ("Reports reported as fixed by user or council - "
                   "this doesn't accurately reflect the true 'fixed' rate as many "
                   "reports are not updated - but the difference in different "
                   "contexts can still be interesting. Reflects a mix of differences "
                   "in how problems are fixed, and differences in if people "
                   "report a problem is fixed.")
    require_columns = [slug, "id"]

    def create_collection_column(self, df):

        if self.__class__.lookup == None:
            fi = pd.read_csv(join(self.source_folder, "fixed_ids.csv"))
            ids = fi["id"]
            lookup = set(ids)
            self.__class__.lookup = lookup
        else:
            lookup = self.__class__.lookup

        df[self.slug] = "Not Reported Fixed"
        df.loc[df["id"].isin(ids), self.slug] = "Reported Fixed"

        return df

    def get_labels(self):

        options = ["Reported Fixed", "Not Reported Fixed"]
        return [[x, ""] for x in options]


@fms_register.register
class ReportedFixedCouncil(FMSCollection):
    name = "Fixed (council)"
    slug = "status-council"
    lookup = None
    md5_lookup = None
    display_in_header = False
    description = ("Only looks at those reported fixed by council vs all other reports. "
                   "Useful as control on conclusions from user-reported fixes (see 'status'). Updates from council "
                   "are via staff accounts or feedback through Open311")
    require_columns = ["id"]

    def create_collection_column(self, df):

        if self.__class__.lookup is None:
            fi = pd.read_csv(join(self.source_folder, "fixed_ids.csv"))
            ids = fi["id"][fi["state"] == "fixed - council"]
            lookup = set(ids)
            self.__class__.lookup = lookup
        else:
            lookup = self.__class__.lookup

        df[self.slug] = "No"
        df.loc[df["id"].isin(lookup), self.slug] = "Yes"

        return df

    def get_labels(self):

        options = ["Yes", "No"]
        return [[x, ""] for x in options]


@fms_register.register
class MethodCollection(FMSCollection):
    name = "Reporting method"
    slug = "method"
    lookup = None
    md5_lookup = None
    description = "There are different ways reports can be made. FixMyStreet.com represents reports made by FixMyStreet.com, Mobile reports are made on an app, and Cobrand are made through [cobranded websites](https://www.fixmystreet.com/pro/)."
    require_columns = ["id", "cobrand"]

    def create_collection_column(self, df):

        if self.__class__.lookup is None:
            lookup = pd.read_csv(join(self.source_folder, "service_ids.csv"))
            ids = lookup["id"]
            lookup = set(ids)
            self.__class__.lookup = lookup
        else:
            lookup = self.__class__.lookup

        df[self.slug] = "Cobrand"
        df.loc[(df["cobrand"] == "fixmystreet"), self.slug] = "FixMyStreet.com"
        df.loc[df["cobrand"].isnull(), self.slug] = "FixMyStreet.com"
        df.loc[df["id"].isin(lookup), self.slug] = "Mobile"

        return df

    def get_labels(self):

        options = ["Cobrand", "Mobile", "FixMyStreet.com"]
        return [[x, ""] for x in options]


@fms_register.register
class Gender(FMSAnalysis):

    name = "Reports by gender"
    slug = "gender"
    h_label = "Gender"
    description = "Gender is derived from name. Inconclusive names are dropped, so this represents less than 100% of the dataset. "
    group = "Characteristics"
    overview = True
    priority = 2

    unit = "gender"
    allowed_values = ["male", "female"]
    verbose_allowed_values = ["Male", "Female"]
    require_columns = ["derived_gender"]

    def create_analysis_column(self):
        df = self.source_df
        func = self.transform_function()
        print("creating column: {0}".format(self.slug))
        df[self.slug] = df["derived_gender"]


@fms_register.register
class MethodAnalysis(FMSAnalysis):

    name = "Reports by method of report"
    slug = "method"
    h_label = name
    description = "There are different ways reports can be made. FixMyStreet.com represents reports made by FixMyStreet.com, Mobile reports are made on an app, and Cobrand are made through [cobranded websites](https://www.fixmystreet.com/pro/)."
    group = "Characteristics"
    overview = True
    exclusions = ["method", "cobrand"]
    allowed_values = ["Cobrand", "Mobile", "FixMyStreet.com"]
    require_columns = ["id", "cobrand"]

    lookup = None
    md5_lookup = None

    def create_analysis_column(self):

        df = self.source_df
        if self.__class__.lookup is None:
            lookup = pd.read_csv(join(self.source_folder, "service_ids.csv"))
            lookup = set(lookup["id"])
            self.__class__.lookup = lookup
        else:
            lookup = self.__class__.lookup

        df[self.slug] = "Cobrand"
        df.loc[df["cobrand"] == "fixmystreet", self.slug] = "FixMyStreet.com"
        df.loc[df["cobrand"].isnull(), self.slug] = "FixMyStreet.com"
        df.loc[df["id"].isin(lookup), self.slug] = "Mobile"

        print("done")


@ fms_register.register
class Survey(FMSAnalysis):

    name = "Reports made as first report (ever)"
    slug = "first_report_survey"
    h_label = "Repeat report (survey)"
    description = "Results of a survey asking if this is first time someone has reported an issue to a council."
    group = "Characteristics"
    require_columns = ["id"]

    def add_columns(self, df):
        """
        restrict to survey answers only and append
        """
        survey_responses = pd.read_csv(
            join(settings.FMS_EXPLORER_SOURCE, "survey_response.csv"))

        ids = set(survey_responses["id"])
        lookup = survey_responses.set_index("id")["ever_reported"].to_dict()

        df["ever_reported"] = df["id"].map(lookup)

        self.stored_ids = ids

        return df

    def restrict_source_df(self, df):
        df = df[df["id"].isin(self.stored_ids)]
        return df

    def create_analysis_column(self):

        df = self.source_df
        df[self.slug] = "First Report"
        df.loc[df["ever_reported"] == 0, self.slug] = "Reported Before"


@ fms_register.register
class Photo(FMSAnalysis):

    name = "Photo submitted with report"
    slug = "photo"
    h_label = "Photo submitted"
    description = "FixMyStreet allows photos of problems to be uploaded. This variable covers if a report has an attached photo."
    group = "Characteristics"
    lookup = None
    require_columns = ["id"]

    def get_lookup(self):
        """
        get photo lookup
        """
        if self.__class__.lookup == None:
            lookup = pd.read_csv(
                join(settings.FMS_EXPLORER_SOURCE, "photo_ids.csv"))
            ids = set(lookup["id"])
            self.__class__.lookup = ids
        return self.__class__.lookup

    def create_analysis_column(self):
        df = self.source_df
        lookup = self.get_lookup()
        df[self.slug] = "No Photo"
        df.loc[df["id"].isin(lookup), self.slug] = "Photo"


@ fms_register.register
class FixedAnalysis(FMSAnalysis):

    name = "Reported fixed"
    slug = "fixed"
    h_label = "Problem reported fixed"
    description = ("Reports reported as fixed by user or council - this "
                   "doesn't accurately reflect the true 'fixed' rate as "
                   "many reports are not updated - but the difference "
                   "in different contexts can still be useful.")
    group = "Characteristics"
    exclusions = ["status", "status-council"]
    lookup = None

    def get_lookup(self):
        """
        get photo lookup
        """
        if self.__class__.lookup == None:
            lookup = pd.read_csv(
                join(settings.FMS_EXPLORER_SOURCE, "fixed_ids.csv"))
            ids = set(lookup["id"])
            self.__class__.lookup = ids
        return self.__class__.lookup

    def create_analysis_column(self):
        df = self.source_df
        lookup = self.get_lookup()
        df[self.slug] = "Not Reported Fixed"
        df.loc[df["id"].isin(lookup), self.slug] = "Reported Fixed"


class TimeAnalysis(FMSAnalysis):
    group = "Time"
    time_part = ""
    require_columns = ["created"]

    def create_analysis_column(self):
        """
        add column based on time
        """
        df = self.source_df
        print("creating column: {0}".format(self.slug))
        dt = pd.to_datetime(df['created'], format='%Y-%m-%d %H:%M:%S.%f')
        df[self.slug] = getattr(dt.dt, self.__class__.time_part)


@ fms_register.register
class Month(TimeAnalysis):

    name = "Reports by month"
    slug = "month"
    h_label = "Month"
    description = "Which month of the year a report was made in."
    time_part = "month"

    allowed_values = [x for x in range(1, 13)]
    verbose_allowed_values = [calendar.month_name[x][:3] for x in range(1, 13)]


@ fms_register.register
class Year(TimeAnalysis):

    name = "Reports by year"
    slug = "year"
    h_label = "Year"
    description = "Which year a report was made in."
    time_part = "year"
    exclusions = ["year"]

    allowed_values = [x for x in range(2007, current_year + 1)]


@ fms_register.register
class Hour(TimeAnalysis):

    name = "Reports by hour of day"
    slug = "hour"
    h_label = "Hour"
    description = "Which hour of the day a report was made in. 1 represents reports between 1AM and 2PM"
    time_part = "hour"
    overview = True
    priority = 2
    allowed_values = [x for x in range(0, 24)]


@ fms_register.register
class Day(TimeAnalysis):

    name = "Reports by day of week"
    slug = "day"
    h_label = "Day of week"
    description = "Which day of the week a report was made on."
    time_part = "dayofweek"

    allowed_values = [x for x in range(0, 7)]
    verbose_allowed_values = ['Monday',
                              'Tuesday',
                              'Wednesday',
                              'Thursday',
                              'Friday',
                              'Saturday',
                              'Sunday']


@ fms_register.register
class Repeat(FMSAnalysis):
    name = "Reports made as first report (via FMS)"
    h_label = "Repeat report (FMS)"
    slug = "first_fms_report"
    group = "Characteristics"
    description = "Using the user associated with a report, this tracks if it was the first or subsequent report a user made."
    exclusions = ["repeat_use"]
    require_columns = ["id", "first_report_by_user"]
    allowed_values = ["First Report", "Reported Before"]

    def create_analysis_column(self):

        df = self.source_df
        map = {True: "First Report",
               False: "Reported Before"}
        df[self.slug] = df["first_report_by_user"].map(map)


@fms_register.register
class Ruc(FMSAnalysis):
    name = "Reports by composite UK rural/urban classification"
    slug = "uk_ruc"
    h_label = "Composite RUC category"
    group = "UK IMD"
    description = "3 point urban-ruralness division. Urban/Rural matches English RUC definition. 'More Rural' is equiv to Scottish definition."
    allowed_values = [x for x in range(0, 3)]
    verbose_allowed_values = ['Urban', 'Rural', 'More Rural']
    require_columns = ["lsoa"]

    def create_analysis_column(self):

        df = self.source_df
        ruc = pd.read_csv(join(self.lookup_folder, "composite_ruc.csv"))
        ruc_map = ruc.set_index("lsoa")["ukruc-3"].to_dict()
        df[self.slug] = df["lsoa"].map(ruc_map)


@fms_register.register
class Ruc(FMSAnalysis):
    name = "Reports by English rural/urban classification"
    slug = "ruc"
    h_label = "Composite RUC category"
    group = "English IMD"
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


@ fms_register.register
class UserCount(FMSAnalysis):
    name = "User activity"
    h_label = "Number of reports made"
    slug = "user_count"
    group = "Characteristics"
    description = "Using the user associated with a report, this tracks if the report was made by a user who makes few or many reports."
    allowed_values = ["One Report",
                      "2-20 Reports",
                      "21-50 Reports",
                      "50+ Reports"]
    require_columns = ["id"]

    def create_analysis_column(self):

        df = self.source_df
        repeat = pd.read_csv(
            join(settings.FMS_EXPLORER_SOURCE, "first_report.csv"))
        repeat = repeat.set_index("id")["user_count"].to_dict()

        df["user_count"] = df["id"].map(repeat)

        conditions = [
            (df['user_count'] == 1),
            (df['user_count'] > 1) & (df['user_count'] <= 20),
            (df['user_count'] > 20) & (df['user_count'] <= 50),
            (df['user_count'] > 50)
        ]

        values = ["One Report", "2-20 Reports", "21-50 Reports", "50+ Reports"]

        df[self.slug] = np.select(conditions, values)


@fms_register.register
class DensityDeciles(FMSAnalysis):
    name = "Reports by population density"
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

# generate seperate classes for each w_imd


for i in welsh_imds:
    nice_i = i.replace("_", " ").replace("-", " ").title()

    class GenericWIMD(FMSAnalysis):
        if i == "wimd":
            overview = True
            name = "Reports by Welsh index of multiple deprivation"
            slug = i
            priority = 1
            h_label = "WIMD deciles"
        else:
            overview = False
            name = f"Reports by {nice_i.lower()} deprivation subdomain (Wales)"
            slug = "w_" + i
            h_label = f"{nice_i} deciles"
        exclusions = ["cobrand"]

        description = "Reports sorted by the decile rank in against the Welsh Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        group = "Welsh IMD"
        column = i
        allowed_values = [x for x in range(1, 11)]
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

    GenericWIMD.__name__ == GenericWIMD.slug
    fms_register.register(GenericWIMD)

for i in english_imds:

    class GenericEIMD(FMSAnalysis):
        if i == "imd":
            overview = True
            name = "Reports by English index of multiple deprivation"
            slug = i
            priority = 2
            h_label = "IMD deciles"
        else:
            overview = False
            name = "Reports by " + \
                english_name(i).lower() + \
                " deprivation (England)"
            slug = "e_" + i
            h_label = "{0} deciles".format(english_name(i))
        column = i
        exclusions = ["cobrand"]
        group = "English IMD"
        unit = "Deprivation decile"
        description = "Reports sorted by the decile rank in against the English Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        allowed_values = [x for x in range(1, 11)]
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(join(self.lookup_folder, "imd", "imd2019.csv"))
            index_lookup = imd.set_index(
                "lsoa")[self.__class__.column + "_decile"].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericEIMD.__name__ == GenericEIMD.slug
    fms_register.register(GenericEIMD)


for i in uk_imds:

    nice_i = i.replace("_", " ").replace("-", " ").title()

    class GenericUKIMD(FMSAnalysis):
        if i == "UK_IMD_E":
            overview = True
            name = "Reports by composite UK index of multiple deprivation"
            priority = 3
        if i == "GB_IMD_E":
            overview = False
            name = "Reports by composite GB index of multiple deprivation"
            priority = 2
        slug = i
        column = i
        exclusions = ["cobrand"]
        h_label = "Composite UK deprivation deciles"
        group = "UK IMD"
        allowed_values = [x for x in range(1, 11)]
        description = "Reports sorted by the decile rank in against the composite Index of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure. This measure excludes NI."
        require_columns = ["lsoa"]

        def create_analysis_column(self):

            df = self.source_df
            imd = pd.read_csv(
                join(self.lookup_folder, "imd", f"{self.slug}.csv"))
            index_lookup = imd.set_index(
                "lsoa")[self.slug + "_pop_decile"].to_dict()
            df[self.slug] = df["lsoa"].map(index_lookup)

    GenericUKIMD.__name__ = GenericUKIMD.slug
    fms_register.register(GenericUKIMD)

for i in scottish_imds:

    nice_i = i.replace("_", " ").replace("-", " ").title()

    class GenericSIMD(FMSAnalysis):
        if i == "simd":
            overview = True
            name = "Reports by Scottish index of multiple deprivation"
            slug = i
            priority = 1
            h_label = "SIMD Deciles"
        else:
            overview = False
            name = "Reports by " + \
                nice_i.lower() + \
                " deprivation subdomain (Scotland)"
            slug = "s_" + i
            h_label = "{0} deciles".format(nice_i)
        column = i
        exclusions = ["cobrand"]
        description = "Reports sorted by the decile rank in against the Scottish Indices of Multiple Deprivation of the LSOA a report was made in.\n Lower deciles are more deprived, while higher deciles are better off on this measure."
        group = "Scottish IMD"
        unit = "Deprivation decile"
        allowed_values = [x for x in range(1, 11)]
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

    GenericSIMD.__name__ == GenericSIMD.slug
    fms_register.register(GenericSIMD)


class fms_no_cobrands(AnalysisRegister):
    service = "fms-no-cobrands"
    require_columns = ["cobrand"]

    def get_restriction_function(self):

        def inner(df):
            allowed = set(["", "fixmystreet"])
            df = df[df["cobrand"].isin(allowed)]
            return df

        return inner


fms_no_cobrands.clone(fms_register, exclude=[
                      "MethodCollection", "MethodAnalysis"])


@fms_no_cobrands.register
class NoCoMethodCollection(FMSCollection):
    name = "Reporting method"
    slug = "method"
    lookup = None
    md5_lookup = None
    description = "There are different ways reports can be made. FixMyStreet.com represents reports made by FixMyStreet.com, Mobile reports are made on an app, and Cobrand are made through [cobranded websites](https://www.fixmystreet.com/pro/)."
    require_columns = ["id"]

    def create_collection_column(self, df):

        df = self.source_df
        if self.__class__.lookup is None:
            lookup = pd.read_csv(join(self.source_folder, "service_ids.csv"))
            lookup = set(lookup["id"])
            self.__class__.lookup = lookup
        else:
            lookup = self.__class__.lookup

        df[self.slug] = "Cobrand"
        df.loc[~(df["cobrand"] == "fixmystreet"),
               self.slug] = "FixMyStreet.com"
        df.loc[~df["cobrand"].isnull(), self.slug] = "FixMyStreet.com"
        df.loc[df["id"].isin(lookup), self.slug] = "Mobile"

        print("done")

    def get_labels(self):

        options = ["Mobile", "FixMyStreet.com"]
        return [[x, ""] for x in options]


@fms_no_cobrands.register
class NoCoMethodAnalysis(FMSAnalysis):

    name = "Reports by method of report"
    slug = "method"
    h_label = "Method used to report"
    description = "There are different ways reports can be made. FixMyStreet.com represents reports made by FixMyStreet.com, Mobile reports are made on an app, and Cobrand are made through [cobranded websites](https://www.fixmystreet.com/pro/)."
    group = "Characteristics"
    overview = True
    exclusions = ["method", "cobrand"]
    require_columns = ["id"]

    allowed_values = ["Mobile", "FixMyStreet.com"]

    lookup = None
    md5_lookup = None

    def create_analysis_column(self):

        df = self.source_df
        if self.__class__.lookup == None:
            lookup = pd.read_csv(join(self.source_folder, "service_ids.csv"))
            ids = lookup["id"]
            lookup = set(ids)
            self.__class__.lookup = lookup
        else:
            lookup = self.__class__.lookup

        df[self.slug] = "Cobrand"
        df.loc[(df["cobrand"] == "fixmystreet"), self.slug] = "FixMyStreet.com"
        df.loc[df["cobrand"].isnull(), self.slug] = "FixMyStreet.com"
        df.loc[df["id"].isin(lookup), self.slug] = "Mobile"


class fms_base_year(AnalysisRegister):
    """
    Create a class for records restrainted to a single year 
    """
    service = "fms_2018"
    year = "2018"
    require_columns = ["created"]

    def __init__(self):
        super().__init__()
        self.index_cache = None

    def get_restriction_function(self):

        def inner(df):
            if self.index_cache is None:
                analysis_year = str(self.__class__.year)
                year = df["created"].str.slice(stop=4)
                index = year == analysis_year
                self.index_cache = index
            else:
                index = self.index_cache

            df = df[index]
            return df

        return inner


years = range(2019, current_year+1)
year_clones = []

for y in years:

    name = "fms_{0}".format(y)

    class fms_year(fms_base_year):
        """
        FMS reports made in {0}
        """.format(y)
        service = name
        year = str(y)

    fms_year.__name__ == name
    fms_year.clone(fms_register, exclude=[
        "YearCollection", "Year"])

    year_clones.append(fms_year)


if __name__ == "__main__":
    fms_register.run_all()
