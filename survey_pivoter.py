#! /bin/env python3

import pandas as pd
import numpy as np
import os
import yaml
from collections import defaultdict
from tqdm import tqdm
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("config_file", help="Path to config yaml file with survey-specific settings " + 
    "(e.g. config.yml)")
args = parser.parse_args()

config_file = args.config_file

with open(config_file, 'r') as ymlfile:
    try:
        cfg = yaml.load(ymlfile)
        year = cfg['year']
        survey_name = cfg['survey_name']
        id_col = cfg['id_column']
        
        spss = cfg['spss']
        spss = bool(spss)
        weight_col = cfg['weight_col']
        if spss == False:
            input_filename_l = cfg['input_filename_with_labels']
            input_filename_v = cfg['input_filename_with_values']
            input_filename_l_v_map = cfg['input_filename_value_label_map']
        elif spss == True:
            input_filename = cfg['input_filename']
        else:
            raise Exception(
                "Configuration variable 'spss' must be set either to True or False (boolean var, " + 
                "not a string) in config file. Actual value is {}".format(spss)
            )
        both_attribute_and_question = cfg['both_attribute_and_question']
        dont_pivot = cfg['dont_pivot']
        exclude_from_analysis = cfg['exclude_from_analysis']
        COMMON_STRING_THRESHOLD = cfg['common_string_threshold']
    except KeyError as e:
        raise KeyError("Expected variable {} in config file {} but it wasn't found".format(e, config_file))

if spss:
    from rpy2.robjects import pandas2ri, r

output_file = '{}_{}_pivoted.csv'.format(year, survey_name.lower().replace(' ', '_'))

# applies to spss file only
def get_df(filename, val_labels):
    # This is a really weird workaround used because the pandas2ri method was changing the
    # data that came back to code N/As incorrectly when value labels were on. So now R 
    # writes csvs and pandas reads them
    tmpfile = 'tmp_spss_reader.csv'
    r_commands = """ 
    df = suppressWarnings(foreign::read.spss("{}", to.data.frame = TRUE, use.value.labels = {}))
    write.csv(df, file='{}', row.names=FALSE)
    """.format(filename, str(val_labels).upper(), tmpfile)
    r(r_commands)
    d = pd.read_csv(tmpfile, low_memory=False)
    os.remove(tmpfile)
    return(d)

# get the labels (text) for variables
def get_variable_labels(filename, varnames):
    if (spss == True):
        w = r('as.data.frame(attributes(foreign::read.spss("{}"))["variable.labels"])[,1]'.format(filename))
        cat = pandas2ri.ri2py(w)
        return(list(cat))
    else:
        # open the file here
        # index 1 for the second sheet        
        # l_v_map = pd.read_excel(filename, 1, parse_cols="Name, Label", encoding="iso-8859-1")

        l_v_df = pd.read_excel(filename, 1)
        l_v_map = dict(zip(l_v_df["Name"], l_v_df["Label"]))
        
        label_list = []

        for name in varnames:
            if name in l_v_map:
                label_list.append(l_v_map[name])
            else:
                label_list.append(name)
        
        return label_list

# obtain the domain for each question
def get_variable_value_domain(filename):
    if (spss == True):
        # do something with spss
        print("SPSS file")
    else:
        range_df = pd.read_excel(filename, 0)    
        range_df.rename(columns=dict(zip(range_df.columns, ["Question", "Value", "Label"])), inplace=True)

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
            # if pd.isnull(quesetion_label):
            #     continue

            tup = (question_value, question_label)
            if not question in domain_map:                   
                domain_map[question] = []
            domain_map[question].append(tup)

    return domain_map

# This doesn't seem to be working as it's supposed to. Are we treating the median value as 0, and 
# just shift the rest according to the median value? Need to fix this. Right now, everything below 
# is given 1, and everything above is given 0. If there is no domain, just simply return 0.
def get_count_neg_map(domain):
    l = len(domain)
    m = {}
    if l == 0:
        return m

    midValue = domain[int(np.floor(l/2))]
    # for i in range(0, int(np.floor(l/2))):
    #     m[domain[i]] = 1
    # for i in range(int(np.ceil(l/2)), l):
    #     m[domain[i]] = 0
    # if l % 2 != 0:
    #     m[domain[int(np.floor(l/2))]] = 0.5

    for i in range(0, l):
        m[str(domain[i])] = str(domain[i] - midValue);

    # for i in range(0, int(np.floor(l/2))):
    #     m[domain[i]] = 1
    # for i in range(int(np.ceil(l/2)), l):
    #     m[domain[i]] = 0
    # if l % 2 != 0:
    #     m[domain[int(np.floor(l/2))]] = 0.5

    return m

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
    
if spss == True:
    df1 = get_df(input_filename, True)
    df2 = get_df(input_filename, False)
else:
    df1 = pd.read_csv(input_filename_l, low_memory=False, encoding="iso-8859-1")
    df2 = pd.read_csv(input_filename_v, low_memory=False, encoding="iso-8859-1")

if df1.shape != df2.shape:
    print("Shape of labels data is {} and shape of values data is {}".format(df1.shape, df2.shape))
    raise

varnames = df1.columns

if spss == True:
    varlabels = get_variable_labels(input_filename, [])
else:
    # will eventually need to replace this with the actual text of the question
    varlabels = get_variable_labels(input_filename_l_v_map, varnames)

