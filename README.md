# Information
This script is adapted and modified by Son Ngo'17 as part of a project with Bowdoin College, Institutional Research, Analytics & Consulting Office. The collaborator of this project is Steve Papaccio. The original author of this script is Courtney Wade and the GitHub page can be accessed [here](https://github.com/cwade/survey_pivoter).

Bowdoin conducts surveys using Qualtrics, an online survey tool, and performs analysis on the results. Typical survey data files are provided by Qualtrics in a one row per survey respondent format. This format can make it difficult to perform certain types of analysis, particularly when using analysis and data visualization tools such as Tableau. There is a need to be able to easily “pivot” this data into a one row per question per response format that would be easier to analyze.

# Overview

*(SPSS file is no longer supported in this script)*

SurveyPivoter is a fairly simple Python 3 script that takes in a survey data file with one row per survey response and outputs a new file that's one row per question response. It's for taking files that come out of Qualtrics (or other survey software) and transforming them for use in Tableau, using [Steve Wexler's recommended methods of survey data visualization](http://www.datarevelations.com/visualizing-survey-data).

It requires installation of the following python libraries (using pip install [library name] or your preferred method):
- pandas
- PyYAML
- tqdm (for progress bar)
 
To run the script from the directory where it's located:

```
python3 survey_pivoter.py [path/to/config_file]
```

The sample config file included here, config.yml, contains a lot of documentation about all the survers' parameters that need to be specified for the script to work. Survey files will either come from Qualtrics directly or from COFHE.  In either case, they will adhere to a similar format.  There will be three sources of data to work with

| Data Source                     | Description                                                                                                                                                                                                                                                                                                                                                                                                                  |
|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Responses as values             | A spreadsheet containing one row per student and one column per question. Responses to the questions are recorded as values (e.g. “5”).                                                                                                                                                                                                                                                                                      |
| Question names & labels         | A spreadsheet containing one row per question, with a column titled “Name” containing the question number (e.g. Q1, Q2, etc.) and a column titled “Label” containing the question text (e.g. “How satisfied were you with ...”). This spreadsheet may have other columns. Note: This spreadsheet is likely found in the same file as the “Response sets for each question” spreadsheet (second sheet) but may not always be. |
| Response sets for each question | A spreadsheet containing the set of possible responses to each question. Note: This spreadsheet is likely found in the same file as the “Question names & labels” spreadsheet (first sheet) but may not always be.                                                                                                                                                                                                           |

Sample data files are also included. These csv files can be created by taking an SPSS file and saving it as a csv file, unchecked 'Save value labels where defined instead of data files'. They can also be created by taking any Qualtrics survey, and downloading the csv with 'Use numeric values' selected. *Note that if you're using Qualtrics csv files, you'll have to delete one of the two header rows in each of your csv files before running the script.*

## Output Specifications

The order of columns in the output file should be sorted as follows:
 1. Attribute columns
 2. Question group columns (value and text)
 3. Question columns (value and text)
 4. Response columns (value and text)
 5. Count_negative and normalized_by_median and weight columns

The attribute columns refer to any non-question column in the input file, and those will not be pivoted unless specified as questions as well by the user in the config file. The name of these columns will be converted into their actual text if possible in the output file.

The question group columns identify questions of the form Q#_* as member of group Q#. However, Q#a and Q# will be treated as two different groups. The question group text will be determined by the longest common string of its members' question texts.

The question columns store the value and text of each question. If there is no corresponding text for any question, the value will serve as the text. This is true for the question group text as well.

The response columns store the value and text of each response. If there is no corresponding text for any response, the value will serve as the text. This is true for the question group text as well. An error will also occur if a value is mapped to two different texts.

The script computes a variable called 'count_negative' which is used in Steve Wexler's diverging stacked bar charts. The script assumes that the top half of responses on the numeric scale are positive and the bottom half are negative. If there's an odd number of possible answers, the middle value is counted as half negative and half positive (0.5). 

The script also computes a variable called “normalized_by_median”. The values for this variable should be based on the range of responses for each question, with the value being offset by the value of the median. The median can be computed as the middle value of the range. If there are an even number of response types, take the average of the two middle values of the range. Then, the offset is rounded up to the nearest integer by magnitude. For example, (-0.5) is rounded to (-1), and (0.5) is rounded to (1).

This script is still under development and contributions are welcome!