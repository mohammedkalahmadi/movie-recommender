
# Movie Recommendation Website – v2 (Enhanced UI + Easy Sharing)

## What’s new
- Modern UI (navbar, hero section, toasts, loading spinner, keyboard shortcuts, a11y labels)
- Robust caching (no Parquet dependency)
- Simple steps to share on your local network or deploy to the internet

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app/app.py
flask run --port 5000
```
Open http://127.0.0.1:5000

## Share on your LAN (same Wi‑Fi)
```bash
export FLASK_APP=app/app.py
flask run --host 0.0.0.0 --port 5000
```
Find your Mac’s IP (e.g., 192.168.1.20) and ask others on the same Wi‑Fi to open:
`http://<YOUR_IP>:5000`

## Production options (quick)
- **Render**: create a Web Service, build command `pip install -r requirements.txt`, start command `gunicorn app.app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
- **Railway/Heroku**: similar start command with Gunicorn.
- **Azure App Service**: use the same Gunicorn command and configure `WEBSITES_PORT`.

Add a `Procfile` (for platforms that use it):
```
web: gunicorn app.app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT
```

For Nginx reverse proxy, point to `127.0.0.1:5000` and enable gzip and caching for `/static/`.
