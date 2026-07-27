import os
import re
import pickle
import urllib.parse
import requests
import pandas as pd
import streamlit as st

# =============================================================================
# 1. APPLICATION CONFIGURATION & STATE INITIALIZATION
# =============================================================================
st.set_page_config(
    page_title="Netflix • Watch Movies Online",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Clear Streamlit cache to guarantee fresh state
st.cache_data.clear()

# Initialize session state for interactive click-to-recommend functionality
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

# Extract query parameters for poster click navigation
try:
    query_movie = st.query_params.get("movie", None)
    if query_movie:
        if isinstance(query_movie, list):
            query_movie = query_movie[0]
        st.session_state.selected_movie = urllib.parse.unquote(query_movie)
except Exception:
    pass

# =============================================================================
# 2. UI & CSS STYLING HELPERS
# =============================================================================
def render_html(html_str: str) -> None:
    """Renders HTML cleanly without Streamlit markdown treating indented lines as code blocks."""
    clean_html = "".join([line.strip() for line in html_str.splitlines()])
    st.markdown(clean_html, unsafe_allow_html=True)


def load_custom_css() -> None:
    """Injects style.css into the Streamlit app header."""
    css_file = "style.css"
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            css_content = f"<style>{f.read()}</style>"
            try:
                st.html(css_content)
            except AttributeError:
                render_html(css_content)

load_custom_css()

# =============================================================================
# 3. PRECOMPUTED POSTERS & API CONFIGURATION
# =============================================================================
DEFAULT_POSTERS = {
    "Avatar": "https://image.tmdb.org/t/p/w500/gKY6q7SjCkAU6FqvqWybDYgUKIF.jpg",
    "The Avengers": "https://image.tmdb.org/t/p/w500/RYMX2wcKCBAr24UyPD7xwmjaTn.jpg",
    "Titanic": "https://image.tmdb.org/t/p/w500/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg",
    "The Dark Knight": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
    "Iron Man": "https://image.tmdb.org/t/p/w500/78lPtwv72eTNqFW9COBYI0dWDJa.jpg",
    "Interstellar": "https://image.tmdb.org/t/p/w500/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg",
    "Inception": "https://image.tmdb.org/t/p/w500/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg",
    "Gladiator": "https://image.tmdb.org/t/p/w500/wN2xWp1eIwCKOD0BHTcErTBv1Uq.jpg",
    "The Matrix": "https://image.tmdb.org/t/p/w500/dXNAPwY7VrqMAo51EKhhCJfaGb5.jpg",
    "Fight Club": "https://image.tmdb.org/t/p/w500/jSziioSwPVrOy9Yow3XhWIBDjq1.jpg",
    "Jurassic Park": "https://image.tmdb.org/t/p/w500/4vaXzwsRtyRA7cGNFevFA2pTocv.jpg",
    "Forrest Gump": "https://image.tmdb.org/t/p/w500/Cw4hIUIAmSYfK9QfaUW5igp9La.jpg",
    "The Shawshank Redemption": "https://image.tmdb.org/t/p/w500/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg",
    "Pulp Fiction": "https://image.tmdb.org/t/p/w500/vQWk5YBFWF4bZaofAbv0tShwBvQ.jpg",
    "The Godfather": "https://image.tmdb.org/t/p/w500/wWJbBo5yjw22AIjE8isBFoiBI3S.jpg"
}

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
try:
    if not TMDB_API_KEY and "TMDB_API_KEY" in st.secrets:
        TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    pass
TMDB_API_KEY = TMDB_API_KEY.strip()

# =============================================================================
# 4. DATA MODEL LOADERS
# =============================================================================
@st.cache_data(show_spinner=False)
def load_data():
    """Loads movie dataframe, similarity matrix, and rich metadata dictionary. Automatically builds models if missing."""
    if not os.path.exists("movie_dict.pkl") or not os.path.exists("similarity.pkl"):
        try:
            import model_builder
            model_builder.build_models()
        except Exception as e:
            st.error(f"Error building models: {e}")
            return None, None, {}

    if not os.path.exists("movie_dict.pkl") or not os.path.exists("similarity.pkl"):
        return None, None, {}

    with open("movie_dict.pkl", "rb") as f:
        movie_dict = pickle.load(f)
    with open("similarity.pkl", "rb") as f:
        similarity_matrix = pickle.load(f)
        
    metadata_dict = {}
    if os.path.exists("metadata_dict.pkl"):
        try:
            with open("metadata_dict.pkl", "rb") as f:
                metadata_dict = pickle.load(f)
        except Exception:
            pass

    return pd.DataFrame(movie_dict), similarity_matrix, metadata_dict

with st.spinner("🎬 Curating your Netflix streaming catalog & recommendations..."):
    movies, similarity, all_metadata = load_data()

# =============================================================================
# 5. POSTER & METADATA SERVICES
# =============================================================================
def fetch_poster(movie_id: int, movie_title: str = None) -> str:
    """Fetches high-res movie poster URL with multi-layer fallback strategy."""
    if movie_title and movie_title in DEFAULT_POSTERS:
        return DEFAULT_POSTERS[movie_title]
    
    if TMDB_API_KEY:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                poster_path = res.json().get('poster_path')
                if poster_path:
                    return f"https://image.tmdb.org/t/p/w500/{poster_path}"
        except Exception:
            pass

    try:
        page_url = f"https://www.themoviedb.org/movie/{movie_id}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(page_url, headers=headers, timeout=4)
        if res.status_code == 200:
            matches = re.findall(r'https://image\.tmdb\.org/t/p/w(?:500|600_and_h900_bestv2)/[^"\']+\.(?:jpg|png|webp)', res.text)
            if matches:
                return matches[0]
    except Exception:
        pass

    return "https://placehold.co/500x750/1F1F1F/FFFFFF/png?text=Poster+Not+Available&font=Montserrat"


def fetch_movie_details(movie_id: int, movie_title: str) -> dict:
    """Extracts Director, Starring Cast, Studio/Crew, Tagline, Overview, Runtime, Year, and Rating."""
    if movie_title in all_metadata:
        return all_metadata[movie_title]

    details = {
        "tagline": "An unforgettable cinematic journey.",
        "overview": "Discover the incredible story and characters that make this feature film a captivating streaming experience.",
        "year": "2018", 
        "runtime": "2h 15m", 
        "rating": "7.8 / 10", 
        "genres": "Feature Film • Drama • Adventure", 
        "match": "94% Match",
        "director": "Acclaimed Director",
        "cast": "Leading Ensemble Cast",
        "crew": "Major Production Studio"
    }

    if TMDB_API_KEY:
        try:
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json()
                if data.get("tagline"): details["tagline"] = data["tagline"]
                if data.get("overview"): details["overview"] = data["overview"]
                if data.get("release_date"): details["year"] = data["release_date"][:4]
                if data.get("runtime"): details["runtime"] = f"{data['runtime'] // 60}h {data['runtime'] % 60}m"
                if data.get("vote_average"): details["rating"] = f"{round(data['vote_average'], 1)} / 10"
                if data.get("genres"): details["genres"] = " • ".join([g["name"] for g in data["genres"][:3]])
                if data.get("production_companies"): details["crew"] = " • ".join([c["name"] for c in data["production_companies"][:2]])
            
            cred_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API_KEY}&language=en-US"
            cred_res = requests.get(cred_url, timeout=3)
            if cred_res.status_code == 200:
                c_data = cred_res.json()
                cast_list = [actor["name"] for actor in c_data.get("cast", [])[:7]]
                if cast_list: details["cast"] = ", ".join(cast_list)
                for member in c_data.get("crew", []):
                    if member.get("job") == "Director":
                        details["director"] = member.get("name")
                        break
        except Exception:
            pass

    return details

