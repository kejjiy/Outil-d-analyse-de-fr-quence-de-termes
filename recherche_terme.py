import os
import re
import datetime
import pandas as pd
import unicodedata
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import streamlit as st
# from wordcloud import WordCloud  # Commenté en raison de problèmes potentiels d'installation
import plotly.express as px
from collections import defaultdict

def normalize_text(text):
    return unicodedata.normalize('NFC', text)

def parse_file(file):
    try:
        content = file.read().decode('utf-8', errors='ignore')
        content = normalize_text(content)
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text(separator=' ')
        text = normalize_text(text)
        return text
    except Exception as e:
        print(f"Erreur lors du parsing du fichier : {e}")
        return ''

def extract_pv_number(filename):
    basename = os.path.basename(filename)
    pv_number = os.path.splitext(basename)[0]
    # Retirer les préfixes 'PV' et les suffixes de version '_vX.X'
    pv_number = re.sub(r'(_v\d+\.\d+)', '', pv_number)
    pv_number = pv_number.replace('PV', '')
    pv_number = pv_number.strip()
    if not pv_number:
        pv_number = basename  # Utiliser le nom de fichier complet si pv_number est vide
    return pv_number

def extract_date_from_pv(filename):
    basename = os.path.basename(filename)
    pv_number = os.path.splitext(basename)[0]
    # Retirer les préfixes 'PV' et les suffixes de version '_vX.X'
    pv_number = re.sub(r'(_v\d+\.\d+)', '', pv_number)
    pv_number = pv_number.replace('PV', '')
    # Extraire les dates
    date_pattern = re.compile(r'(\d{4})-(\d{2})-([\d\-]+)')
    matches = date_pattern.findall(pv_number)
    dates = []
    for match in matches:
        year, month, days_str = match
        days = re.findall(r'\d+', days_str)
        for day in days:
            if len(day) == 0:
                continue
            date_str = f"{year}-{month}-{day.zfill(2)}"
            try:
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(date)
            except ValueError:
                pass
    if dates:
        earliest_date = min(dates)
        return earliest_date
    else:
        return None

def build_search_pattern(search_query):
    # Diviser la requête sur '/' pour gérer l'opérateur 'OU'
    terms = [term.strip() for term in search_query.split('/')]
    # Échapper les caractères spéciaux regex dans chaque terme
    terms = [re.escape(term) for term in terms]
    # Créer un motif qui correspond à chaque phrase
    pattern = '(' + '|'.join(terms) + ')'
    return re.compile(pattern, re.IGNORECASE)

def extract_context(text, match, window=40):
    # window est le nombre de caractères avant et après la correspondance
    start_idx = max(match.start() - window, 0)
    end_idx = min(match.end() + window, len(text))
    context = text[start_idx:end_idx]
    return context.strip()

def analyze_file(file, filename, search_pattern):
    text = parse_file(file)
    pv_number = extract_pv_number(filename)
    date = extract_date_from_pv(filename)
    matches = list(search_pattern.finditer(text))
    results = []
    term_count = len(matches)
    if matches:
        for match in matches:
            context = extract_context(text, match)
            results.append({
                'pv_number': pv_number,
                'date': date.strftime('%d/%m/%Y') if date else 'Non daté',
                'context': context
            })
    return pv_number, date, term_count, results

def analyze_files_uploaded(files, search_pattern, start_date, end_date):
    results = []
    term_frequency = defaultdict(int)
    for file, filename in files:
        date = extract_date_from_pv(filename)
        pv_number = extract_pv_number(filename)

        # Décider si le fichier doit être inclus en fonction de la date
        if date is not None:
            if not (start_date <= date.date() <= end_date):
                continue  # Ignorer les fichiers en dehors de la plage de dates
            key = date.strftime('%Y')  # Utiliser l'année comme clé
        else:
            # Inclure les fichiers sans date et utiliser le nom de fichier comme clé
            key = pv_number

        pv_number, date, term_count, file_results = analyze_file(file, filename, search_pattern)
        term_frequency[key] += term_count  # Utiliser la clé appropriée
        results.extend(file_results)
    return results, term_frequency

