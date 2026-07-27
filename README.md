# 🎬 Premium Content-Based Movie Recommendation System

A modern, polished, Netflix-inspired movie recommendation system built with **Python**, **Scikit-Learn**, and **Streamlit**. It uses **Content-Based Filtering** (Cosine Similarity) on movie metadata (genres, keywords, cast, crew, and plot summaries) and dynamically fetches actual movie posters using the **TMDB API**.

---

## ✨ Features
- **🔥 Premium Netflix UI/UX**: Sleek dark mode, vibrant red accents, smooth hover zoom animations (`transform: scale(1.05)`), and clean typography.
- **🖼️ Flawless Poster Rendering**: Displays real-time high-resolution movie posters in a responsive 5-column grid.
- **⚡ Automated Dataset Downloading**: Integrated with `kagglehub` to automatically fetch and cache the official TMDB 5000 dataset without any manual file moving!
- **🛡️ Robust Error Handling**: Automatic fallback to clean placeholder images if the TMDB API rate-limits, fails, or lacks an image.
- **🧠 Machine Learning Engine**: Vectorizes combined metadata tags using `CountVectorizer(max_features=5000)` and computes precise vector similarity using `cosine_similarity`.

---

## 🚀 Local Setup & Installation

### 1. Clone the Repository & Install Dependencies
```bash
git clone <your-repo-url>
cd Movie-Recommendation-System
pip install -r requirements.txt
```

### 2. Download the TMDB 5000 Dataset (Automated via `kagglehub`)
Thanks to the integrated **`kagglehub`** support in `model_builder.py`, you **do not need to manually download or move dataset files**! 
When you run `model_builder.py`, it will automatically execute:
```python
import kagglehub
path = kagglehub.dataset_download("tmdb/tmdb-movie-metadata")
```
and automatically copy `tmdb_5000_movies.csv` and `tmdb_5000_credits.csv` into your project directory for you!

*(Note: If you prefer manual downloading, you can still download from [Kaggle](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata) and place the CSV files in the root folder).*

### 3. Generate the ML Models (Phase 1)
Run the preprocessing script to clean data, extract features, and build the similarity matrix:
```bash
python model_builder.py
```
This generates two required pickle files in your directory:
- `movie_dict.pkl`
- `similarity.pkl`

### 4. Configure Your TMDB API Key
To fetch real posters, get a free v3 API key from [The Movie Database (TMDB)](https://www.themoviedb.org/settings/api). You can configure it in one of three ways:
- **Option A (Recommended for Local Dev)**: Set an environment variable:
  ```bash
  # Windows PowerShell
  $env:TMDB_API_KEY="your_actual_api_key_here"
  ```
- **Option B (Streamlit Secrets)**: Create `.streamlit/secrets.toml` and add:
  ```toml
  TMDB_API_KEY = "your_actual_api_key_here"
  ```
- **Option C (UI Input)**: Simply paste your key directly into the sidebar configuration panel inside the web app!

### 5. Launch the Web App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deployment to Streamlit Community Cloud

1. **Push to GitHub**: Commit and push your code to a public GitHub repository. Remember that `.gitignore` excludes dataset CSVs and `.pkl` files!
2. **Handle Model Files in Production**:
   - Since `.pkl` files are excluded by `.gitignore`, you can either remove `*.pkl` from `.gitignore` before committing if they are under GitHub's 100MB file limit (Git LFS recommended for large models), OR modify `app.py` to automatically trigger `build_models()` on startup if `similarity.pkl` is missing.
3. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io/) and connect your GitHub repository.
   - Select `app.py` as the main file path.
   - In the **Advanced settings** -> **Secrets** section, add your API key:
     ```toml
     TMDB_API_KEY = "your_production_api_key"
     ```
4. Click **Deploy!** 🚀

---

### 💡 Quick Start Instructions
To launch your app right now from your PowerShell terminal:
```powershell
# 1. Install dependencies (including kagglehub)
pip install -r requirements.txt

# 2. Generate the models (kagglehub will automatically fetch the TMDB 5000 dataset!)
python model_builder.py

# 3. Start the web app
streamlit run app.py
```