# =============================================================================
# 6. RECOMMENDATION ALGORITHM
# =============================================================================
def recommend(movie_title: str):
    """Computes top 5 similar movies, posters, and match percentage scores."""
    try:
        movie_index = movies[movies['title'] == movie_title].index[0]
        distances = similarity[movie_index]
        movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

        recommended_titles = []
        recommended_posters = []
        match_scores = []

        for item in movies_list:
            idx = item[0]
            score = item[1]
            m_id = movies.iloc[idx].movie_id
            m_title = movies.iloc[idx].title
            
            match_pct = min(99, max(85, int(score * 100) + 72))
            
            recommended_titles.append(m_title)
            recommended_posters.append(fetch_poster(m_id, m_title))
            match_scores.append(f"{match_pct}% Match")

        return recommended_titles, recommended_posters, match_scores
    except Exception:
        return [], [], []

# =============================================================================
# 7. UI COMPONENT RENDERING HELPERS
# =============================================================================
def render_movie_row(title_text: str, movie_titles_list: list, row_key_prefix: str) -> None:
    """Renders a 5-column horizontal grid of clickable movie posters."""
    render_html(f"""
    <div style="margin-top: 2rem; margin-bottom: 0.8rem;">
        <h3 style="color: #FFFFFF; font-size: 1.45rem; font-weight: 800; margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.8); border-left: 4px solid #E50914; padding-left: 10px;">{title_text}</h3>
    </div>
    """)
    
    cols = st.columns(5)
    default_matches = ["98% Match", "97% Match", "95% Match", "94% Match", "91% Match"]
    for i, col in enumerate(cols):
        if i < len(movie_titles_list):
            m_title = movie_titles_list[i]
            poster_url = DEFAULT_POSTERS.get(m_title, "https://placehold.co/500x750/1F1F1F/FFFFFF/png?text=Poster+Not+Available&font=Montserrat")
            match_badge = default_matches[i % len(default_matches)]
            encoded_title = urllib.parse.quote(m_title)
            with col:
                render_html(f"""
                <a href="?movie={encoded_title}" target="_self" class="movie-card-link" title="Click to view details and recommendations for {m_title}">
                    <img src="{poster_url}" class="poster-img" alt="{m_title}">
                    <div style="text-align: left; margin-top: 8px; padding: 0 2px;">
                        <div style="margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
                            <div>
                                <span style="color: #46d369; font-weight: 800; font-size: 0.82rem;">{match_badge}</span>
                                <span style="border: 1px solid rgba(255,255,255,0.4); color: #AAAAAA; padding: 0px 4px; font-size: 0.65rem; border-radius: 2px; margin-left: 6px;">HD</span>
                            </div>
                            <span style="color: #AAAAAA; font-size: 0.72rem;">16+</span>
                        </div>
                        <h4 style="color: #FFFFFF; font-size: 0.95rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{m_title}</h4>
                    </div>
                </a>
                """)

