# Extracting relevant information for the new CSV structure
data_entries = []

# Loop through the main sections and elements to extract required fields
for section in data.get('sections', []):
    for element in section.get('elements', []):
        element_data = data.get(element, {})
        role = element_data.get('role', '')
        for span in element_data.get('spans', []):
            for region in element_data.get('boundingRegions', []):
                data_entries.append({
                    'word': element_data.get('content', ''),
                    'polygon': region.get('polygon', []),
                    'pagenum': region.get('pageNumber', ''),
                    'element': element,
                    'role': role
                })

# Convert the data into a DataFrame
df = pd.DataFrame(data_entries)

# Define the CSV file path
csv_file_path = '/mnt/data/sample_output_with_fields.csv'

# Save the DataFrame to a CSV file
df.to_csv(csv_file_path, index=False)

csv_file_path
