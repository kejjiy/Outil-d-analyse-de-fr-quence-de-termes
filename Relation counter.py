import os
import glob
from bs4 import BeautifulSoup
from collections import Counter
import pandas as pd

def find_relations_in_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        soup = BeautifulSoup(content, 'xml')
        
        relations = []
        
        # Find all <u> elements with class "nom"
        u_elements = soup.find_all('u', class_='nom')
        
        # Iterate over the u_elements to find relations
        for i in range(len(u_elements) - 1):
            current_speaker = u_elements[i].get_text(strip=True)
            next_speaker = u_elements[i + 1].get_text(strip=True)
            # Ignore relations where a person speaks to themselves
            if current_speaker != next_speaker:
                relation = (current_speaker, next_speaker)
                relations.append(relation)
        
        return relations
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return []

def find_relations_in_directory(directory_path):
    total_relations = []
    
    for file_path in glob.glob(os.path.join(directory_path, "*.xml")):
        print(f"Processing file: {file_path}")
        file_relations = find_relations_in_file(file_path)
        total_relations.extend(file_relations)
    
    return total_relations

def count_relations(relations):
    relation_counter = Counter(relations)
    return relation_counter

def export_relations_to_excel(relation_counter, output_file_path):
    try:
        # Convert the Counter object to a DataFrame
        data = [(rel[0], rel[1], count) for rel, count in relation_counter.items()]
        df = pd.DataFrame(data, columns=['Speaker1', 'Speaker2', 'Count'])
        # Save the DataFrame to an Excel file
        df.to_excel(output_file_path, index=False)
    except Exception as e:
        print(f"Error writing to file {output_file_path}: {e}")

# Path to the directory containing XML files
directory_path = r'C:\Users\kingd\Documents\Cours\Stage\Output\XML Balisé sans noms'
# Path to the output Excel file
output_file_path = r'C:\Users\kingd\Documents\Cours\Stage\Output\relations.xlsx'

# Find relations in the directory
relations = find_relations_in_directory(directory_path)

# Count the relations
relation_counts = count_relations(relations)

# Export the relations to an Excel file
export_relations_to_excel(relation_counts, output_file_path)

print(f"Relations have been exported to {output_file_path}")
