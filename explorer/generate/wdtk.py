import datetime
import os
from collections import Counter
from useful_grid import QuickGrid
from .base import AnalysisRegister, AnalysisType, CollectionType
from .funcs import md5_hash
import calendar

import pandas as pd
from proj import settings
from functools import lru_cache
# when re-running this, fix the absolute references below
current_year = settings.WDTK_CURRENT_YEAR

join = os.path.join


@lru_cache(maxsize=None)
def get_value_lookup():
    lookup_folder = os.path.join("resources", "wdtk")
    df = QuickGrid().open(
        [lookup_folder, "survey_lookup.csv"], force_unicode=True)
    return df


class wdtk_register(AnalysisRegister):
    service = "wdtk"


class WDTKCollection(CollectionType):
    lookup_folder = os.path.join("resources", "wdtk")
    lookup_value = ""

    def label_lookup(self):
        df = get_value_lookup()
        items = [x for x in df if x["qid"] == self.__class__.lookup_value]
        items = [x for x in items if "select" not in x["aname"]]
        return {x["aid"]: x["aname"] for x in items}

    def get_labels(self):
        df = get_value_lookup()
        items = [x["aname"]
                 for x in df if x["qid"] == self.__class__.lookup_value]
        items = [x for x in items if "select" not in x]
        items = [[x, None] for x in items]

        return items


class WDTKAnalysis(AnalysisType):
    source_folder = settings.WDTK_EXPLORER_SOURCE
    experiment_folder = os.path.join(source_folder, "grid")
    processed_folder = os.path.join(source_folder, "processed")
    lookup_folder = os.path.join("resources", "wdtk")
    pickle_folder = os.path.join(source_folder, "pickle")
    source_file = os.path.join(
        source_folder, "survey_reduced.csv")
    create_analysis = False

    def load_verbose_allowed_values(self):

        df = get_value_lookup()

        items = [x for x in df if x["qid"] ==
                 self.slug and "select" not in x["aname"]]
        items.sort(key=lambda x: int(x["aid"]))
        done = []
        final = []
        for i in items:
            if i["aid"] not in done:
                final.append(i["aname"])
                done.append(i["aid"])

        return final

    def load_allowed_values(self):

        df = get_value_lookup()

        items = [x for x in df if x["qid"] ==
                 self.slug and "select" not in x["aname"]]
        items.sort(key=lambda x: int(x["aid"]))
        done = []
        final = []
        for i in items:
            if i["aid"] not in done:
                final.append(i["aid"])
                done.append(i["aid"])

        return final

    def create_analysis_column(self):
        """
        not needed because all columns exist without transformation
        """
        if self.__class__.create_analysis:
            super().create_analysis_column()


@wdtk_register.register
class YearCollection(WDTKCollection):
    name = "Year"
    slug = "year"
    display_in_header = False
    description = "Emails grouped by year"
    time_part = "year"
    require_columns = ["whenstored"]

    def create_collection_column(self, df):

        df[self.slug] = df["whenstored"].str.slice(start=-4).astype('int')

    def get_labels(self):
        return [[str(x), ""] for x in range(2012, current_year + 1)]


@wdtk_register.register
class AuthorityType(WDTKCollection):
    name = "Authority type"
    slug = "authority_type"
    description = "The kind of local authority the request was sent to."
    default = True
    require_columns = ["authority"]
    lookup_value = "authority"

    def create_collection_column(self, df):
        df[self.slug] = df["authority"]
        return df


@wdtk_register.register
class PreviousUse(WDTKCollection):
    name = "Previous FOI use"
    slug = "previous_foi_use"
    description = "If users previously sent an FOI. "
    require_columns = ["previouscontact"]
    lookup_value = "previouscontact"

    def create_collection_column(self, df):
        df[self.slug] = df["previouscontact"]

        return df


@wdtk_register.register
class MessageConcern(WDTKCollection):
    name = "Message concern"
    slug = "messageconcern"
    description = "The purpose of the request"
    lookup_value = "messageconcern"

    def create_collection_column(self, df):
        return df


@wdtk_register.register
class Gender(WDTKAnalysis):

    name = "Requests by gender of sender"
    slug = "gender"
    h_label = "Gender"
    group = "Demographics"
    overview = True
    description = "Gender of sender as declared in survey."