# =============================================================================
# 8. TOP NAVIGATION BAR
# =============================================================================
render_html("""
<div class="netflix-navbar">
    <div class="navbar-left">
        <a href="?" target="_self" class="netflix-logo">NETFLIX</a>
    </div>
</div>
""")

if movies is None or similarity is None:
    st.error("🚨 **Service Temporarily Unavailable.** We are currently updating our streaming catalog. Please refresh the page soon!")
    st.stop()

# =============================================================================
# 9. SEARCH BAR & DISCOVERY ENGINE (ACCESS ALL 4,800+ MOVIES)
# =============================================================================
render_html("""
<div style="margin-top: 1rem; margin-bottom: 0.5rem;">
    <h3 style="color: #FFFFFF; font-size: 1.3rem; font-weight: 800; margin: 0; display: flex; align-items: center;">
        <span style="color: #E50914; margin-right: 8px;">🔍</span> Search & Explore Full Catalog (4,800+ Movies)
    </h3>
    <p style="color: #AAAAAA; font-size: 0.9rem; margin: 4px 0 12px 0;">Search by keyword or select any movie from our complete catalog dropdown below to instantly view details and AI recommendations.</p>
</div>
""")

col_search, col_dropdown = st.columns([3, 2])

with col_search:
    search_query = st.text_input(
        "Unified Search",
        placeholder="Type any title, actor, director, or genre (e.g. Inception, DiCaprio, Nolan, Sci-Fi)...",
        label_visibility="collapsed"
    )

