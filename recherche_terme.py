import os
import re
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import streamlit as st
from concurrent.futures import ProcessPoolExecutor, as_completed

def parse_file(file):
    try:
        content = file.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text(separator=' ')
        return text
    except Exception as e:
        print(f"Erreur lors du parsing du fichier : {e}")
        return ''

def extract_pv_number(filename):
    basename = os.path.basename(filename)
    pv_number = os.path.splitext(basename)[0]
    return pv_number

def build_search_pattern(search_query):
    terms = [re.escape(term.strip()) for term in search_query.split('/')]
    pattern = r'\b(' + '|'.join(terms) + r')\b'
    return re.compile(pattern, re.IGNORECASE)

def extract_context(text, match, window=8):
    words = text.split()
    match_word = match.group(0)
    match_indices = [i for i, word in enumerate(words) if word.lower() == match_word.lower()]
    contexts = []
    for index in match_indices:
        start = max(index - window, 0)
        end = min(index + window + 1, len(words))
        context = ' '.join(words[start:end])
        contexts.append(context)
    return contexts

def analyze_file(file, filename, search_pattern):
    text = parse_file(file)
    pv_number = extract_pv_number(filename)
    matches = list(search_pattern.finditer(text))
    results = []
    term_count = len(matches)
    if matches:
        for match in matches:
            contexts = extract_context(text, match)
            for context in contexts:
                results.append({
                    'pv_number': pv_number,
                    'context': context
                })
    return pv_number, term_count, results

def analyze_files_uploaded(files, search_pattern):
    results = []
    term_frequency = {}
    for file, filename in files:
        pv_number, term_count, file_results = analyze_file(file, filename, search_pattern)
        term_frequency[pv_number] = term_count
        results.extend(file_results)
    return results, term_frequency

def plot_term_frequency(term_frequency):
    pv_numbers = sorted(term_frequency.keys())
    frequencies = [term_frequency[pv] for pv in pv_numbers]
    plt.figure(figsize=(10, 5))
    plt.plot(pv_numbers, frequencies, marker='o')
    plt.xlabel('Numéro du PV')
    plt.ylabel('Nombre d\'occurrences')
    plt.title('Fréquence des termes au fil du temps')
    plt.xticks(rotation=90)
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()

def main():
    st.title('Analyse de la Fréquence des Termes dans les PV du Conseil Constitutionnel')

    # Modification ici : utilisation de st.file_uploader
    uploaded_files = st.file_uploader(
        "Téléchargez les fichiers XML/XHTML",
        accept_multiple_files=True,
        type=['xml', 'xhtml']
    )

    search_query = st.text_input('Entrez le(s) terme(s) à rechercher (utilisez "/" pour "OU")', '')

    if st.button('Lancer l\'analyse'):
        if not uploaded_files or not search_query:
            st.error('Veuillez télécharger les fichiers et fournir les termes de recherche.')
        else:
            search_pattern = build_search_pattern(search_query)
            with st.spinner('Analyse en cours...'):
                # Préparez les fichiers pour l'analyse
                files = [(file, file.name) for file in uploaded_files]
                results, term_frequency = analyze_files_uploaded(files, search_pattern)
            if term_frequency:
                st.subheader('Graphique de fréquence des termes')
                plot_term_frequency(term_frequency)
                
                st.subheader('Occurrences trouvées')
                for result in results:
                    st.write(f"**PV {result['pv_number']}**: {result['context']}")
            else:
                st.info('Aucune occurrence trouvée.')

if __name__ == '__main__':
    main()