@wdtk_register.register
class Age(WDTKAnalysis):

    name = "Requests by age of sender"
    slug = "age"
    h_label = "Age"
    group = "Demographics"
    overview = True
    description = "Age of sender as declared in survey."

    def reorder_columns(self, columns):
        def change(v):
            lv = v.lower().strip()
            lv = lv.replace("less than", "")
            return lv[0]
        columns = list(columns)
        columns.sort(key=change)
        return columns

@wdtk_register.register
class Education(WDTKAnalysis):

    name = "Requests by education of sender"
    slug = "education_any"
    h_label = "Education"
    group = "Demographics"
    description = "Education of sender as declared in survey."


@wdtk_register.register
class Lifestage(WDTKAnalysis):

    name = "Requests by lifestage of sender"
    slug = "lifestage"
    h_label = "Lifestage"
    group = "Demographics"
    description = "Lifestage of sender as declared in survey."
    overview = True


@wdtk_register.register
class Income(WDTKAnalysis):

    name = "Requests by income of sender"
    slug = "income"
    h_label = "Income"
    group = "Demographics"
    description = "Income of sender as declared in survey."


@wdtk_register.register
class Ethnicity(WDTKAnalysis):
    name = "Requests by ethnicity of sender"
    slug = "ethnicity"
    h_label = "Ethnicity"
    group = "Demographics"
    description = "Ethnicity of sender as declared in survey."


@wdtk_register.register
class BAME(WDTKAnalysis):
    name = "Requests by Ethnicity (grouped)"
    slug = "bame"
    h_label = "Ethnicity (grouped)"
    group = "Demographics"
    description = "Grouped ethnicity of sender as declared in survey."
    create_analysis = True
    require_columns = ["ethnicity"]

    def create_analysis_column(self):

        df = self.source_df

        white = ["British",
                 "English",
                 "Welsh",
                 "Scottish",
                 "Irish",
                 "Other white",
                 ]

        na = ["Don't know",
              "Don't want to answer"]

        vdf = get_value_lookup()

        items = [x for x in vdf if x["qid"] ==
                 "ethnicity" and "select" not in x["aname"]]
        items.sort(key=lambda x: int(x["aid"]))
        lookup = {x["aid"]: x["aname"] for x in items}

        df["ethnicity"] = df["ethnicity"].map(lookup)

        df[self.slug] = "Ethnic minority (excluding white minorities)"
        df.loc[df["ethnicity"].isin(white), self.slug] = "White ethnicities"
        df.loc[df["ethnicity"].isin(na), self.slug] = "NA"

        return df


@wdtk_register.register
class Disability(WDTKAnalysis):
    name = "Requests by if sender has a disability"
    slug = "disability"
    h_label = "Disability"
    group = "Demographics"
    description = "Disability of sender as declared in survey."


@wdtk_register.register
class Activity(WDTKAnalysis):
    name = "Users who have taken part in political activity"
    slug = "activity"
    h_label = "Users who have taken part in political activity"
    group = "Participation"
    description = "Political activity is here prompted as demonstrations, signing a petition, contacting a politician, boycotting a product, donating money or displaying a campaign badge."


@wdtk_register.register
class Groups(WDTKAnalysis):
    name = "Users who have taken part in political or community groups"
    slug = "groups"
    h_label = "Users who have taken part in political activity"
    group = "Participation"
    description = "Users who have taken part in political activity - e.g formal member or volunteering"


# requester wdtk

@wdtk_register.register
class PreviousContact(WDTKAnalysis):
    name = "Previously made an FOI request"
    slug = "previouscontact"
    h_label = "Previous FOI"
    group = "Participation"
    exclusions = ["previous_foi_use"]
    description = "Previous FOI methods as declared in survey."


@wdtk_register.register
class UseFrequency(WDTKAnalysis):
    name = "How often users make FOI requests"
    slug = "usefrequency"
    h_label = "How often users make FOI requests?"
    group = "Participation"
    description = "Frequency of FOI use as declared in survey."


@wdtk_register.register
class InternetAbility(WDTKAnalysis):
    name = "How users rate their ability to use the internet"
    slug = "internetability"
    h_label = "How do users rate their ability to use the internet?"
    group = "Demographics"
    description = "Internet reliability use as declared in survey."

