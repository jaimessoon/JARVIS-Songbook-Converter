import streamlit as st
import requests
import json
import re
import html
from pychord import Chord

# --- CONFIG & HEADERS ---
st.set_page_config(page_title="JARVIS Songbook Converter", page_icon="🎸", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# --- CORE FUNCTIONS ---

def search_ultimate_guitar(query):
    search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={query}"
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        # Search for the JSON data in the new 'js-store' location
        pattern = re.compile(r'class="js-store"\s+data-value="([^"]+)"')
        match = pattern.search(response.text)
        if match:
            json_str = html.unescape(match.group(1))
            data = json.loads(json_str)
            return data['store']['page']['data'].get('results', [])
    except Exception as e:
        st.error(f"Search Error: {e}")
    return []

def get_song_data(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        pattern = re.compile(r'class="js-store"\s+data-value="([^"]+)"')
        match = pattern.search(response.text)
        if match:
            json_str = html.unescape(match.group(1))
            data = json.loads(json_str)
            page_data = data['store']['page']['data']
            content = page_data.get('tab_view', {}).get('wiki_tab', {}).get('content', "")
            title = page_data['tab']['song_name']
            artist = page_data['tab']['artist_name']
            return title, artist, content
    except Exception as e:
        st.error(f"Retrieve Error: {e}")
    return None, None, None

def transpose_chordpro(text, semitones):
    # Ultimate Guitar uses [ch]Chord[/ch]. Songbook Pro uses [Chord].
    if semitones == 0:
        processed = text.replace("[ch]", "[").replace("[/ch]", "]")
    else:
        def shift(match):
            chord_str = match.group(1)
            try:
                c = Chord(chord_str)
                c.transpose(semitones)
                return f"[{c.chord}]"
            except:
                return f"[{chord_str}]"
        processed = re.sub(r'\[ch\](.*?)\[/ch\]', shift, text)
    
    # Clean up standard UG tags
    processed = processed.replace("[tab]", "").replace("[/tab]", "")
    return processed

# --- UI LAYOUT ---

st.title("🎸 JARVIS")
st.caption("Jaimes' Artist Resource & Verse Integration System")

# SIDEBAR: Settings & Backup Manual Mode
with st.sidebar:
    st.header("⚙️ Settings")
    transpose_val = st.slider("Transpose (Semitones)", -11, 11, 0)
    st.divider()
    
    st.header("🆘 Manual Backup")
    st.write("If search fails, paste the 'Source' text from the website here:")
    manual_content = st.text_area("Paste UG Tab Content here:", height=200)
    manual_title = st.text_input("Manual Title", "My Song")
    manual_artist = st.text_input("Manual Artist", "Unknown")

# MAIN AREA
tab1, tab2 = st.tabs(["Search & Convert", "Output Result"])

with tab1:
    query = st.text_input("Search Ultimate-Guitar:", placeholder="e.g. Amazing Grace")

    if query:
        with st.status(f"JARVIS is searching for '{query}'...", expanded=True) as status:
            results = search_ultimate_guitar(query)
            
            if results:
                # Filter for entries that have URLs
                valid_results = [r for r in results if 'tab_url' in r]
                
                if valid_results:
                    status.update(label=f"Found results for '{query}'!", state="complete")
                    options = [f"{r['song_name']} - {r['artist_name']} ({r.get('type', 'Tab')})" for r in valid_results]
                    selected_option = st.selectbox("Select Version:", options)
                    
                    selected_index = options.index(selected_option)
                    url = valid_results[selected_index]['tab_url']
                    
                    if st.button("Convert Selection"):
                        t, a, c = get_song_data(url)
                        if c:
                            st.session_state['chordpro'] = f"{{title: {t}}}\n{{artist: {a}}}\n\n" + transpose_chordpro(c, transpose_val)
                            st.session_state['song_name'] = t
                            st.info("Check 'Output Result' tab!")
                else:
                    status.update(label=f"No results found for '{query}'", state="error")
            else:
                status.update(label=f"No results found for '{query}'", state="error")
                st.error(f"I couldn't find anything for '{query}'.")

    # Handle Manual Mode
    if manual_content:
        if st.button("Convert Manual Paste"):
            # If manually pasted, we assume chords are either in [ch] or just raw text
            # Here we wrap them in [] for ChordPro
            c_processed = manual_content.replace("[ch]", "[").replace("[/ch]", "]")
            st.session_state['chordpro'] = f"{{title: {manual_title}}}\n{{artist: {manual_artist}}}\n\n" + c_processed
            st.session_state['song_name'] = manual_title
            st.success("Manual content processed! Check 'Output Result' tab.")

with tab2:
    if 'chordpro' in st.session_state:
        st.subheader(f"Songbook Pro Format: {st.session_state.get('song_name')}")
        
        # Action Buttons
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="💾 Download .pro file",
                data=st.session_state['chordpro'],
                file_name=f"{st.session_state.get('song_name')}.pro",
                mime="text/plain"
            )
        with col2:
            st.button("📋 Refresh/Reset", on_click=lambda: st.session_state.clear())

        st.text_area("Copy/Paste Content:", value=st.session_state['chordpro'], height=500)
    else:
        st.write("Search for a song and convert it to see the result here.")
