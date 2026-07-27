"""
Batch poster URL fetcher — tries multiple methods to get poster URLs.
Uses urllib (different SSL stack), HTTP fallback, and TMDB API discovery.
"""
import os
import re
import sys
import ssl
import time
import pickle
import json
import pandas as pd
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')

POSTERS_PKL = "posters_dict.pkl"
MOVIE_DICT_PKL = "movie_dict.pkl"

def load_existing():
    if os.path.exists(POSTERS_PKL):
        with open(POSTERS_PKL, "rb") as f:
            return pickle.load(f)
    return {}

def save_posters(d):
    with open(POSTERS_PKL, "wb") as f:
        pickle.dump(d, f)

def fetch_poster_urllib(movie_id):
    """Use urllib with a lenient SSL context."""
    url = f"https://www.themoviedb.org/movie/{movie_id}"
    
    # Create a lenient SSL context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html',
    })
    
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            
            # og:image
            m = re.search(r'content=["\'](https://image\.tmdb\.org/t/p/[^"\']+)["\'][^>]*property=["\']og:image', text)
            if not m:
                m = re.search(r'property=["\']og:image["\'][^>]*content=["\'](https://image\.tmdb\.org/t/p/[^"\']+)["\']', text)
            if m:
                poster = m.group(1)
                poster = re.sub(r'/t/p/w\d+/', '/t/p/w500/', poster)
                return poster
            
            # Any poster image
            imgs = re.findall(r'https://image\.tmdb\.org/t/p/w\d+/\w+\.jpg', text)
            if imgs:
                return re.sub(r'/t/p/w\d+/', '/t/p/w500/', imgs[0])
    except Exception as e:
        pass
    
    return None


def fetch_poster_api_nokey(movie_id):
    """Try the TMDB API v3 discover endpoint — some public endpoints work without auth."""
    # This usually won't work without a key, but worth trying
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=undefined"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pp = data.get('poster_path')
            if pp:
                return f"https://image.tmdb.org/t/p/w500{pp}"
    except Exception:
        pass
    return None


def main():
    print("=" * 60)
    print("  BATCH POSTER DOWNLOADER v2 (urllib + SSL bypass)")
    print("=" * 60)
    
    with open(MOVIE_DICT_PKL, "rb") as f:
        movies_df = pd.DataFrame(pickle.load(f))
    
    total = len(movies_df)
    posters = load_existing()
    print(f"Total movies: {total} | Already fetched: {len(posters)}")
    
    pending = [(r['movie_id'], r['title']) for _, r in movies_df.iterrows() if r['title'] not in posters]
    print(f"Remaining: {len(pending)}")
    
    if not pending:
        print("All done!")
        return
    
    # Test connectivity first with a single request
    print("\nTesting connectivity...")
    test_url = fetch_poster_urllib(19995)  # Avatar
    if test_url:
        print(f"  SUCCESS! Test poster: {test_url}")
    else:
        print("  WARNING: urllib method failed. Trying API fallback...")
        test_url = fetch_poster_api_nokey(19995)
        if test_url:
            print(f"  API fallback works: {test_url}")
        else:
            print("  Both methods failed. Network may be blocking TMDB entirely.")
            print("  Will still attempt batch — some requests may succeed.")
    
    fetched = 0
    failed = 0
    consecutive_fails = 0
    
    for i, (mid, title) in enumerate(pending):
        url = fetch_poster_urllib(mid)
        
        if url:
            posters[title] = url
            fetched += 1
            consecutive_fails = 0
            tag = "OK"
        else:
            failed += 1
            consecutive_fails += 1
            tag = "MISS"
        
        done = len(posters)
        pct = done / total * 100
        print(f"  [{done}/{total} {pct:.0f}%] {tag} - {title}")
        
        # Save every 50 movies
        if (i + 1) % 50 == 0:
            save_posters(posters)
            print(f"  -> Checkpoint saved: {len(posters)} posters")
        
        # If 20 consecutive failures, the network is down — stop
        if consecutive_fails >= 20:
            print(f"\n  STOPPING: {consecutive_fails} consecutive failures. Network appears blocked.")
            break
        
        time.sleep(0.35)
    
    save_posters(posters)
    print(f"\n{'=' * 60}")
    print(f"  DONE! Fetched: {fetched} | Failed: {failed}")
    print(f"  Total saved: {len(posters)} / {total} ({len(posters)/total*100:.1f}%)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
