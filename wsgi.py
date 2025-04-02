import os
import sys
import logging
from datetime import datetime, timedelta

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Caregiver, Shift

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

def initialize_database():
    """Initialize database with caregivers and shifts."""
    try:
        logger.debug("Creating database tables...")
        db.create_all()
        
        # Clear existing data
        logger.debug("Clearing existing data...")
        Shift.query.delete()
        Caregiver.query.delete()
        db.session.commit()
        
        # Create caregivers with exact names
        logger.debug("Creating caregivers...")
        caregivers = [
            'MB', 'Teontae', 'MG', 'Amanda', 'Michelle', 'Fatima', 'Kisha'
        ]
        for name in caregivers:
            caregiver = Caregiver(name=name)
            db.session.add(caregiver)
        db.session.commit()
        logger.debug("Caregivers created successfully")
        
        # Create shifts for April-May 2025
        logger.debug("Creating shifts for April-May 2025...")
        # Define the weekly pattern
        weekly_pattern = {
            0: {  # Monday
                'A': 'MB',
                'G1': 'Teontae',
                'G2': 'MG',
                'B': 'Amanda',  # Will be skipped for 4/28
                'C': 'Michelle'
            },
            1: {  # Tuesday
                'A': 'Fatima',
                'G1': 'MG',
                'G2': 'Teontae',
                'B': 'Michelle',
                'C': 'Kisha'
            },
            2: {  # Wednesday
                'A': 'MB',
                'G1': 'MG',
                'G2': 'Teontae',
                'B': 'Kisha',
                'C': 'Amanda'  # Will be skipped for 4/30
            },
            3: {  # Thursday
                'A': 'Fatima',
                'G1': 'MB',
                'G2': 'Teontae',
                'B': 'Kisha',
                'C': 'Amanda'  # Will be skipped for 5/1
            },
            4: {  # Friday
                'A': 'MB',
                'G1': 'Kisha',
                'G2': 'Teontae',
                'B': 'Fatima',
                'C': 'Amanda'  # Will be skipped for 5/2
            },
            5: {  # Saturday
                'A': 'MG',
                'G2': 'Teontae',
                'G1': 'Fatima',
                'B': 'Kisha',
                'C': 'Michelle'
            },
            6: {  # Sunday
                'A': 'MG',
                'G2': 'Teontae',
                'G1': 'Michelle',
                'B': 'Fatima',
                'C': 'Amanda'
            }
        }

        # Get all caregivers
        caregivers = {c.name: c.id for c in Caregiver.query.all()}
        
        # Create shifts from April 7th to May 31st, 2025
        current_date = datetime(2025, 4, 7)
        end_date = datetime(2025, 5, 31)

        while current_date <= end_date:
            # Get the day pattern based on weekday
            day_pattern = weekly_pattern[current_date.weekday()]
            
            for shift_type, caregiver_name in day_pattern.items():
                # Skip Amanda's shifts during her time off
                if (caregiver_name == 'Amanda' and 
                    datetime(2025, 4, 28) <= current_date <= datetime(2025, 5, 2)):
                    continue
                
                new_shift = Shift(
                    date=current_date.date(),
                    shift_type=shift_type,
                    caregiver_id=caregivers[caregiver_name]
                )
                db.session.add(new_shift)
            
            current_date += timedelta(days=1)

        db.session.commit()
        logger.debug("Shifts created successfully")
            
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        db.session.rollback()
        raise

# Initialize database on startup
with app.app_context():
    initialize_database()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 