all_titles_sorted = ["-- Browse All 4,800+ Movies --"] + list(movies['title'].sort_values().unique())
with col_dropdown:
    selected_from_dropdown = st.selectbox(
        "Browse Full Catalog",
        options=all_titles_sorted,
        label_visibility="collapsed"
    )
    if selected_from_dropdown and selected_from_dropdown != "-- Browse All 4,800+ Movies --":
        st.session_state.selected_movie = selected_from_dropdown

# Render search results if query typed
if search_query and len(search_query.strip()) >= 2:
    query = search_query.strip().lower()
    matching_df = movies[movies['title'].str.lower().str.contains(query, na=False) | movies['tags'].str.contains(query, na=False)].head(10)
    
    if not matching_df.empty:
        exact_match = movies[movies['title'].str.lower() == query]
        if not exact_match.empty:
            st.session_state.selected_movie = exact_match.iloc[0]['title']
        elif len(matching_df) == 1 or movies['title'].str.lower().str.startswith(query).any():
            top_title = matching_df.iloc[0]['title']
            if query in top_title.lower():
                st.session_state.selected_movie = top_title

        render_html(f"""
        <div style="margin-top: 1.5rem; margin-bottom: 1rem; padding: 12px 18px; background: rgba(255, 255, 255, 0.06); border-left: 4px solid #FFFFFF; border-radius: 6px;">
            <h3 style="color: #FFFFFF; font-size: 1.4rem; font-weight: 700; margin: 0;">🔍 Search Results for: <span style="color: #E50914;">"{search_query}"</span> ({len(matching_df)} found)</h3>
        </div>
        """)
        
        res_cols = st.columns(5)
        for i, (_, row_data) in enumerate(matching_df.iterrows()):
            col_idx = i % 5
            m_title = row_data['title']
            m_id = row_data['movie_id']
            encoded_title = urllib.parse.quote(m_title)
            with res_cols[col_idx]:
                render_html(f"""
                <a href="?movie={encoded_title}" target="_self" class="movie-card-link" title="Click to view details and recommendations for {m_title}">
                    <img src="{fetch_poster(m_id, m_title)}" class="poster-img" alt="{m_title}">
                    <div style="text-align: left; margin-top: 8px; padding: 0 2px;">
                        <div style="margin-bottom: 4px;">
                            <span style="color: #46d369; font-weight: 800; font-size: 0.82rem;">95% Match</span>
                            <span style="border: 1px solid rgba(255,255,255,0.4); color: #AAAAAA; padding: 0px 4px; font-size: 0.65rem; border-radius: 2px; margin-left: 6px;">HD</span>
                        </div>
                        <h4 style="color: #FFFFFF; font-size: 0.95rem; font-weight: 700; margin: 0; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{m_title}</h4>
                    </div>
                </a>
                """)
        render_html("<hr style='border-color: rgba(255,255,255,0.15); margin: 2rem 0;'>")
    else:
        st.warning(f"No movies, actors, or genres matching '{search_query}' were found. Try another keyword!")

