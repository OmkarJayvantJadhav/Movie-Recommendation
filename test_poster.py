import requests
import re

def scrape_poster(movie_id):
    url = f"https://www.themoviedb.org/movie/{movie_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            matches = re.findall(r'https://image\.tmdb\.org/t/p/w(?:500|600_and_h900_bestv2)/[^"\']+\.(?:jpg|png|webp)', r.text)
            if matches:
                return matches[0]
    except Exception as e:
        print("Error:", e)
    return "Not Found"

print("Titan A.E.:", scrape_poster(7450))
print("Small Soldiers:", scrape_poster(11551))
print("Independence Day:", scrape_poster(602))
print("Ender's Game:", scrape_poster(80274))
print("Aliens vs Predator:", scrape_poster(440))
