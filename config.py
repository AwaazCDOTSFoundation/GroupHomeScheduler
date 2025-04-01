import os

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///schedule.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Environment configuration
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Shift types
    SHIFTS = ['Morning', 'Afternoon', 'Night']

class ShiftConfig:
    SHIFTS = {
        'A': {'name': 'A Shift', 'time': '6:00 AM - 2:00 PM', 'start_hour': 6, 'duration': 8, 'color': '#90EE90'},
        'B': {'name': 'B Shift', 'time': '4:00 PM - 12:00 AM', 'start_hour': 16, 'duration': 8, 'color': '#87CEEB'},
        'C': {'name': 'C Shift', 'time': '12:00 AM - 8:00 AM', 'start_hour': 0, 'duration': 8, 'color': '#DDA0DD'},
        'G1': {'name': 'G1 Shift', 'time': '12:00 PM - 8:00 PM', 'start_hour': 12, 'duration': 8, 'color': '#F0E68C'},
        'G2': {'name': 'G2 Shift', 'time': '9:00 AM - 5:00 PM', 'start_hour': 9, 'duration': 8, 'color': '#FFB6C1'}
    }
    
    CAREGIVERS = ['CG1', 'CG2', 'CG3', 'CG4', 'CG5', 'CG6', 'CG7', 'CG8']
    SHIFTS_PER_WEEK = 5  # Each caregiver works 5 days
    HOURS_PER_SHIFT = 8  # Each shift is 8 hours
    HOURS_PER_WEEK = 40  # Total weekly hours per caregiver 