def plot_term_frequency_interactive(term_frequency):
    # Séparer les clés qui sont des années et celles qui sont des noms de fichiers
    year_keys = []
    file_keys = []
    for key in term_frequency.keys():
        if key.isdigit():
            year_keys.append(key)
        else:
            file_keys.append(key)
    # Trier les années numériquement
    year_keys = sorted(year_keys)
    # Trier les noms de fichiers alphabétiquement
    file_keys = sorted(file_keys)
    # Combiner les clés
    all_keys = year_keys + file_keys
    frequencies = [term_frequency[key] for key in all_keys]
    fig = px.bar(
        x=all_keys,
        y=frequencies,
        labels={'x': 'Année/Fichier', 'y': 'Nombre d\'occurrences'},
        title='Fréquence des termes par année ou par fichier'
    )
    fig.update_layout(xaxis_tickangle=90)
    st.plotly_chart(fig)

def display_paginated_results(results, items_per_page=10):
    total_results = len(results)
    if total_results == 0:
        st.write("Aucune occurrence trouvée.")
        return
    total_pages = (total_results - 1) // items_per_page + 1
    # Utilisation de st.number_input avec key pour éviter les conflits
    page = st.number_input('Page', min_value=1, max_value=total_pages, value=1, key='page_number')
    start = (page - 1) * items_per_page
    end = start + items_per_page
    for result in results[start:end]:
        st.write(f"**PV {result['pv_number']}** ({result['date']}): {result['context']}")
    st.write(f"Page {page} sur {total_pages}")

def download_results(results):
    df = pd.DataFrame(results)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Télécharger les résultats en CSV",
        data=csv,
        file_name='resultats_analyse.csv',
        mime='text/csv',
    )

def main():
    st.title("Analyse de la Fréquence d'Apparition de Termes dans des Fichiers XML")

    # Téléchargement des fichiers
    uploaded_files = st.file_uploader(
        "Téléchargez les fichiers XML/XHTML",
        accept_multiple_files=True,
        type=['xml', 'xhtml']
    )

    search_query = st.text_input('Entrez le(s) terme(s) ou phrase(s) à rechercher (utilisez "/" pour "OU")', '')

    # Définir les dates par défaut en utilisant st.session_state ou les valeurs par défaut
    default_start_date = st.session_state.get('start_date', datetime.date(1959, 1, 1))
    default_end_date = st.session_state.get('end_date', datetime.date.today())

    # Définir les valeurs min et max pour les sélecteurs de date
    min_date = datetime.date(1959, 1, 1)
    max_date = datetime.date.today()

    # Sélection des dates avec min_value et max_value
    st.sidebar.subheader('Filtres de Date')
    start_date = st.sidebar.date_input(
        'Date de début',
        value=default_start_date,
        min_value=min_date,
        max_value=max_date,
        key='start_date_input'
    )
    end_date = st.sidebar.date_input(
        'Date de fin',
        value=default_end_date,
        min_value=min_date,
        max_value=max_date,
        key='end_date_input'
    )

    # Vérifier que la date de fin est supérieure ou égale à la date de début
    if start_date > end_date:
        st.sidebar.error('La date de début doit être antérieure ou égale à la date de fin.')

    if st.button('Lancer l\'analyse'):
        if not uploaded_files or not search_query:
            st.error('Veuillez télécharger les fichiers et fournir les termes de recherche.')
        elif start_date > end_date:
            st.error('La date de début doit être antérieure ou égale à la date de fin.')
        else:
            search_pattern = build_search_pattern(search_query)
            with st.spinner('Analyse en cours...'):
                # Préparez les fichiers pour l'analyse
                files = [(file, file.name) for file in uploaded_files]
                results, term_frequency = analyze_files_uploaded(files, search_pattern, start_date, end_date)
                # Stocker les résultats dans st.session_state
                st.session_state['results'] = results
                st.session_state['term_frequency'] = term_frequency
                st.session_state['search_query'] = search_query  # Enregistrer la requête de recherche
                st.session_state['start_date'] = start_date
                st.session_state['end_date'] = end_date

    # Vérifier si les résultats sont dans session_state
    if 'results' in st.session_state and 'term_frequency' in st.session_state:
        if st.session_state['term_frequency']:
            st.subheader('Graphique de fréquence des termes par année ou par fichier')
            plot_term_frequency_interactive(st.session_state['term_frequency'])

            # Section du nuage de mots (commentée)
            # st.subheader('Nuage de mots des contextes')
            # all_contexts = ' '.join([result['context'] for result in st.session_state['results']])
            # generate_wordcloud(all_contexts)

            st.subheader('Occurrences trouvées')
            display_paginated_results(st.session_state['results'])

            st.subheader('Télécharger les résultats')
            download_results(st.session_state['results'])
        else:
            st.info('Aucune occurrence trouvée.')

if __name__ == '__main__':
    main()
