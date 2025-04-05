from .config import TimeOffConfig, ShiftConfig
import os
import re
from datetime import datetime, timedelta
from .models import db, Shift, Caregiver, TimeOff
import logging

logger = logging.getLogger(__name__)

def get_shift(shifts, date, caregiver_name):
    """Helper function to find shift for a caregiver on a specific date"""
    name_mappings = {
        'MB': 'MB',
        'Maria B.': 'MB'
    }
    search_name = name_mappings.get(caregiver_name, caregiver_name)

    # First check if caregiver has time off from database
    caregiver = Caregiver.query.filter_by(name=search_name).first()
    if caregiver:
        time_off = TimeOff.query.filter(
            TimeOff.caregiver_id == caregiver.id,
            TimeOff.start_date <= date,
            TimeOff.end_date >= date
        ).first()
        if time_off:
            for shift in shifts:
                if shift.date == date and shift.caregiver.name == search_name:
                    return {'shift_type': shift.shift_type, 'time_off': True}
            return None

    for shift in shifts:
        if shift.date == date and shift.caregiver.name == search_name:
            return {'shift_type': shift.shift_type, 'time_off': False}
    return None

# Constants for the schedule
CAREGIVER_COLORS = {
    'Kisha': '#FFB6C1',      # Light pink
    'MB': '#90EE90',         # Light green
    'MG': '#98FB98',         # Pale green
    'Amanda': '#87CEEB',      # Sky blue
    'Michelle': '#B0C4DE',    # Light steel blue
    'Teontae': '#DDA0DD',     # Plum
    'Fatima': '#FFB6C1'       # Light pink
}

CAREGIVER_ORDER = [
    'Kisha', 
    'MB', 
    'MG',
    'Amanda', 
    'Michelle', 
    'Teontae', 
    'Fatima'
]

def update_config_file(new_pattern):
    """Update the config.py file with new weekly pattern"""
    try:
        # Get the absolute path to the config file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config.py')
        
        # Read the current config file
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Find the WEEKLY_PATTERN section
        pattern_start = content.find('WEEKLY_PATTERN = {')
        if pattern_start == -1:
            raise ValueError("Could not find WEEKLY_PATTERN in config file")
            
        # Find the end of the pattern (counting braces)
        brace_count = 0
        pattern_end = pattern_start
        in_pattern = False
        
        for i, char in enumerate(content[pattern_start:]):
            if char == '{':
                brace_count += 1
                in_pattern = True
            elif char == '}':
                brace_count -= 1
                if in_pattern and brace_count == 0:
                    pattern_end = pattern_start + i + 1
                    break
        
        # Format the new pattern
        new_pattern_str = "WEEKLY_PATTERN = {\n"
        for day, shifts in new_pattern.items():
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][int(day)]
            new_pattern_str += f"    {day}: {{  # {day_name}\n"
            for shift_type, caregiver in shifts.items():
                new_pattern_str += f"        '{shift_type}': '{caregiver}',\n"
            new_pattern_str += "    },\n"
        new_pattern_str += "}"
        
        # Replace the old pattern with the new one
        new_content = content[:pattern_start] + new_pattern_str + content[pattern_end:]
        
        # Create a backup of the current config file
        backup_path = config_path + '.bak'
        with open(backup_path, 'w') as f:
            f.write(content)
        
        # Write the new content
        with open(config_path, 'w') as f:
            f.write(new_content)
            
        # Verify the new content was written correctly
        with open(config_path, 'r') as f:
            written_content = f.read()
            if new_pattern_str not in written_content:
                # Restore from backup if verification fails
                with open(backup_path, 'r') as backup:
                    with open(config_path, 'w') as f:
                        f.write(backup.read())
                raise ValueError("Failed to verify new content was written correctly")
            
        # Remove the backup file if everything succeeded
        os.remove(backup_path)
        return True
        
    except Exception as e:
        print(f"Error updating config file: {str(e)}")
        return False 

