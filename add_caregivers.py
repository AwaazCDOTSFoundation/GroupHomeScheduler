from app import db, create_app
from app.models import Caregiver

def add_caregivers():
    app = create_app()
    with app.app_context():
        caregivers = ['Amanda', 'Fatima', 'Kisha', 'MB', 'MG', 'Michelle', 'Teontae']
        for name in caregivers:
            if not Caregiver.query.filter_by(name=name).first():
                db.session.add(Caregiver(name=name))
        db.session.commit()
        print('Caregivers:', [c.name for c in Caregiver.query.all()])

if __name__ == '__main__':
    add_caregivers() 