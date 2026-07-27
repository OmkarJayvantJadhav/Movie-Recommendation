import os
import ast
import pickle
import shutil
import urllib.request
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Constants & Paths
MOVIES_CSV = "tmdb_5000_movies.csv"
CREDITS_CSV = "tmdb_5000_credits.csv"
MOVIES_PKL = "movie_dict.pkl"
SIMILARITY_PKL = "similarity.pkl"

# Public mirrors for backup fallback download if kagglehub is unavailable
MIRROR_MOVIES = "https://raw.githubusercontent.com/Laxminarayana-Position/Movie-Recommendation-System/main/tmdb_5000_movies.csv"
MIRROR_CREDITS = "https://raw.githubusercontent.com/Laxminarayana-Position/Movie-Recommendation-System/main/tmdb_5000_credits.csv"


def download_if_missing(file_path, url):
    """Downloads dataset from public mirror if not found locally."""
    if not os.path.exists(file_path):
        print(f"[{file_path}] not found locally. Attempting fallback download...")
        try:
            urllib.request.urlretrieve(url, file_path)
            print(f"-> Successfully downloaded [{file_path}]!")
        except Exception as e:
            print(f"-> Could not download [{file_path}] automatically: {e}")
            return False
    return True


def get_dataset_paths():
    """
    Checks for local dataset files. If missing, downloads automatically using kagglehub,
    falling back to public mirrors if kagglehub is not installed or fails.
    """
    if os.path.exists(MOVIES_CSV) and os.path.exists(CREDITS_CSV):
        print("-> Found dataset files in local workspace.")
        return MOVIES_CSV, CREDITS_CSV
    
    print("\nLocal CSV files not found. Attempting automatic download via kagglehub...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("tmdb/tmdb-movie-metadata")
        print(f"-> Kaggle dataset located at: {path}")
        
        movies_cache = os.path.join(path, "tmdb_5000_movies.csv")
        credits_cache = os.path.join(path, "tmdb_5000_credits.csv")
        
        # Copy to local directory for project consistency
        if os.path.exists(movies_cache) and os.path.exists(credits_cache):
            shutil.copy(movies_cache, MOVIES_CSV)
            shutil.copy(credits_cache, CREDITS_CSV)
            print("-> Successfully copied dataset files to local project directory!")
            return MOVIES_CSV, CREDITS_CSV
        else:
            return movies_cache, credits_cache
    except ImportError:
        print("-> [NOTE] 'kagglehub' not installed (`pip install kagglehub`). Falling back to mirror download...")
    except Exception as e:
        print(f"-> [NOTE] kagglehub download encountered an issue ({e}). Falling back to mirror download...")
    
    # Fallback to mirror URLs
    download_if_missing(MOVIES_CSV, MIRROR_MOVIES)
    download_if_missing(CREDITS_CSV, MIRROR_CREDITS)
    return MOVIES_CSV, CREDITS_CSV


def convert(text):
    """Extracts 'name' attributes from JSON-like string representations of lists."""
    names = []
    try:
        for item in ast.literal_eval(text):
            names.append(item['name'])
    except (ValueError, SyntaxError, TypeError):
        pass
    return names


def convert_top_3(text):
    """Extracts top 3 cast members from JSON-like string."""
    names = []
    try:
        counter = 0
        for item in ast.literal_eval(text):
            if counter != 3:
                names.append(item['name'])
                counter += 1
            else:
                break
    except (ValueError, SyntaxError, TypeError):
        pass
    return names


def fetch_director(text):
    """Extracts the director name from crew JSON-like string."""
    names = []
    try:
        for item in ast.literal_eval(text):
            if item.get('job') == 'Director':
                names.append(item['name'])
                break
    except (ValueError, SyntaxError, TypeError):
        pass
    return names


def collapse_spaces(list_of_strings):
    """Removes spaces between words (e.g., 'Science Fiction' -> 'ScienceFiction')."""
    return [item.replace(" ", "") for item in list_of_strings]


def build_models():
    print("=" * 60)
    print("PHASE 1: TMDB 5000 Data Preprocessing & Model Building")
    print("=" * 60)

    # 1. Ensure datasets exist via kagglehub or local check
    movies_path, credits_path = get_dataset_paths()
    if not os.path.exists(movies_path) or not os.path.exists(credits_path):
        print("\n[ERROR] Datasets missing. Please check your network connection or install kagglehub (`pip install kagglehub`).")
        return

    # 2. Load datasets
    print("\n[1/6] Loading datasets...")
    movies = pd.read_csv(movies_path)
    credits = pd.read_csv(credits_path)

    # 3. Merge datasets on 'title'
    print("[2/6] Merging movies and credits datasets...")
    movies = movies.merge(credits, on='title')
    
    # Ensure standard 'movie_id' column exists (movies['id'] holds the TMDB ID)
    if 'id' in movies.columns:
        movies['movie_id'] = movies['id']
    elif 'movie_id_x' in movies.columns:
        movies['movie_id'] = movies['movie_id_x']

    # Keep only essential columns for content-based filtering
    required_cols = ['movie_id', 'title', 'overview', 'genres', 'keywords', 'cast', 'crew']
    movies = movies[required_cols].dropna(subset=['overview'])

    # 4. Feature Extraction & Cleaning
    print("[3/6] Extracting features (genres, keywords, top 3 cast, director)...")
    movies['genres'] = movies['genres'].apply(convert).apply(collapse_spaces)
    movies['keywords'] = movies['keywords'].apply(convert).apply(collapse_spaces)
    movies['cast'] = movies['cast'].apply(convert_top_3).apply(collapse_spaces)
    movies['crew'] = movies['crew'].apply(fetch_director).apply(collapse_spaces)
    
    # Convert overview string into a list of words
    movies['overview'] = movies['overview'].apply(lambda x: x.split() if isinstance(x, str) else [])

    # Create unified 'tags' column
    print("[4/6] Creating unified 'tags' feature representation...")
    movies['tags'] = movies['overview'] + movies['genres'] + movies['keywords'] + movies['cast'] + movies['crew']
    
    # Create final dataframe
    new_df = movies[['movie_id', 'title', 'tags']].copy()
    new_df['tags'] = new_df['tags'].apply(lambda x: " ".join(x)).str.lower()

    # 5. Text Vectorization & Cosine Similarity
    print("[5/6] Applying CountVectorizer and computing Cosine Similarity matrix...")
    cv = CountVectorizer(max_features=5000, stop_words='english')
    vectors = cv.fit_transform(new_df['tags']).toarray()
    
    similarity = cosine_similarity(vectors)
    print(f"-> Cosine similarity matrix computed successfully. Shape: {similarity.shape}")

    # 6. Export models using Pickle
    print("[6/6] Exporting processed data and similarity matrix to disk...")
    with open(MOVIES_PKL, 'wb') as f:
        pickle.dump(new_df.to_dict(), f)
    
    with open(SIMILARITY_PKL, 'wb') as f:
        pickle.dump(similarity, f)

    print("\n[SUCCESS] Model building complete!")
    print(f"Generated artifacts: '{MOVIES_PKL}' and '{SIMILARITY_PKL}'")
    print("You can now launch the Streamlit web app using: streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    build_models()
