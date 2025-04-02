from app import create_app, db
from app.models import Caregiver, Shift
from datetime import datetime, timedelta

def init_db():
    app = create_app()
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Add caregivers if they don't exist
        caregivers = ['Amanda', 'Fatima', 'Kisha', 'MB', 'MG', 'Michelle', 'Teontae']
        for name in caregivers:
            if not Caregiver.query.filter_by(name=name).first():
                db.session.add(Caregiver(name=name))
        db.session.commit()
        
        print("Caregivers added successfully!")
        print("Current caregivers:", [c.name for c in Caregiver.query.all()])

if __name__ == '__main__':
    init_db() 