def sync_db_to_config():
    """Sync the current database state to the config file"""
    try:
        # Get the current week's pattern from the database
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        end_date = start_date + timedelta(days=6)  # End on Sunday
        
        # Get all shifts for the current week
        shifts = Shift.query.filter(
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
        
        # Create a new pattern dictionary
        new_pattern = {}
        for day in range(7):
            current_date = start_date + timedelta(days=day)
            day_shifts = {}
            
            for shift in shifts:
                if shift.date == current_date:
                    day_shifts[shift.shift_type] = shift.caregiver.name
            
            new_pattern[day] = day_shifts
        
        # Update the config file
        if update_config_file(new_pattern):
            logger.info("Successfully synced database to config file")
            return True
        else:
            logger.error("Failed to sync database to config file")
            return False
            
    except Exception as e:
        logger.error(f"Error syncing database to config: {str(e)}")
        return False

def sync_config_to_db():
    """Sync the config file state to the database"""
    try:
        # Get the current week's pattern from config
        weekly_pattern = ShiftConfig.WEEKLY_PATTERN
        
        # Get the current week's dates
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        end_date = start_date + timedelta(days=6)  # End on Sunday
        
        # Delete existing shifts for this week
        Shift.query.filter(
            Shift.date >= start_date,
            Shift.date <= end_date
        ).delete()
        
        # Create new shifts based on config
        for day, shifts in weekly_pattern.items():
            current_date = start_date + timedelta(days=int(day))
            
            for shift_type, caregiver_name in shifts.items():
                # Get or create caregiver
                caregiver = Caregiver.query.filter_by(name=caregiver_name).first()
                if not caregiver:
                    caregiver = Caregiver(name=caregiver_name)
                    db.session.add(caregiver)
                    db.session.commit()
                
                # Create new shift
                new_shift = Shift(
                    date=current_date,
                    shift_type=shift_type,
                    caregiver_id=caregiver.id
                )
                db.session.add(new_shift)
        
        db.session.commit()
        logger.info("Successfully synced config to database")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing config to database: {str(e)}")
        return False

def sync_time_off_to_config():
    """Sync time off from database to config file"""
    try:
        # Get all time off records from database
        time_off_dict = TimeOff.get_all_time_off()
        
        # Format the new time off schedule
        new_schedule = "    SCHEDULE = {\n"
        for caregiver_name, dates in time_off_dict.items():
            if dates:  # Only include caregivers with time off
                new_schedule += f"        '{caregiver_name}': [\n"
                for date in sorted(dates):
                    new_schedule += f"            datetime({date.year}, {date.month}, {date.day}).date(),\n"
                new_schedule += "        ],\n"
        new_schedule += "    }"
        
        # Update the config file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config.py')
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Find the TimeOffConfig class and its SCHEDULE
        time_off_start = content.find('class TimeOffConfig:')
        if time_off_start == -1:
            raise ValueError("Could not find TimeOffConfig in config file")
            
        schedule_start = content.find('SCHEDULE = {', time_off_start)
        if schedule_start == -1:
            raise ValueError("Could not find SCHEDULE in TimeOffConfig")
            
        # Find the end of the schedule
        brace_count = 0
        schedule_end = schedule_start
        in_schedule = False
        
        for i, char in enumerate(content[schedule_start:]):
            if char == '{':
                brace_count += 1
                in_schedule = True
            elif char == '}':
                brace_count -= 1
                if in_schedule and brace_count == 0:
                    schedule_end = schedule_start + i + 1
                    break
        
        # Replace the old schedule with the new one
        new_content = content[:schedule_start] + new_schedule + content[schedule_end:]
        
        # Create a backup
        backup_path = config_path + '.bak'
        with open(backup_path, 'w') as f:
            f.write(content)
        
        # Write the new content
        with open(config_path, 'w') as f:
            f.write(new_content)
            
        # Verify the write
        with open(config_path, 'r') as f:
            if new_schedule not in f.read():
                # Restore from backup
                with open(backup_path, 'r') as backup:
                    with open(config_path, 'w') as f:
                        f.write(backup.read())
                raise ValueError("Failed to verify new content was written correctly")
        
        # Remove backup
        os.remove(backup_path)
        logger.info("Successfully synced time off to config")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing time off to config: {str(e)}")
        return False

def sync_time_off_from_config():
    """Sync time off from config to database"""
    try:
        # Get current time off from config
        config_schedule = TimeOffConfig.SCHEDULE
        
        # For each caregiver in config
        for caregiver_name, dates in config_schedule.items():
            # Get or create caregiver
            caregiver = Caregiver.query.filter_by(name=caregiver_name).first()
            if not caregiver:
                caregiver = Caregiver(name=caregiver_name)
                db.session.add(caregiver)
                db.session.commit()
            
            # Group consecutive dates
            if dates:
                dates = sorted(dates)
                date_ranges = []
                range_start = dates[0]
                prev_date = dates[0]
                
                for date in dates[1:]:
                    if (date - prev_date).days > 1:
                        date_ranges.append((range_start, prev_date))
                        range_start = date
                    prev_date = date
                date_ranges.append((range_start, prev_date))
                
                # Add time off records for each range
                for start_date, end_date in date_ranges:
                    # Check if record already exists
                    existing = TimeOff.query.filter_by(
                        caregiver_id=caregiver.id,
                        start_date=start_date,
                        end_date=end_date
                    ).first()
                    
                    if not existing:
                        time_off = TimeOff(
                            caregiver_id=caregiver.id,
                            start_date=start_date,
                            end_date=end_date
                        )
                        db.session.add(time_off)
        
        db.session.commit()
        logger.info("Successfully synced time off from config")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing time off from config: {str(e)}")
        return False

def ensure_sync():
    """Ensure database and config are in sync"""
    try:
        # First sync config to db to ensure we have the latest config state
        if not sync_config_to_db():
            logger.error("Failed to sync config to database")
            return False
            
        # Sync time off from config to database
        if not sync_time_off_from_config():
            logger.error("Failed to sync time off from config to database")
            return False
            
        # Then sync db to config to ensure any changes are preserved
        if not sync_db_to_config():
            logger.error("Failed to sync database to config")
            return False
            
        # Finally sync time off from database to config
        if not sync_time_off_to_config():
            logger.error("Failed to sync time off from database to config")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring sync: {str(e)}")
        return False 