# =============================================================================
# 10. MOVIE DETAILS SHOWCASE & AI RECOMMENDATIONS
# =============================================================================
if st.session_state.selected_movie:
    m_name = st.session_state.selected_movie
    try:
        m_id = movies[movies['title'] == m_name].iloc[0]['movie_id']
    except Exception:
        m_id = 0
        
    m_poster = fetch_poster(m_id, m_name)
    m_details = fetch_movie_details(m_id, m_name)

    # 1. Movie Details Showcase Card
    render_html(f"""
    <div style="background: linear-gradient(135deg, rgba(20,20,20,0.95) 0%, rgba(32,32,32,0.95) 100%); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 2.2rem; margin: 1.5rem 0 2.5rem 0; box-shadow: 0 20px 40px rgba(0,0,0,0.8);">
        <div style="display: flex; gap: 2.5rem; align-items: flex-start; flex-wrap: wrap;">
            <div style="flex: 0 0 240px; max-width: 240px;">
                <img src="{m_poster}" alt="{m_name}" style="width: 100%; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.9); border: 1px solid rgba(255,255,255,0.2); display: block;">
            </div>
            <div style="flex: 1; min-width: 300px;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
                    <span style="background-color: #E50914; color: #fff; font-weight: 900; font-size: 0.75rem; padding: 3px 8px; border-radius: 2px; letter-spacing: 0.5px;">NETFLIX SELECTION</span>
                    <span style="color: #46d369; font-weight: 800; font-size: 1.05rem;">{m_details.get('match', '98% Match')}</span>
                </div>
                <h1 style="color: #FFFFFF; font-size: 3rem; font-weight: 900; margin: 0 0 8px 0; line-height: 1.1; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">{m_name}</h1>
                <p style="color: #CCCCCC; font-style: italic; font-size: 1.15rem; margin: 0 0 1.2rem 0; font-weight: 500;">"{m_details.get('tagline', '')}"</p>
                <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 1.5rem; flex-wrap: wrap; font-size: 0.95rem;">
                    <span style="color: #E5E5E5; font-weight: 700;">📅 {m_details.get('year', '2015')}</span>
                    <span style="color: #E5E5E5; font-weight: 700;">⏱️ {m_details.get('runtime', '2h 10m')}</span>
                    <span style="color: #E50914; font-weight: 800;">⭐ {m_details.get('rating', '8.2 / 10')}</span>
                    <span style="border: 1px solid rgba(255,255,255,0.4); color: #CCCCCC; padding: 1px 6px; font-size: 0.75rem; border-radius: 2px; font-weight: 600;">HD</span>
                    <span style="border: 1px solid rgba(255,255,255,0.4); color: #CCCCCC; padding: 1px 6px; font-size: 0.75rem; border-radius: 2px; font-weight: 600;">5.1 Audio</span>
                    <span style="background: rgba(255,255,255,0.1); color: #FFFFFF; padding: 3px 10px; border-radius: 4px; font-size: 0.85rem; font-weight: 600;">🎬 {m_details.get('genres', 'Feature Film')}</span>
                </div>
                <h4 style="color: #AAAAAA; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 6px 0;">Story Synopsis</h4>
                <p style="color: #E5E5E5; font-size: 1.1rem; line-height: 1.6; margin: 0 0 1.4rem 0; max-width: 780px;">{m_details.get('overview', 'No overview available.')}</p>
                <div style="padding-top: 1.2rem; border-top: 1px solid rgba(255, 255, 255, 0.15); font-size: 0.92rem; line-height: 1.8;">
                    <div style="margin-bottom: 4px;">
                        <span style="color: #737373; font-weight: 700; display: inline-block; width: 90px;">Director:</span>
                        <span style="color: #FFFFFF; font-weight: 600;">{m_details.get('director', 'Acclaimed Director')}</span>
                    </div>
                    <div style="margin-bottom: 4px;">
                        <span style="color: #737373; font-weight: 700; display: inline-block; width: 90px;">Starring:</span>
                        <span style="color: #E5E5E5; font-weight: 500;">{m_details.get('cast', 'All-Star Cast')}</span>
                    </div>
                    <div>
                        <span style="color: #737373; font-weight: 700; display: inline-block; width: 90px;">Studio/Crew:</span>
                        <span style="color: #AAAAAA; font-style: italic;">{m_details.get('crew', 'Major Studio')}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """)
    
    # 2. Recommended Movies Grid
    render_html(f"""
    <div style="margin-top: 2rem; margin-bottom: 1rem; padding: 12px 18px; background: rgba(229, 9, 20, 0.15); border-left: 5px solid #E50914; border-radius: 6px;">
        <h3 style="color: #FFFFFF; font-size: 1.5rem; font-weight: 800; margin: 0;">🍿 MORE LIKE <span style="color: #FF2E38;">{m_name.upper()}</span></h3>
    </div>
    """)
    
    with st.spinner("Finding your best matches..."):
        names, posters, match_scores = recommend(m_name)

    if names:
        col1, col2, col3, col4, col5 = st.columns(5)
        columns = [col1, col2, col3, col4, col5]

        for i, col in enumerate(columns):
            encoded_rec_title = urllib.parse.quote(names[i])
            with col:
                render_html(f"""
                <a href="?movie={encoded_rec_title}" target="_self" class="movie-card-link" title="Click to view details and recommendations for {names[i]}">
                    <img src="{posters[i]}" class="poster-img" alt="{names[i]}">
                    <div style="text-align: left; margin-top: 8px; padding: 0 2px;">
                        <div style="margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;">
                            <div>
                                <span style="color: #46d369; font-weight: 800; font-size: 0.82rem;">{match_scores[i]}</span>
                                <span style="border: 1px solid rgba(255,255,255,0.4); color: #AAAAAA; padding: 0px 4px; font-size: 0.65rem; border-radius: 2px; margin-left: 6px;">HD</span>
                            </div>
                            <span style="color: #AAAAAA; font-size: 0.72rem;">18+</span>
                        </div>
                        <h4 style="color: #FFFFFF; font-size: 0.95rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{names[i]}</h4>
                    </div>
                </a>
                """)
        render_html("<hr style='border-color: rgba(255,255,255,0.15); margin: 2.5rem 0;'>")

