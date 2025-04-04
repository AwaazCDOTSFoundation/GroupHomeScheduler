from flask_sqlalchemy import SQLAlchemy
from .config import ShiftConfig, TimeOffConfig
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from . import db

class Caregiver(db.Model):
    __tablename__ = 'caregiver'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shifts = db.relationship('Shift', backref='caregiver', lazy=True)

    def __repr__(self):
        return f'<Caregiver {self.name}>'

class Shift(db.Model):
    __tablename__ = 'shift'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(10), nullable=False)  # A, B, C, G1, G2
    caregiver_id = db.Column(db.Integer, db.ForeignKey('caregiver.id'), nullable=False)
    
    @property
    def start_hour(self):
        shift_hours = {
            'A': 6,   # 6 AM
            'B': 16,  # 4 PM
            'C': 0,   # 12 AM
            'G1': 12, # 12 PM
            'G2': 9   # 9 AM
        }
        return shift_hours.get(self.shift_type, 0)
    
    @property
    def end_hour(self):
        return (self.start_hour + 8) % 24
    
    @property
    def duration_hours(self):
        return 8
    
    @property
    def time_range(self):
        start = f"{self.start_hour:02d}:00"
        end = f"{self.end_hour:02d}:00"
        return f"{start}-{end}"

    def __repr__(self):
        return f'<Shift {self.date} {self.shift_type} {self.caregiver.name}>'

class TimeOff(db.Model):
    __tablename__ = 'time_off'
    id = db.Column(db.Integer, primary_key=True)
    caregiver_id = db.Column(db.Integer, db.ForeignKey('caregiver.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200))
    category = db.Column(db.String(50), nullable=False, default='vacation')  # vacation, sick, personal, etc.
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    caregiver = db.relationship('Caregiver', backref='time_off')
    
    @staticmethod
    def get_all_time_off():
        """Get all time off records grouped by caregiver"""
        time_off_records = TimeOff.query.all()
        time_off_dict = {}
        
        for record in time_off_records:
            if record.caregiver.name not in time_off_dict:
                time_off_dict[record.caregiver.name] = []
            
            # Add all dates in the range
            current_date = record.start_date
            while current_date <= record.end_date:
                time_off_dict[record.caregiver.name].append(current_date)
                current_date += timedelta(days=1)
        
        return time_off_dict

    def __repr__(self):
        return f'<TimeOff {self.caregiver.name} {self.start_date} to {self.end_date} ({self.status})>'

def initialize_time_off():
    """Initialize time off data from config if database is empty"""
    if TimeOff.query.count() == 0:
        for caregiver_name, dates in TimeOffConfig.SCHEDULE.items():
            caregiver = Caregiver.query.filter_by(name=caregiver_name).first()
            if caregiver:
                for date in dates:
                    time_off = TimeOff(
                        caregiver_id=caregiver.id,
                        start_date=date,
                        end_date=date
                    )
                    db.session.add(time_off)
        db.session.commit() 