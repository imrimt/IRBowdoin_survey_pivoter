#! /bin/env python3

import pandas as pd
import numpy as np
import os
import yaml
from collections import defaultdict
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("config_file", help="Path to config yaml file with survey-specific settings (e.g. config.yml)")
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
                "Configuration variable 'spss' must be set either to True or False (boolean var, not a string) in config file. Actual value is {}".format(spss)
            )
        both_attribute_and_question = cfg['both_attribute_and_question']
        dont_pivot = cfg['dont_pivot']
        exclude_from_analysis = cfg['exclude_from_analysis']
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

# create the attributes list here
attributes = []
attributes_rename = {}
attributes_rename_backward = {}
for name in varnames:
    if not name.startswith("Q"):
        # print(name)
        if name in varmap:
            rename = varmap[name]

            if rename in attributes_rename_backward:
                newname = "{} ({})".format(rename, name)
                rename = newname
            else:
                attributes_rename_backward[rename] = name
                # attribute contains the transformed name
                
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

print(attributes)

df.rename(columns=attributes_rename, inplace=True)
df_cols = df.columns

# If weight column specified above doesn't exist, 
# create it and set all weights to 1
if weight_col not in df_cols:
    df[weight_col] = 1

# What is this one for?
def get_count_neg_map(domain):
    l = len(domain)
    m = defaultdict(lambda: 0)
    for i in range(0, int(np.floor(l/2))):
        m[domain[i]] = 1
    for i in range(int(np.ceil(l/2)), l):
        m[domain[i]] = 0
    if l % 2 != 0:
        m[domain[int(np.floor(l/2))]] = .5
    return(m)

# identify the necessary columns to keep as column as well. If the columns
# have numerical/categorical data, it will suffixed with "_l"
every_row = []
# for v in include_in_every_row:
for v in attributes:
    if v not in df.columns:
        if v + '_l' in df.columns:
            every_row.append(v + '_l')
            print('Merged data file is missing column {0}, using {0}_l instead'.format(v))
        else:
            print('Merged data file is missing column {}, and no replacement was found'.format(v))
    else:
        every_row.append(v)

# construct the new data frame with the right format        
dataframes = []
for v in varnames:
    if v not in dont_pivot:

        # built-in required columns for every row
        pivoted = pd.DataFrame(columns = [
                               'survey_name', 'year', 'id', 'question_varname',
                               'question_text', 'answer_text', 'answer_value', 
                               'weight', 'count_negative'] + every_row)

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

        # Now figure out domain excluding 'exclude from analysis' answers. NOT SURE WHAT THIS IS DOING?        
        domain = list(pd.unique(vals[(labels.notnull()) & (~labels.isin(exclude_from_analysis))].dropna().values))
        domain.sort()
        m = get_count_neg_map(domain)
        pivoted.count_negative = 0
        if len(m) > 0:
            pivoted['count_negative'] = vals.replace(m)

        pivoted['survey_name'] = survey_name
        pivoted['year'] = year
        pivoted['id'] = df[id_col]
        pivoted['question_varname'] = v
        pivoted['question_text'] = v if v in attributes else varmap[v]
        pivoted['weight'] = df[[weight_col]]
        pivoted[every_row] = df[every_row]
        dataframes.append(pivoted)
        
final_product = pd.concat(dataframes)
final_product = final_product[final_product['answer_value'].notnull()]
final_product = final_product[final_product['answer_value'].str.strip() != '']
final_product = final_product.sort_values(['year', 'survey_name', 'question_varname', 'id'])
final_product.to_csv(output_file, index=False)
print('Reshaped output file was successfully written to {}'.format(output_file))