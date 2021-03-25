import calendar
import datetime
import os
from collections import Counter

import numpy as np
import pandas as pd
from useful_grid import QuickGrid, QuickText

regenerate_processed = False

# store the final product in the project directory
# rather than the source folder
# can be committed to allow database to be regenerated
store_in_demographics_folder = True

join = os.path.join


def clean_zero_columns(df):
    """
    remove columns with only zero values
    """
    headers = df.columns[1:]
    remove = []
    for h in headers:
        values = df[h].sum()
        if values == 0:
            remove.append(h)

    df = df.drop(columns=remove)
    return df


class CollectionType(object):
    """
    Items to be examined by analysis (usually discreet - like categories)
    """
    name = ""
    slug = ""
    lookup_folder = r""
    lookup_file = ""
    description = ""
    display_in_header = True
    default = False
    stored_labels = None
    require_columns = []

    def __init__(self):
        transitions = ["name",
                       "slug"]

        for t in transitions:
            setattr(self, t, getattr(self.__class__, t))

    def create_collection_column(self, df):
        """
        create column for the items to be examined if these are not already present
        """
        return df

    def _get_labels(self):
        if self.__class__.stored_labels is None:
            self.__class__.stored_labels = self.get_labels()
        return self.__class__.stored_labels

    def restrict_source_df(self, df):
        """
        override if an analysis can only work on a subset of the data
        """
        return df

    def get_labels(self):
        """
        returns a list of two item lists
        first is meta categories, 
        second is categories
        blank values are ignored
        """
        return []

    def allowed_values(self):
        labels = self._get_labels()
        labels = [x[0] for x in labels]
        return labels

    def label_lookup(self):
        return {}


