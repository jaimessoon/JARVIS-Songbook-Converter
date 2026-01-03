import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re
from pychord import Chord

st.set_page_config(page_title="JARVIS Songbook Converter", page_icon="🎸")

# --- CORE FUNCTIONS ---

def search_ultimate_guitar(query):
    search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={query}"
    response = requests.get(search_url, headers={'User-Agent': 'Mozilla/5.0'})
    pattern = re.compile(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', re.DOTALL)
    match = pattern.search(response.text)
    if match:
        data = json.loads(match.group(1))
        return data['data'].get('results', [])
    return []

def get_song_data(url):
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    pattern = re.compile(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', re.DOTALL)
    match = pattern.search(response.text)
    if match:
        data = json.loads(match.group(1))
        tab_view = data['data'].get('tab_view', {})
        wiki_tab = tab_view.get('wiki_tab', {})
        content = wiki_tab.get('content', "")
        title = data['data']['tab']['song_name']
        artist = data['data']['tab']['artist_name']
        return title, artist, content
    return None, None, None

def transpose_chordpro(text, semitones):
    if semitones == 0:
        return text.replace("[ch]", "[").replace("[/ch]", "]")
    
    def shift(match):
        chord_str = match.group(1)
        try:
            c = Chord(chord_str)
            c.transpose(semitones)
            return f"[{c.chord}]"
        except:
            return f"[{chord_str}]" # Return original if pychord can't parse

    # Replace [ch]Chord[/ch] with transposed [Chord]
    processed = re.sub(r'\[ch\](.*?)\[/ch\]', shift, text)
    return processed.replace("[tab]", "").replace("[/tab]", "")

# --- UI LAYOUT ---

st.title("🎸 JARVIS")
st.caption("Jaimes' Artist Resource & Verse Integration System")

# Sidebar for Transposition
with st.sidebar:
    st.header("Settings")
    transpose_val = st.slider("Transpose (Semitones)", -11, 11, 0)
    st.info("0 = Original Key. +1 = Up a half step.")

query = st.text_input("Search for a song:", placeholder="e.g. Hotel California")

if query:
    results = search_ultimate_guitar(query)
    
    if results:
        # We only want results that have a URL and are likely chords/tabs
        valid_results = [r for r in results if 'tab_url' in r and 'type' in r]
        options = [f"{r['song_name']} - {r['artist_name']} ({r['type']})" for r in valid_results]
        
        selected_option = st.selectbox("Select Version:", options)
        selected_index = options.index(selected_option)
        selected_url = valid_results[selected_index]['tab_url']
        
        if st.button("Generate Songbook Pro File"):
            with st.spinner("JARVIS is processing..."):
                title, artist, content = get_song_data(selected_url)
                
                if content:
                    final_content = f"{{title: {title}}}\n{{artist: {artist}}}\n\n"
                    final_content += transpose_chordpro(content, transpose_val)
                    
                    st.success(f"Successfully converted {title}!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("💾 Download .pro", final_content, f"{title}.pro")
                    with col2:
                        if st.button("📋 Copy to Clipboard (Preview)"):
                            st.toast("Check the text box below!")

                    st.text_area("ChordPro Content:", value=final_content, height=500)
    else:
        st.error("No results found. Try a different search term.")