# =============================================================================
# 11. FEATURED HERO BANNER & CATALOG ROWS
# =============================================================================
render_html("""
<div class="hero-banner">
    <div class="top10-badge"><span class="top10-icon">TOP 10</span> #1 in Movies Today</div>
    <h1 class="hero-title">THE DARK KNIGHT</h1>
    <div class="hero-meta">
        <span>99% Match</span>
        <span style="color: #CCCCCC; font-weight: 500;">2008</span>
        <span style="border: 1px solid rgba(255,255,255,0.4); color: #CCCCCC; padding: 0 6px; font-size: 0.75rem; border-radius: 2px;">HD</span>
        <span style="border: 1px solid rgba(255,255,255,0.4); color: #CCCCCC; padding: 0 6px; font-size: 0.75rem; border-radius: 2px;">5.1 Audio</span>
        <span style="color: #CCCCCC; font-weight: 500;">2h 32m</span>
    </div>
    <p class="hero-overview">
        When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.
    </p>
</div>
""")

render_html("<br>")

render_movie_row("🔥 Trending Now on Netflix", ["Avatar", "The Avengers", "Titanic", "Inception", "Interstellar"], "trending")
render_movie_row("🌟 Critically Acclaimed Masterpieces", ["The Dark Knight", "The Shawshank Redemption", "The Godfather", "Pulp Fiction", "Fight Club"], "masterpieces")
render_movie_row("🎬 Sci-Fi & Action Favorites", ["The Matrix", "Gladiator", "Jurassic Park", "Iron Man", "Forrest Gump"], "scifi")

# =============================================================================
# 12. CONSUMER FOOTER
# =============================================================================
render_html("""
<div style="text-align: center; padding: 4rem 0 3rem 0; margin-top: 3rem; border-top: 1px solid rgba(255, 255, 255, 0.08); color: #737373; font-size: 0.85rem; line-height: 1.8;">
    <p style="margin-bottom: 1rem;">Questions? Call 1-800-012-3456</p>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-bottom: 1.5rem; font-size: 0.8rem;">
        <span style="cursor: pointer;">FAQ</span>
        <span style="cursor: pointer;">Help Center</span>
        <span style="cursor: pointer;">Terms of Use</span>
        <span style="cursor: pointer;">Privacy</span>
        <span style="cursor: pointer;">Cookie Preferences</span>
        <span style="cursor: pointer;">Corporate Information</span>
    </div>
    <p style="color: #555555;">© 2026 Netflix, Inc. • All rights reserved.</p>
</div>
""")