class AnalysisType(object):
    """
    An analysis type (time, IMD, etc)
    """
    source_folder = r""
    experiment_folder = r""
    processed_folder = r""
    pickle_folder = r""

    name = ""
    slug = ""
    h_label = "Category"
    description = ""
    group = ""
    overview = False
    exclusions = []
    _register = None

    priority = 0
    source_file = ""
    allowed_values = []  # if blank uses all values of property
    verbose_allowed_values = []  # list of nicer namers for the allowed values
    use_passthrough_cross = False
    require_columns = []

    @classmethod
    def check_folders(cls):
        """
        create the meta folders required
        """
        for s in [cls.source_folder,
                  cls.experiment_folder,
                  cls.processed_folder,
                  cls.pickle_folder]:
            if os.path.exists(s) is False:
                os.makedirs(s)

    def load_allowed_values(self):
        return []

    def load_verbose_allowed_values(self):
        return list(self.allowed_values)

    def __init__(self, collection_type):

        self._source_df = None
        self._processed_df = None
        self.collection = collection_type()

        transitions = ["name",
                       "slug",
                       "description",
                       "source_file",
                       "allowed_values",
                       "verbose_allowed_values",
                       "require_columns",
                       "pickle_folder"]

        for t in transitions:
            setattr(self, t, getattr(self.__class__, t))

        if self.allowed_values == []:
            self.allowed_values = self.load_allowed_values()
        if self.verbose_allowed_values == []:
            self.verbose_allowed_values = self.load_verbose_allowed_values()

    @property
    def csv_name(self):
        return "{0}.csv".format(self.slug)

    @property
    def final_location(self):
        return self.grid_file_location()

    @property
    def final_csv_name(self):
        return "{0}_{1}_{2}.csv".format(self._register.service,
                                        self.collection.slug,
                                        self.slug)

    def get_source_df(self):
        df = pd.read_csv(self.source_file)
        return df

    def processed_file_location(self):
        return join(self.processed_folder, self.final_csv_name)

    def grid_file_location(self):
        if store_in_demographics_folder is True:
            service_folder = join("resources", "processed",
                                  self._register.service)
            if os.path.exists(service_folder) is False:
                os.makedirs(service_folder)
            return join(service_folder, self.final_csv_name)
        else:
            return join(self.experiment_folder, self.final_csv_name)

    @property
    def processed_df(self):
        if self._processed_df is None:
            self._processed_df = pd.read_csv(self.processed_file_location())
        return self._processed_df

    @processed_df.setter
    def processed_df(self, value):
        self._processed_df = value

    def process(self, optional_restriction_function=None, optional_required_columns=[], regenerate=False):
        if self.__class__.use_passthrough_cross:
            self.create_passthrough_cross()
        else:
            self.created_processed(
                optional_restriction_function, optional_required_columns, regenerate=regenerate)
            self.create_cross_table()

    def passthrough_cross(self):
        df = pd.DataFrame([])
        return df

    def create_passthrough_cross(self):
        final = self.passthrough_cross()
        allowed = self.collection.allowed_values()
        final = final[final[0].isin(allowed)]
        final = clean_zero_columns(final)
        if len(final) == 0:
            raise ValueError("Contains No Data")
        final.to_csv(self.grid_file_location(), index=False)

    def create_collection_column(self):
        result = self.collection.create_collection_column(
            self.source_df)
        if result is not None:
            self.source_df = result

    def restrict_source_df(self, df):
        """
        override if an analysis can only work on a subset of the data
        """
        return df

    def get_pickle_for_column(self, column):
        """
        retrieve column from pickle
        """
        source_file = self.source_file
        filename = os.path.splitext(os.path.basename(source_file))[0]
        filename += "_" + column + ".pickle"
        pickle_path = os.path.join(self.pickle_folder, filename)
        if os.path.exists(pickle_path):
            return pd.read_pickle(pickle_path)
        else:
            return None

    def column_to_pickle(self, column, series=None):
        """
        dump column in a pickle to retrieve later
        """
        source_file = self.source_file
        filename = os.path.splitext(os.path.basename(source_file))[0]
        filename += "_" + column + ".pickle"
        pickle_path = os.path.join(self.pickle_folder, filename)
        if series is None:
            series = self.source_df[column]
        print("saving {0} to pickle".format(column))
        series.to_pickle(pickle_path)

    def source_header(self):
        """
        get column names in source file
        """
        avaliable = pd.read_csv(self.source_file, nrows=0)
        return avaliable.columns.tolist()

    def prepare_limited_source(self, columns, core):
        """
        create a dataframe of just the columns needed, using pickles if avaliable
        """

        columns = list(set(columns + core))

        # get any already pickles
        existing = {x: self.get_pickle_for_column(x) for x in columns}
        remaining = [x[0] for x in existing.items() if x[1] is None]
        avaliable = self.source_header()

        # load columns from source csv and cache in pickles for next time
        source_from_file = [x for x in remaining if x in avaliable]
        if source_from_file:
            ndf = pd.read_csv(self.source_file, usecols=source_from_file)
            for r in source_from_file:
                existing[r] = ndf[r]
                self.column_to_pickle(r, ndf[r])

        # clean out any remaining none values, will hopefully be generated in a minute
        remaining = [x[0] for x in existing.items() if x[1] is None]
        for r in remaining:
            print("column {0} not found".format(r))
            del existing[r]

        return pd.DataFrame(existing)

    def add_columns(self, df):
        """
        override for an anaysis process to create 
        columns used in multiple subsequent steps
        """
        return df

    def created_processed(self, optional_restriction_function=None,
                          optional_required_columns=[],
                          regenerate=False):
        """
        regenerate will always regenerate analysis and collection columns
        rather than sourcing from pickle
        # note, pickle files will need to be deleted if there is a new version of a file.
        """

        # just load required columns for this operation
        # will otherwise read everything in when source_df is first called
        required_columns = optional_required_columns + \
            self.collection.require_columns + self.require_columns

        core = [self.slug, self.collection.slug]
        if required_columns:
            self.source_df = self.prepare_limited_source(
                required_columns, core)
        else:
            self.source_df = self.get_source_df()

        # allow analysis to add columns for use in subsequent steps
        self.source_df = self.add_columns(self.source_df)

        if self.collection.slug not in self.source_df.columns or regenerate:
            print("creating collection column")
            self.create_collection_column()
            self.column_to_pickle(self.collection.slug)

        if self.slug not in self.source_df.columns or regenerate:
            print("creating analysis column")
            self.create_analysis_column()
            self.column_to_pickle(self.slug)

        # apply restriction at the analysis or collection level
        # need to do it here so we are always loading and saving the full columns
        # apply optional restriction first as it tends to be the largest
        # and the usage can be cached
        if optional_restriction_function:
            self.source_df = optional_restriction_function(self.source_df)
        self.source_df = self.restrict_source_df(self.source_df)
        self.source_df = self.collection.restrict_source_df(self.source_df)

        cols = ["id", self.slug, self.collection.slug]
        if "id" not in self.source_df.columns:
            cols = [self.slug, self.collection.slug]
        pdf = self.source_df[cols]
        # uncomment to see what is being generated
        #pdf.to_csv(self.processed_file_location(), index=False)
        self._processed_df = pdf

    def reorder_columns(self, columns):
        return columns

    def transform_function(self):
        return lambda x: None

    def create_analysis_column(self):
        """
        add column
        """
        df = self.source_df
        func = self.transform_function()
        print("creating column: {0}".format(self.slug))
        df[self.slug] = df.apply(func, axis='columns')

    def create_cross_table(self):
        """
        create the cross analysis count table
        """
        banned = [np.nan]

        df = self.processed_df.copy(deep=True)
        if len(df) == 0:
            raise ValueError("Somehow have an empty processing file")

        # what are valid columns
        if self.allowed_values == []:
            self.allowed_values = df[self.slug].unique()
            self.allowed_values = [
                x for x in self.allowed_values if x not in banned and str(x) != 'nan']
            self.allowed_values.sort()

        if self.verbose_allowed_values == []:
            self.verbose_allowed_values = self.allowed_values

        # just doing counts, so create a stand in if id hasn't been loaded
        if "id" not in df.columns:
            df = df.assign(id=1)

        # force floats into ints
        if df[self.slug].dtype == "float":
            df[self.slug] = df[self.slug].fillna(0).astype(int)

        # create the pivot table
        final = pd.pivot_table(df, values="id",
                               index=[self.collection.slug],
                               columns=[self.slug],
                               aggfunc="count")

        # get column headings to their verbose version
        nice_columns = {x: y for x, y in zip(
            self.allowed_values, self.verbose_allowed_values)}
        nice_columns_str = {str(x): y for x, y in zip(
            self.allowed_values, self.verbose_allowed_values)}
        nice_columns.update(nice_columns_str)
        final = final.rename(columns={x: str(x) for x in final.columns})
        final = final.rename(columns=nice_columns)

        # removed non allowed values

        verbose_with_str = self.verbose_allowed_values
        verbose_with_str += [str(x) for x in self.verbose_allowed_values]

        bad_cols = [
            x for x in final.columns if x not in verbose_with_str]
        final = final.drop(columns=bad_cols)

        # remove zero rows
        final = final.drop(final.loc[final.sum(axis=1) == 0].index)

        # reorder columns
        col_order = self.reorder_columns(final.columns.values)
        final = final[col_order]

        # bring back values for first column
        final = final.reset_index()

        # where the values need to made human from a code
        value_lookup = self.collection.label_lookup()
        if value_lookup:
            final = final[final[self.collection.slug] != "please select"]
            new = final[self.collection.slug]
            new = new.astype(int).apply(lambda x:str(x))
            new = new.map(value_lookup)
            final[self.collection.slug] = new

        # remove any not allowed values
        allowed_row_values = list(set(self.collection.allowed_values()))
        if isinstance(allowed_row_values[0], int):
            allowed_row_values = [str(x) for x in allowed_row_values]

        final = final[final[self.collection.slug].isin(allowed_row_values)]

        final.columns = [str(x) for x in final.columns]

        # remove zero columns
        final = clean_zero_columns(final)

        if len(final) == 0:
            raise ValueError("Contains No Data")
        final.to_csv(self.grid_file_location(), index=False)


