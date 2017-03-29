#! /bin/env python3

# =============================================
# GENERAL INFO
# ============================================= 
# Modified by Son D. Ngo (https://github.com/imrimt)
# Original by: Courtney Wade (https://github.com/cwade)
# In collaboration with Steve Papaccio

# =============================================
# LIBRARY IMPORTS
# ============================================= 
import pandas as pd
import numpy as np
import os
import yaml
from collections import defaultdict
from tqdm import tqdm
import sys
import argparse

# ============================================= 
# GLOBAL LITERALS
# =============================================
ERROR_TAG = "[ERROR] "
WARNING_TAG = "[WARNING] "

# =============================================
# PREPROCESSING FILE
# ============================================= 

parser = argparse.ArgumentParser()
parser.add_argument("config_file", help="Path to config yaml file with survey-specific settings " + 
    "(e.g. config.yml)")
args = parser.parse_args()

config_file = args.config_file
curr_map = {}

with open(config_file, 'r') as ymlfile:
    try:
        cfg = yaml.load(ymlfile)
        year = cfg['year']
        survey_name = cfg['survey_name']
        weight_col = cfg['weight_col']
        input_filename_v = cfg['input_filename_with_values']
        input_filename_l_v_map = cfg['input_filename_value_label_map']            
        both_attribute_and_question = cfg['both_attribute_and_question']
        columns_to_ignore = cfg['columns_to_ignore']
        exclude_from_analysis = cfg['exclude_from_analysis']
        common_string_threshold = cfg['common_string_threshold']
    except KeyError as e:
        raise KeyError("Expected variable {} in config file {} but it wasn't found".format(e, config_file))

output_file = '{}_{}_pivoted.csv'.format(year, survey_name.lower().replace(' ', '_'))


# =============================================
# FUNCTIONS DEFINITION
# ============================================= 

# get the labels (text) for columns' variables
def get_variable_labels(filename, varnames):
    # open the file here
    try:
        # 1 for second sheet of excel file
        l_v_df = pd.read_excel(filename, 1)
    except Exception as e:
        print("Reading error for \"{}\". Exiting.".format(filename))
        print("Error log: {}".format(e))
        quit()

    clean_dataframe(l_v_df)

    l_v_map = dict(zip(l_v_df["Name"], l_v_df["Label"]))
    
    label_list = []

    for name in varnames:
        if name in l_v_map:
            label_list.append(l_v_map[name])
        else:
            print((WARNING_TAG + "Missing label for value \"{}\". Use original value instead").format(name))
            label_list.append(name)
    
    return label_list

# obtain the domain for each question
def get_variable_value_domain(filename):
    try:
        # 0 for first sheet of excel file
        range_df = pd.read_excel(filename, 0)
    except Exception as e:
        print("Reading error for \"{}\". Exiting.".format(filename))
        print("Error log: {}".format(e))
        quit()

    range_df.rename(columns=dict(zip(range_df.columns, ["Question", "Value", "Label"])), inplace=True)

    clean_dataframe(range_df)

    domain_map = {}

    curr_question = ""

    for row in range_df.itertuples():
        index = row[0]

        question = row[1]

        if pd.isnull(question):
            question = curr_question
        else:
            curr_question = question

        question_value = row[2]
        if pd.isnull(question_value): 
            continue
        question_value = int(question_value)

        question_label = row[3]
        if pd.isnull(question_label):
            continue
        
        if not question in domain_map:                   
            domain_map[question] = {}

        if question_value in domain_map[question]:
            print("Duplicated labels for key {} in question {}. Please resolve the issue! Exiting...".format(question_value, question))
            quit()
        domain_map[question][question_value] = question_label

    return domain_map

# Anything above the median should get the value of 0, below of 1. If the median can be computed (
# i.e there are odd number of elements in the domain), then the median has value of 0.5.
def get_count_neg_map(domain, question):
    domain_length = len(domain)
    domain_array = list(domain.keys())
    domain_array.sort()
    map_result = {}

    if domain_length == 0:
        return map_result

    check_domain(domain_array, question)

    # below median --> 1
    for i in range(0, int(np.floor(domain_length/2))):
        map_result[str(domain_array[i])] = 1

    # above median --> 0
    for i in range(int(np.ceil(domain_length/2)), domain_length):
        map_result[str(domain_array[i])] = 0

    # if central point exists --> 0.5
    if domain_length % 2 != 0:
        map_result[str(domain_array[int(np.floor(domain_length/2))])] = 0.5

    return map_result

