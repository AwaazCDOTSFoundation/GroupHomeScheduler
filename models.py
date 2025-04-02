from flask_sqlalchemy import SQLAlchemy
from config import ShiftConfig, Config
import logging
import time
import os
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class Caregiver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shifts = db.relationship('Shift', backref='caregiver', lazy=True)

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(3), nullable=False)  # A, B, C, G1, or G2
    caregiver_id = db.Column(db.Integer, db.ForeignKey('caregiver.id'), nullable=False)

    @property
    def time_range(self):
        return ShiftConfig.SHIFTS[self.shift_type]['time']
    
    @property
    def start_hour(self):
        return ShiftConfig.SHIFTS[self.shift_type]['start_hour']
    
    @property
    def duration_hours(self):
        return ShiftConfig.SHIFTS[self.shift_type]['duration']

def init_db(app):
    max_retries = 5  # Increased retries for production
    retry_delay = 5  # Increased delay for production
    
    # Initialize the db with the app
    db.init_app(app)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database initialization (attempt {attempt + 1}/{max_retries})")
            
            with app.app_context():
                # Create all tables if they don't exist
                db.create_all()
                
                # Check if we need to initialize caregivers
                caregiver_count = Caregiver.query.count()
                
                if caregiver_count == 0:
                    logger.info("No caregivers found. Initializing caregivers...")
                    
                    # Initialize caregivers in smaller batches
                    batch_size = 2
                    for i in range(0, len(ShiftConfig.CAREGIVERS), batch_size):
                        batch = ShiftConfig.CAREGIVERS[i:i + batch_size]
                        for name in batch:
                            if not Caregiver.query.filter_by(name=name).first():
                                caregiver = Caregiver(name=name)
                                db.session.add(caregiver)
                        db.session.commit()
                        logger.info(f"Initialized caregivers batch {i//batch_size + 1}")
                    
                    logger.info(f"Successfully initialized {len(ShiftConfig.CAREGIVERS)} caregivers")
                else:
                    logger.info(f"Found {caregiver_count} existing caregivers")
                
                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to initialize database after all retries")
                # In production, we might want to continue running even if initialization fails
                if os.environ.get('RENDER', ''):
                    logger.warning("Continuing despite database initialization failure")
                    return False
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to initialize database after all retries")
                if os.environ.get('RENDER', ''):
                    logger.warning("Continuing despite database initialization failure")
                    return False
                raise 