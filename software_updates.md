# Software Updates
### 2/22/2017
- Change encoding option to "iso-8859-1" from "utf8"

### 3/1/2017
- Create an automated "attributes" array to replace the manual column_in_every_row config file.
- Fill the "answer_text" column with the right text using the mapping from value_label_map file.
- Change the header of the output file to its corresponding label from the mapping.

### 3/8/2017
- Add question_group_varname and question_group_text column, using the Q#_* pattern so that everything 
before the first _ is a group. The group question text is the longest common string of its group members' text. If the length of the common string is less than a threshold (specified in the config file), then use the group question value as the text.
- We decide that Q#a and Q# belong to two different groups.
- We also striping off line break ('\n' and '\r') and tab characters ('\t') that appear in a response string to prevent unwanted line breaks or column spans.

### 3/15/2017
- In the case of duplicate labels, the first instance will be in original label, and any other instance will have an additional indicator which contains their original value before the mapping in parentheses. 
E.g:

	V3 --> Name

	V4 --> Name

	Name --> Name

	In output file, the column header will appear as: Name (V3) ..... Name (V4) .... Name (Name)
- The full domain has been successfully obtained from the value_text mapping file, and loaded into the software. However, the count negative function has not been updated to our purpose. It has been fixed, to assume that the middle value is always in the middle (floor value) of the list.
- Rearrange the columns to comply with our software specifications.
- Add progress bar.

### 3/16/2017
- Add try-catch blocks for file reading processes.
- Disable the automatic inclusion of the ID column. User no longer needs to specify this in the config file since the ID column will be treated as an attribute.
- Add the ability to completely disregard specific columns. These will not be included in the pivoting process, and the output file at all.
- Code cleaning up.

### 3/22/2017
- Change how the script works: only require the value file, and use the responses' mapping from text_value_map file.
- Clean all data inputs for special characters: "\r", "\t", "\n"
- Add testing procedure, and get prepare to test.

### 3/29/2017
- Add warnings when no mapping value-text for a particular question is not found.
- Raise error when a response mapping is missing in a question's domain, but the response appears in the input file.
- Clean up ReadME file, and split the *software_updates.md* file into its separate file.
- Finish testing with small data.

### 4/7/2017
- Separate mapping files into 2 different files. So now the config file will require 3 input files.
- Simplify warning messages, remove duplicates, and only flush them out after the process has finished.
- Require all inputs and outputs to be xlsx files.
- Clean up config file, remove unnecessary fields.
- Allow the user to specify certain non-case-sensitive text responses in the config file that should not be included in the domain analysis/computation.

### 4/12/2017
- To-do: Come up with new names for each column
- Rerun the tests to make sure that the script is still behaving correctly after the updates on 4/7.

### 4/19/2017 - 4/26/2017
- Change the column names, and fix that only add the "Attribute" tag to the column name, not to the value/text fields in the data (when an attribute is treated as a question).
- Remove group text from questions.
- Remove the hyphen from question group text if it is the last or first character.
- Remove the ellipses from question text if it's the first character. Any non-digit or non-alphabetic should be removed as well. 