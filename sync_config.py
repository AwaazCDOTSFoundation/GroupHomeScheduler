from app import create_app
from app.utils import ensure_sync

app = create_app()

with app.app_context():
    if ensure_sync():
        print("Successfully synced database and config files")
    else:
        print("Failed to sync database and config files") 