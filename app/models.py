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

class Shift(db.Model):
    __tablename__ = 'shift'
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
        
    @property
    def end_hour(self):
        end = self.start_hour + self.duration_hours
        return end if end < 24 else end - 24  # Handle overnight shifts 

    @classmethod
    def clear_schedule(cls, start_date, end_date):
        """Clear all shifts between start_date and end_date"""
        try:
            deleted = cls.query.filter(
                cls.date >= start_date,
                cls.date <= end_date
            ).delete()
            db.session.commit()
            return deleted
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing schedule: {e}")
            return 0

    @classmethod
    def update_config_pattern(cls):
        """Update ShiftConfig.WEEKLY_PATTERN based on current schedule"""
        # Get a week's worth of shifts
        start_date = datetime(2025, 4, 7)  # Use a reference week
        end_date = start_date + timedelta(days=6)
        
        shifts = cls.query.filter(
            cls.date >= start_date,
            cls.date <= end_date
        ).join(Caregiver).all()
        
        new_pattern = {i: {} for i in range(7)}  # 0-6 for Monday-Sunday
        
        for shift in shifts:
            weekday = shift.date.weekday()
            new_pattern[weekday][shift.shift_type] = shift.caregiver.name
            
        return new_pattern

class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @classmethod
    def refresh_monthly_data(cls):
        """Force refresh of monthly schedule data"""
        try:
            # Clear any cached data
            db.session.commit()
            # Signal any listeners that data has changed
            db.session.expire_all()
            # Update last_updated timestamp
            schedule = cls.query.first()
            if not schedule:
                schedule = cls()
            schedule.last_updated = datetime.utcnow()
            db.session.add(schedule)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error refreshing monthly data: {e}")
            return False 

class TimeOff(db.Model):
    __tablename__ = 'time_off'
    id = db.Column(db.Integer, primary_key=True)
    caregiver_id = db.Column(db.Integer, db.ForeignKey('caregiver.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200))

    @classmethod
    def get_all_time_off(cls):
        """Get all time off entries grouped by caregiver name"""
        time_offs = cls.query.join(Caregiver).all()
        result = {}
        for time_off in time_offs:
            if time_off.caregiver.name not in result:
                result[time_off.caregiver.name] = []
            # Add all dates between start_date and end_date
            current_date = time_off.start_date
            while current_date <= time_off.end_date:
                result[time_off.caregiver.name].append(current_date)
                current_date += timedelta(days=1)
        return result 

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