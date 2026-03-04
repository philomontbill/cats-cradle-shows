"""List all active shows with no video preview."""
import json, os, glob

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []
for fp in sorted(glob.glob('data/shows-*.json')):
    with open(fp) as f:
        data = json.load(f)
    venue = data['venue']['name']
    for show in data['shows']:
        if show.get('youtube_id') is None and not show.get('expired'):
            artist = show['artist']
            results.append((artist, venue, show['date']))

results.sort(key=lambda x: x[0].lower())
print(f"{'Artist':<60} {'Venue':<20} {'Date':<12}")
print("-" * 95)
for artist, venue, date in results:
    print(f"{artist:<60} {venue:<20} {date:<12}")
print(f"\nTotal: {len(results)} shows without video preview")
