import json
import csv

# Load JSON data from file
with open('/mnt/data/sample.json', 'r') as file:
    data = json.load(file)

# CSV file output path
csv_file_path = '/mnt/data/output.csv'

# Function to group words into elements based on their spans
def group_words_into_elements(words):
    elements = []
    current_element = []
    previous_end = None

    for word_data in words:
        start_offset = word_data['span']['offset']
        end_offset = start_offset + word_data['span']['length']

        if previous_end is not None and start_offset > previous_end + 1:
            # New element if there is a gap between words
            elements.append(current_element)
            current_element = []

        current_element.append(word_data)
        previous_end = end_offset

    # Add the last element
    if current_element:
        elements.append(current_element)
    
    return elements

# Function to assign roles based on element content (simplified logic)
def assign_role_to_element(element_words):
    first_word = element_words[0]['content'].lower()
    if "coverage" in first_word:
        return "Heading"
    elif "cigna" in first_word:
        return "Footer"
    else:
        return "Body"

# Prepare CSV file
with open(csv_file_path, mode='w', newline='') as csv_file:
    writer = csv.writer(csv_file)
    # Write CSV header
    writer.writerow(['word', 'polygon', 'pagenum', 'element', 'role'])

    # Loop through each page
    for page in data['pages']:
        page_number = page['pageNumber']
        words = page['words']
        
        # Group words into elements
        elements = group_words_into_elements(words)

        # Write each word with its element and assigned role
        for element_index, element_words in enumerate(elements):
            role = assign_role_to_element(element_words)
            for word_data in element_words:
                word = word_data['content']
                polygon = word_data['polygon']
                writer.writerow([word, polygon, page_number, element_index, role])

print(f"CSV file created successfully at {csv_file_path}")
