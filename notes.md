1) Not sure what the "count_negative" functionality is for.

2) Doesn't run on the original sample file from Steve, but runs normally on the abridge file with 10 responses. Potential error might be: 
*UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8e in position 9: invalid start byte*
**Fixed**: Changing "encoding" option to "iso-8859-1"

## The workflow of the script

1. Parse the config file

2. Read both files (text & value) 

3. Merge the two files, adding suffix "_l" and "_v" to each column

	- Create a mapping of the column variables to column names (to be modified)
	- Combine the columns that do not have numerical values

4. Create a data frame using the newly formed columns, then transpose to have the pivoted form.

5. Identify which columns to keep.

6. Go through each column that should be pivoted, and add to the result.

7. Clean for NA data, and white spaces, then write result to file.
