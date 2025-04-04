from app import create_app, db
from app.models import TimeOff, Caregiver
from datetime import datetime

app = create_app()

with app.app_context():
    # Find Kisha's time off record for April 12, 2025
    kisha = Caregiver.query.filter_by(name='Kisha').first()
    if kisha:
        time_off = TimeOff.query.filter_by(
            caregiver_id=kisha.id,
            start_date=datetime(2025, 4, 12).date(),
            end_date=datetime(2025, 4, 12).date()
        ).first()
        
        if time_off:
            # Delete the time off record
            db.session.delete(time_off)
            db.session.commit()
            print("Successfully removed Kisha's time off for April 12, 2025")
        else:
            print("No time off record found for Kisha on April 12, 2025")
    else:
        print("Caregiver Kisha not found in database") 