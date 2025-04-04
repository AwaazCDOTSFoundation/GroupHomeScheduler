import os
from app import create_app, db
from app.models import Caregiver, Shift, TimeOff
from app.config import ShiftConfig
from app.utils import ensure_sync
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = create_app()

def initialize_database():
    with app.app_context():
        logger.debug("Creating database tables...")
        db.create_all()
        
        # Initialize caregivers if none exist
        if Caregiver.query.count() == 0:
            logger.debug("Initializing caregivers...")
            for name in ShiftConfig.CAREGIVERS:
                caregiver = Caregiver(name=name)
                db.session.add(caregiver)
            db.session.commit()
            logger.debug(f"Added {len(ShiftConfig.CAREGIVERS)} caregivers")
            
        # Ensure database and config are in sync
        logger.debug("Syncing database and config...")
        if ensure_sync():
            logger.debug("Successfully synced database and config")
        else:
            logger.error("Failed to sync database and config")

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=5001) 