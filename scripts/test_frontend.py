"""Test frontend pages load correctly."""
import urllib.request
import time
import sys

pages = ['/', '/dashboard', '/market-calendar', '/heatmap',
         '/sky-history', '/leaderboard', '/portfolio', '/birth-chart',
         '/health', '/auth']

all_ok = True
for p in pages:
    try:
        t = time.time()
        r = urllib.request.urlopen('http://127.0.0.1:5173' + p, timeout=10)
        lat = round((time.time() - t) * 1000)
        print(f'  {r.status} {p}  {lat}ms')
    except Exception as e:
        print(f'  FAIL {p}: {e}')
        all_ok = False

sys.exit(0 if all_ok else 1)