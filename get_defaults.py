import pickle
import pandas as pd
import requests
import re

m = pd.DataFrame(pickle.load(open('movie_dict.pkl', 'rb')))
famous = [
    'The Dark Knight', 'Inception', 'Avatar', 'The Avengers', 'Titanic', 
    'Interstellar', 'The Matrix', 'Gladiator', 'Jurassic Park', 'Pulp Fiction', 
    'Fight Club', 'Forrest Gump', 'Iron Man', 'The Shawshank Redemption', 'The Godfather'
]

results = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for _, row in m[m['title'].isin(famous)].iterrows():
    movie_id = row['movie_id']
    title = row['title']
    try:
        r = requests.get(f"https://www.themoviedb.org/movie/{movie_id}", headers=headers, timeout=5)
        if r.status_code == 200:
            matches = re.findall(r'https://image\.tmdb\.org/t/p/w(?:500|600_and_h900_bestv2)/[^"\']+\.(?:jpg|png|webp)', r.text)
            if matches:
                results[title] = matches[0]
            else:
                results[title] = "None"
    except Exception as e:
        results[title] = str(e)

for k, v in results.items():
    print(f'"{k}": "{v}",')
