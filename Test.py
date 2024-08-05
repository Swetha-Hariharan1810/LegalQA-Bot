
import pandas as pd

# Load the uploaded CSV file
file_path = '/mnt/data/test.csv'
df = pd.read_csv(file_path)

# Initialize the 'new_block' column to False
df['new_block'] = False

# Variables to track the state
in_table_block = False

# Iterate through the DataFrame to set the 'new_block' flag
for index, row in df.iterrows():
    blocktype = row['block_type'].lower()
    
    if 'header' in blocktype:
        # Mark new block on 'HEADER'
        df.at[index, 'new_block'] = True
        in_table_block = False
    elif 'table' in blocktype:
        if not in_table_block:
            # Mark new block on first occurrence of 'table' after non-table
            df.at[index, 'new_block'] = True
            in_table_block = True
    else:
        # Mark new block on any block type after a table block
        df.at[index, 'new_block'] = True
        in_table_block = False

# Calculate the block number using the cumulative sum of the 'new_block' flag
df['block_num'] = df['new_block'].cumsum() + 1

# Drop the 'new_block' helper column
df.drop(columns=['new_block'], inplace=True)

# Save the updated DataFrame to a new CSV file
output_path = '/mnt/data/output.csv'
df.to_csv(output_path, index=False)

output_path