#df1: label data
#df2: value data
#df3: merge, add two columns next to each other

varmap = dict(zip(varnames, varlabels))
domain_map = get_variable_value_domain(input_filename_l_v_map)
df3 = df1.merge(df2, left_index=True, right_index=True, suffixes=('_l', '_v'))

new_df_cols = []

for col in varnames:
    lab = '{}_l'.format(col)
    val = '{}_v'.format(col)

    # if there is no mapping, i.e no category
    # combine the two columns into one
    if df3[lab].equals(df3[val]):
        a = df3[lab]
        a.name = col
        new_df_cols.append(a)

    # if there is a mapping, numerical values
    else:
        new_df_cols.append(df3[lab])
        new_df_cols.append(df3[val])

# transposed the needed columns, basically pivotting right here
df = pd.DataFrame(new_df_cols).T

# create the attributes list here. We also want to rename the attribute  column from their values 
# to their labels (texts) in the output file. The renamed columns' name will be stored in 
# attributes. We store the original name of the first occurence of any new name in
# attribute_rename_backward.
attributes = []
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

                    first_occ_name_l = name + '_l'
                    if (name_l in df.columns):
                        first_occ_rename_l = first_occ_rename + '_l'
                        attributes_rename[first_occ_name_l] = first_occ_rename_l

                rename = newname

            else:
                # save the original name that corresponds to the first occurence of new name. 
                # This value will be changed to empty string if we ever encounter this new 
                # name again.
                attributes_rename_backward[rename] = name
            
            attributes.append(rename)
            attributes_rename[name] = rename

            name_l = name + '_l'
            if (name_l in df.columns):
                rename_l = rename + '_l'
                attributes_rename[name_l] = rename_l

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

# clean the dataframe for \n, \r and \t characters
# Note: for some reason, we have to use str.replace here instead 
# of the df.replace function, as it doesn't replace the special 
# characters
for v in df.select_dtypes([np.object]).columns[1:]:
    df[v] = df[v].astype(str)
    df[v] = (df[v]).str.replace('\r', ', ')
    df[v] = (df[v]).str.replace('\t', ', ')

# identify the necessary columns to keep as column as well. If the columns
# have numerical/categorical data, it will suffixed with "_l"
attribute_col = []
for v in tqdm(attributes, desc="Adding attributes"):
    if v not in df.columns:
        if v + '_l' in df.columns:
            attribute_col.append(v + '_l')
            print('Merged data file is missing column {0}, using {0}_l instead'.format(v))
        else:
            print('Merged data file is missing column {}, and no replacement was found'.format(v))
    else:
        attribute_col.append(v)

# construct the new data frame with the right format        
dataframes = []
group_map = {}
for v in tqdm(varnames, desc="Pivoting"):
    if v not in dont_pivot:

        # order of columns
        pivoted = pd.DataFrame(columns = ['survey_name', 'year', 'id'] + attribute_col +
                               ['question_group_varname', 'question_group_text', 'question_varname', 'question_text',  
                               'answer_text', 'answer_value', 'weight', 'count_negative'])

        # change v to be the renamed value if v is a pivoted attribute
        if v in both_attribute_and_question:
            v = attributes_rename[v]

        # add question columns, with both texts and question id
        if '{}_l'.format(v) in df_cols and v not in attributes:
            labels = df['{}_l'.format(v)]
            vals = df['{}_v'.format(v)]

        # this is the part where a value that doesn't have a corresponding 
        # variable should be kept as it is 
        else:
            # create a range value from 0 to the length of data frame? Not 
            # exactly sure but it seems like it
            # labels = pd.Series(np.nan, index=np.arange(0, len(df)))            

            # keep it as it is 
            labels = df[v]
            vals = df[v]

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
            # we only want the numerical value (i.e the first element in the tuple item)
            domain = [item[0] for item in domain_map[v]]
        else:
            domain = []
        domain.sort()
        m = get_count_neg_map(domain)
        print(m)
        pivoted.count_negative = 0
        if len(m) > 0:
            pivoted['count_negative'] = vals.replace(m)

        pivoted['survey_name'] = survey_name
        pivoted['year'] = year
        pivoted['id'] = df[id_col]

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
            if (len(common_string) >= COMMON_STRING_THRESHOLD):
                group_name_text = common_string
            else:
                group_name_text = group_name_var

            group_map[group_name_var] = group_name_text

        pivoted['question_varname'] = v
        pivoted['question_text'] = v if v in attributes else varmap[v]
        pivoted['question_group_varname'] = group_name_var
        pivoted['question_group_text'] = group_name_text
        pivoted['weight'] = df[[weight_col]]
        pivoted[attribute_col] = df[attribute_col]
        dataframes.append(pivoted)

# parse through the data frame one more time to update group_text
for row in dataframes:
    row['question_group_text'] = row['question_group_varname'].apply(update_group_text)

#============== FINAL PRODUCT ==============#
final_product = pd.concat(dataframes)
final_product = final_product[final_product['answer_value'].notnull()]
final_product = final_product[final_product['answer_value'].str.strip() != '']
final_product = final_product.sort_values(['year', 'survey_name', 'question_varname', 'id'])
final_product.to_csv(output_file, index=False)
print('Reshaped output file was successfully written to {}'.format(output_file))