# Shift all values by the median. The median is computed by taking the middle value (averages for 
# even length). Then, all value is offset by the value of the median, rounding up to the nearest 
# integer (in magnitude). 
def get_normalized_by_median_map(domain, question):
    domain_length = len(domain)
    domain_array = list(domain.keys())
    domain_array.sort()
    map_result = {}

    if domain_length == 0:
        return map_result

    check_domain(domain_array, question)

    # compute median
    if domain_length % 2 != 0:
        midValue = domain_array[int(np.floor(domain_length/2))]
    else:
        midValue = float(domain_array[int(domain_length/2) - 1] + domain_array[int(domain_length/2)]) / 2.0

    for i in range(0, domain_length):
        if (domain_array[i] < midValue):
            map_result[str(domain_array[i])] = str(int(np.floor(domain_array[i] - midValue)))
        elif (domain_array[i] > midValue):
            map_result[str(domain_array[i])] = str(int(np.ceil(domain_array[i] - midValue)))
        else:
            map_result[str(domain_array[i])] = 0

    return map_result

def check_domain(domain_array, question):
    prev = domain_array[0]
    for item in domain_array[1:]:
        if (item <= 0):
            print((WARNING_TAG + "There is a non-positive value in the domain of question {}").format(question))
            return
        if (item != prev + 1):
            print((WARNING_TAG + "There is discontinuity in the domain of question {}").format(question))
            return
        prev = item

# update group_text according to their group name using the group map
def update_group_text(group_name):
    return group_map[group_name]

# find the largest common string from the beginninng of sa and sb
def common_start(sa, sb):
    def _iter():
        for a, b in zip(sa, sb):
            if a == b:
                yield a
            else:
                return

    return ''.join(_iter())

# create a labels series that has a corresponding label to
# every value in vals. If there is no mapping, then keep 
# vals as original
def map_value_to_label(vals, column_name):
    labels = []
    if column_name in domain_map:
        curr_map = domain_map[column_name]
        curr_list = list(curr_map.keys())
        
        if not curr_map:
            return labels
        else:            
            for item in vals:
                if not item.isdigit() or pd.isnull(item):
                    labels.append(item)
                else:
                    item = int(item)
                    if item not in curr_map:                    
                        print((ERROR_TAG + "Do not find a mapping for the current value {} of column {}. Use original value instead. "
                            + "Please recheck your mapping file").format(item, column_name))
                        quit()
                        # labels.append(item)                     
                    else:
                        labels.append(curr_map[item])
    return labels

# clean the dataframe for \n, \r and \t characters
# Note: for some reason, we have to use str.replace here instead 
# of the df.replace function, as it doesn't replace the special 
# characters
def clean_dataframe(df):
    for v in df.select_dtypes([np.object]).columns[1:]:
        df[v] = df[v].astype(str)
        df[v] = (df[v]).str.replace('\r', ', ')
        df[v] = (df[v]).str.replace('\t', ', ')
        df[v] = (df[v]).str.replace('\n', ', ')

# =============================================
# MAIN PROCESS
# ============================================= 

try:
    value_df = pd.read_csv(input_filename_v, low_memory=False, encoding="iso-8859-1")
except Exception as e:
    print((ERROR_TAG + "Reading error for \"{}\". Exiting.").format(input_filename_v))
    print("Error log: {}".format(e))
    quit()

# obtain all the values of the columns
varnames = [x for x in value_df.columns if x not in columns_to_ignore]

# obtain all the labels of the columns
varlabels = get_variable_labels(input_filename_l_v_map, varnames)

# create a dictionary that map varnames to varlabels
varmap = dict(zip(varnames, varlabels))

# obtain domain map for each question, if applicable
domain_map = get_variable_value_domain(input_filename_l_v_map)

# transposed the needed columns, basically pivotting right here
new_df_cols = [value_df[col] for col in varnames]
df = pd.DataFrame(new_df_cols).T

# create the attributes list here. We also want to rename the attribute  column from their values 
# to their labels (texts) in the output file. The renamed columns' name will be stored in 
# attributes. We store the original name of the first occurence of any new name in
# attribute_rename_backward.
attributes = []
dont_pivot = []
attributes_rename = {}
attributes_rename_backward = {}

for name in tqdm(varnames, desc="Renaming Columns"):
    if not name.startswith("Q"):        
        if name in varmap:
            rename = varmap[name]

            # if there is a duplicate in the label of a name
            if rename in attributes_rename_backward:

                # then add an extension that indicates its original name to the new name
                newname = "{} ({})".format(rename, name)

                # update the first occurrence of the new name. If this process has 
                # already happened, then first_occ_name should return an empty string
                # so we only do the process once
                first_occ_name = attributes_rename_backward[rename]
                if first_occ_name:
                    index = attributes.index(rename)
                    first_occ_rename = "{} ({})".format(rename, first_occ_name)
                    attributes[index] = first_occ_rename                    
                    attributes_rename[first_occ_name] = first_occ_rename

                    # change the original name that corresponds to the first occurence of new name
                    # to empty string to indicate that we shouldn't do this updating process more 
                    # than one                    
                    attributes_rename_backward[rename] = ""

                rename = newname

            else:
                # save the original name that corresponds to the first occurence of new name. 
                # This value will be changed to empty string if we ever encounter this new 
                # name again.
                attributes_rename_backward[rename] = name
            
            attributes.append(rename)
            attributes_rename[name] = rename

        # we do not pivot the attribute columns
        # unless we want certain columns to be pivoted as well
        if not name in both_attribute_and_question:
            dont_pivot.append(name)