class AnalysisRegister(object):
    """
    register store to access analysis and collection class
    """
    analysis_stored = None
    collections_stored = None
    service = ""
    require_columns = []

    @classmethod
    def init_registers(cls):
        if cls.analysis_stored == None:
            cls.analysis_stored = list()
        if cls.collections_stored == None:
            cls.collections_stored = list()

    @classmethod
    def register(cls, class_to_register):

        cls.init_registers()

        if issubclass(class_to_register, CollectionType):
            relevant_register = cls.collections_stored
        if issubclass(class_to_register, AnalysisType):
            relevant_register = cls.analysis_stored
        relevant_register.append(class_to_register)

        class_to_register._register = cls

        return class_to_register

    @classmethod
    def clone(cls, parent, new_default="", exclude=[], extra=[], include=[], override_properties={}):
        """
        need to re-register when we're cloning so they have the correct
        parent service type
        """

        def passes_test(name):
            if include == [] and exclude == []:
                return True
            if include:
                return name in include
            if exclude:
                return name not in exclude

        for c in parent.collections_stored + parent.analysis_stored + extra:
            if passes_test(c.__name__):
                if hasattr(c, "default"):
                    if new_default:
                        if c.__name__ == new_default:
                            set_default = True
                        else:
                            set_default = False
                    else:
                        set_default = c.default
                else:
                    set_default = False

                class clone(c):
                    if hasattr(c, "default"):
                        default = set_default
                        if default == True:
                            display_in_header = True

                for k, v in override_properties.items():
                    if hasattr(c, k):
                        setattr(c, k, v)

                clone.__name__ == c.__name__

                cls.register(clone)

    def get_restriction_function(self):
        return lambda x: x

    @classmethod
    def run_all(cls, force=False, create_locks=False, regenerate_pickle=False):

        collections = cls.collections_stored
        analysis = cls.analysis_stored

        func = cls().get_restriction_function()
        required_cols = cls.require_columns

        total = len(collections) * len(analysis)
        count = 0
        for c in collections:
            print("collection: {0}".format(c.slug))
            for a in analysis:
                a.check_folders()
                count += 1
                if c.slug not in a.exclusions:
                    print(a.name, "{0}/{1}".format(count, total))
                    combo = a(c)
                    if os.path.exists(combo.final_location) is False or force:
                        partial_loc = combo.final_location + ".partial.txt"
                        if os.path.exists(partial_loc):
                            continue
                        elif create_locks is True:
                            QuickText().save(partial_loc)
                        a(c).process(func,
                                     required_cols,
                                     regenerate=regenerate_pickle)
                        if os.path.exists(partial_loc):
                            os.remove(partial_loc)
