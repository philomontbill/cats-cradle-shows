"""List all active shows with no video preview, sorted by Spotify popularity."""
import json, os, glob

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

spotify = {}
if os.path.exists('qa/spotify_cache.json'):
    with open('qa/spotify_cache.json') as f:
        spotify = json.load(f)

results = []
for fp in sorted(glob.glob('data/shows-*.json')):
    with open(fp) as f:
        data = json.load(f)
    venue = data['venue']['name']
    for show in data['shows']:
        if show.get('youtube_id') is None and not show.get('expired'):
            artist = show['artist']
            sp = spotify.get(artist, {})
            pop = sp.get('popularity', '?')
            match = sp.get('match_confidence', '-')
            results.append((pop if isinstance(pop, int) else -1, artist, venue, show['date'], match))

results.sort(key=lambda x: -x[0])
print(f"{'Artist':<60} {'Venue':<20} {'Date':<12} {'Pop':>3}  {'Spotify'}")
print("-" * 110)
for pop, artist, venue, date, match in results:
    p = str(pop) if pop >= 0 else '?'
    print(f"{artist:<60} {venue:<20} {date:<12} {p:>3}  {match}")
print(f"\nTotal: {len(results)} shows without video preview")