# rename the columns that are used as attributes
df.rename(columns=attributes_rename, inplace=True)
df_cols = df.columns

# If weight column specified above doesn't exist, 
# create it and set all weights to 1
if weight_col not in df_cols:
    df[weight_col] = 1

clean_dataframe(df)

# identify the necessary columns to keep as column as well. If the columns
# have numerical/categorical data, it will be suffixed with "_l"
attribute_col = []
for v in tqdm(attributes, desc="Adding attributes"):
    if v not in df.columns:
        print((WARNING_TAG + "Merged data file is missing column {}, and no replacement was found").format(v))
    else:
        attribute_col.append(v)

# construct the new data frame with the right format        
dataframes = []
group_map = {}

# print(attribute_col)

for v in tqdm(varnames, desc="Pivoting"):
    if v not in dont_pivot:

        # order of columns
        pivoted = pd.DataFrame(columns = ['survey_name', 'year'] + attribute_col +
                               ['question_group_varname', 'question_group_text', 'question_varname', 
                               'question_text', 'answer_value', 'answer_text', 
                               'count_negative', 'normalized_by_median', 'weight'])


        # change v to be the renamed value if v is a pivoted attribute
        if v in both_attribute_and_question:
            v = attributes_rename[v]

        vals = df[v]

        temp_list = map_value_to_label(vals, v)
        labels = vals if not temp_list else pd.Series(temp_list)

        pivoted['answer_value'] = vals
        pivoted['answer_text'] = labels

        # Figure out which indices to exclude from analysis. NOT SURE WHAT THIS IS DOING?
        if len(labels.dropna()) > 0:
            exclude = pd.Series(False, index=np.arange(0, len(labels)))
            exclude[(labels.notnull()) & (labels.dropna().astype(str).str.lower().isin(exclude_from_analysis))] = True

        # Now figure out domain excluding 'exclude from analysis' answers using the domain_map built 
        # earlier
        # domain = list(pd.unique(vals[(labels.notnull()) & (~labels.isin(exclude_from_analysis))].dropna().values))
        if v in domain_map:                
            domain = domain_map[v]
        else:
            domain = {}
        # domain.sort()
        negative_map = get_count_neg_map(domain, v)
        normalize_map = get_normalized_by_median_map(domain, v)
        
        pivoted.count_negative = 0
        pivoted.normalized_by_median = 0

        if len(negative_map) > 0:
            pivoted['count_negative'] = vals.replace(negative_map)

        if len(normalize_map) > 0:
            pivoted['normalized_by_median'] = vals.replace(normalize_map)

        pivoted['survey_name'] = survey_name
        pivoted['year'] = year
        # pivoted['id'] = df[id_col]

        question_text = v if v in attributes else varmap[v]

        # create group if there is a '_'
        if '_' in v:
            group_name_var = v[:v.find('_')]
        else:
            group_name_var = v

        # if there is no mapping in group_map, implying that this is the first 
        # occurrence of group_name
        if group_name_var not in group_map:
            group_map[group_name_var] = question_text
            group_name_text = question_text

        # there is a mapping, so update the mapped value string by finding
        # the most common string with the current value. If the common string 
        # is less than threshold number of characters, then use group_name_var
        # as the text
        else:
            common_string = common_start(question_text, group_map[group_name_var])
            if (len(common_string) >= common_string_threshold):
                group_name_text = common_string
            else:
                group_name_text = group_name_var

            group_map[group_name_var] = group_name_text

        pivoted['question_varname'] = v
        pivoted['question_text'] = question_text
        pivoted['question_group_varname'] = group_name_var
        pivoted['question_group_text'] = group_name_text
        pivoted['weight'] = df[[weight_col]]
        pivoted[attribute_col] = df[attribute_col]
        dataframes.append(pivoted)

# parse through the data frame one more time to update group_text
for row in dataframes:
    row['question_group_text'] = row['question_group_varname'].apply(update_group_text)

# =============================================
# FINAL PRODUCT
# ============================================= 
final_product = pd.concat(dataframes)
final_product = final_product[final_product['answer_value'].notnull()]
final_product = final_product[final_product['answer_value'].str.strip() != '']
final_product = final_product.sort_values(['year', 'survey_name', 'question_varname'])
final_product.to_csv(output_file, index=False)
print('Reshaped output file was successfully written to {}'.format(output_file))