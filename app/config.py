import os
from datetime import datetime

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change')
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Default SQLite database path
    default_db_path = f'sqlite:///{os.path.join(basedir, "instance", "schedule.db")}'
    
    # Get database URL from environment with SQLite as fallback
    SQLALCHEMY_DATABASE_URI = default_db_path
    if 'DATABASE_URL' in os.environ:
        db_url = os.environ['DATABASE_URL']
        if db_url.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = db_url.replace('postgres://', 'postgresql://')
        else:
            SQLALCHEMY_DATABASE_URI = db_url
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Environment configuration
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Shift types
    SHIFTS = ['Morning', 'Afternoon', 'Night']

class ShiftConfig:
    SHIFTS = {
        'A': {'time': '6:00 AM - 2:00 PM', 'start_hour': 6, 'duration': 8},
        'B': {'time': '4:00 PM - 12:00 AM', 'start_hour': 16, 'duration': 8},
        'C': {'time': '12:00 AM - 8:00 AM', 'start_hour': 0, 'duration': 8},
        'G1': {'time': '12:00 PM - 8:00 PM', 'start_hour': 12, 'duration': 8},
        'G2': {'time': '9:00 AM - 5:00 PM', 'start_hour': 9, 'duration': 8}
    }
    
    WEEKLY_PATTERN = {
    0: {  # Monday
        'C': 'Michelle',
        'A': 'MB',
        'G1': 'Teontae',
        'B': 'Amanda',
    },
    1: {  # Tuesday
        'C': 'Kisha',
        'A': 'Fatima',
        'G1': 'MG',
        'B': 'Michelle',
    },
    2: {  # Wednesday
        'C': 'Amanda',
        'A': 'MB',
        'G1': 'MG',
        'B': 'Kisha',
    },
    3: {  # Thursday
        'C': 'Amanda',
        'A': 'Fatima',
        'G2': 'MB',
        'G1': 'Teontae',
        'B': 'Kisha',
    },
    4: {  # Friday
        'C': 'Amanda',
        'A': 'MB',
        'G2': 'Teontae',
        'G1': 'Kisha',
        'B': 'Fatima',
    },
    5: {  # Saturday
        'C': 'Michelle',
        'A': 'MG',
        'G1': 'Fatima',
        'B': 'Kisha',
    },
    6: {  # Sunday
        'C': 'Amanda',
        'A': 'MG',
        'G2': 'Teontae',
        'G1': 'Michelle',
        'B': 'Fatima',
    },
}
    
    CAREGIVERS = ['CG1', 'CG2', 'CG3', 'CG4', 'CG5', 'CG6', 'CG7', 'CG8']
    SHIFTS_PER_WEEK = 5  # Each caregiver works 5 days
    HOURS_PER_SHIFT = 8  # Each shift is 8 hours
    HOURS_PER_WEEK = 40  # Total weekly hours per caregiver

class TimeOffConfig:
                                                            SCHEDULE = {
        'Michelle': [
            datetime(2025, 4, 13).date(),
            datetime(2025, 4, 19).date(),
            datetime(2025, 4, 20).date(),
        ],
        'Amanda': [
            datetime(2025, 4, 28).date(),
            datetime(2025, 4, 29).date(),
            datetime(2025, 4, 30).date(),
            datetime(2025, 5, 1).date(),
            datetime(2025, 5, 2).date(),
        ],
        'Kisha': [
            datetime(2025, 4, 12).date(),
        ],
    } 