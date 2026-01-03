import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

st.set_page_config(page_title="JARVIS Songbook Converter", page_icon="🎸")

def search_ultimate_guitar(query):
    search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={query}"
    response = requests.get(search_url)
    # Ultimate Guitar stores data in a JSON object inside a script tag
    pattern = re.compile(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', re.DOTALL)
    match = pattern.search(response.text)
    if match:
        data = json.loads(match.group(1))
        return data['data']['results']
    return []

def get_song_data(url):
    response = requests.get(url)
    pattern = re.compile(r'window\.UGAPP\.store\.page\s*=\s*(\{.*?\});', re.DOTALL)
    match = pattern.search(response.text)
    if match:
        data = json.loads(match.group(1))
        # This contains the tab content (lyrics + chords)
        tab_content = data['data']['tab_view']['wiki_tab']['content']
        # Metadata
        title = data['data']['tab']['song_name']
        artist = data['data']['tab']['artist_name']
        return title, artist, tab_content
    return None, None, None

def convert_to_songbook_pro(text):
    # Basic logic: Ultimate Guitar uses [ch]G[/ch] for chords. 
    # Songbook Pro uses [G].
    converted = text.replace("[ch]", "[").replace("[/ch]", "]")
    # Clean up other UG specific tags
    converted = converted.replace("[tab]", "").replace("[/tab]", "")
    return converted

# --- UI LOGIC ---
st.title("🎸 JARVIS")
st.subheader("Ultimate-Guitar to Songbook Pro Converter")

query = st.text_input("Search for a song or artist:", placeholder="e.g. Wish You Were Here")

if query:
    results = search_ultimate_guitar(query)
    
    if results:
        # Filter for Chords/Tabs only (Type 200/300 usually)
        options = [f"{r.get('song_name')} - {r.get('artist_name')} ({r.get('type')})" for r in results if 'tab_url' in r]
        selected_option = st.selectbox("Select a version:", options)
        
        # Find the URL for the selection
        selected_index = options.index(selected_option)
        selected_url = results[selected_index]['tab_url']
        
        if st.button("Convert Song"):
            title, artist, content = get_song_data(selected_url)
            if content:
                chordpro_content = f"{{title: {title}}}\n{{artist: {artist}}}\n\n" + convert_to_songbook_pro(content)
                
                st.success(f"Converted: {title} by {artist}")
                
                # Option 1: Copy Text Area
                st.text_area("Songbook Pro Format (Copy & Paste):", value=chordpro_content, height=400)
                
                # Option 2: Download File
                st.download_button(
                    label="Download .pro file",
                    data=chordpro_content,
                    file_name=f"{title.replace(' ', '_')}.pro",
                    mime="text/plain"
                )
    else:
        st.warning("No results found.")