# message


class TimeAnalysis(WDTKAnalysis):
    group = "Request"
    time_part = ""
    create_analysis = True
    require_columns = ["whenstored"]

    def create_analysis_column(self):
        """
        add column based on time
        """
        df = self.source_df
        print("creating column: {0}".format(self.slug))
        dt = pd.to_datetime(df['whenstored'], format='%d/%m/%Y')
        df[self.slug] = getattr(dt.dt, self.__class__.time_part)


@wdtk_register.register
class Year(TimeAnalysis):

    name = "Requests by year"
    slug = "year"
    h_label = "Year"
    description = ""
    time_part = "year"
    description = "Year the message was sent."
    exclusions = ["year"]

    allowed_values = [x for x in range(2012, current_year + 1)]
    overview = True


@wdtk_register.register
class Referrer(WDTKAnalysis):
    name = "How did user find out about WDTK"
    slug = "referrer"
    h_label = "How did user find out about WDTK"
    group = "WDTK"
    description = "How did user find out about WDTK as declared in survey."
    overview = True


@wdtk_register.register
class NetPromoter(WDTKAnalysis):
    name = "Would user recommend to friend"
    slug = "netpromoter"
    h_label = "Would user recommend to friend?"
    group = "WDTK"
    description = "Would user recommend WDTK as declared in survey."

    def reorder_columns(self, columns):
        def change(v):
            lv = v[:2].strip()
            if len(lv) == 1:
                lv = "0" + lv
            return lv
        columns = list(columns)
        columns.sort(key=change)
        return columns


@wdtk_register.register
class MessageConcernA(WDTKAnalysis):
    name = "Who is information relevant for"
    slug = "messageconcern"
    h_label = "Information is relevant for"
    group = "Request"
    description = "Who would information be relevant for as declared in survey."
    exclusions = ["messageconcern"]
    overview = True


@wdtk_register.register
class OpinionDesign(WDTKAnalysis):
    name = "WhatDoTheyKnow is pretty to look at"
    slug = "opinion_design"
    h_label = "WhatDoTheyKnow is pretty to look at"
    group = "WDTK"


@wdtk_register.register
class OpinionDesign(WDTKAnalysis):
    name = "WhatDoTheyKnow is easy to navigate"
    slug = "opinion_navigation"
    h_label = "WhatDoTheyKnow is easy to navigate"
    group = "WDTK"


@wdtk_register.register
class OpinionDesign(WDTKAnalysis):
    name = "WhatDoTheyKnow provides objective and unpartisan info"
    slug = "opinion_objectivity"
    h_label = "WhatDoTheyKnow provides objective and unpartisan info"
    group = "WDTK"


@wdtk_register.register
class OpinionDesign(WDTKAnalysis):
    name = "WhatDoTheyKnow is well structured"
    slug = "opinion_structure"
    h_label = "WhatDoTheyKnow is well structured"
    group = "WDTK"


@wdtk_register.register
class RegisteredUser(WDTKAnalysis):
    name = "Declares as registered user"
    slug = "registration"
    h_label = "Declares as registered user"
    group = "WDTK"
    description = "Says is registered user - note, all people who take survey must be registered users."


@wdtk_register.register
class MessageConcernA(WDTKAnalysis):
    name = "User got response"
    slug = "response"
    h_label = "User got response"
    group = "Request"
    exclusions = ["messageconcern"]
    description = "User got response for as declared in survey."


@wdtk_register.register
class Satisfied(WDTKAnalysis):
    name = "Users were satifised by response"
    slug = "satisfaction"
    h_label = "Users were satifised by response"
    group = "Request"
    description = "User was satisifed by response as declared in survey."


@wdtk_register.register
class Followup(WDTKAnalysis):
    name = "User took follow-up action"
    slug = "followupaction"
    h_label = "User took follow-up action"
    group = "Request"
    description = "User took follow-up action"


@wdtk_register.register
class Dialogue(WDTKAnalysis):
    name = "User will get in touch with authority again"
    slug = "dialogue"
    h_label = "User will get in touch with authority again"
    group = "Request"
    description = "User will get in touch with authority again"
