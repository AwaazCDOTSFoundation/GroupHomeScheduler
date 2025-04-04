from .config import TimeOffConfig
import os
import re
from datetime import datetime

def get_shift(shifts, date, caregiver_name):
    """Helper function to find shift for a caregiver on a specific date"""
    name_mappings = {
        'Maria B.': 'MB'
    }
    search_name = name_mappings.get(caregiver_name, caregiver_name)

    # First check if caregiver has time off
    if caregiver_name in TimeOffConfig.SCHEDULE and date in TimeOffConfig.SCHEDULE[caregiver_name]:
        # Return special "time-off" indicator
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
    'Maria B.': '#90EE90',    # Light green
    'MG': '#98FB98',         # Pale green
    'Amanda': '#87CEEB',      # Sky blue
    'Michelle': '#B0C4DE',    # Light steel blue
    'Teontae': '#DDA0DD',     # Plum
    'Fatima': '#FFB6C1'       # Light pink
}

CAREGIVER_ORDER = [
    'Kisha', 
    'Maria B.', 
    'MG',
    'Amanda', 
    'Michelle', 
    'Teontae', 
    'Fatima'
]

def update_config_file(new_pattern):
    """Update the config.py file with new weekly pattern"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.py')
    
    try:
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
        new_pattern_str = "    WEEKLY_PATTERN = {\n"
        for day, shifts in new_pattern.items():
            new_pattern_str += f"        {day}: {{  # {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][int(day)]}\n"
            for shift_type, caregiver in shifts.items():
                new_pattern_str += f"            '{shift_type}': '{caregiver}',\n"
            new_pattern_str += "        },\n"
        new_pattern_str += "    }"
        
        # Replace the old pattern with the new one
        new_content = content[:pattern_start] + new_pattern_str + content[pattern_end:]
        
        # Write back to the file
        with open(config_path, 'w') as f:
            f.write(new_content)
            
        return True
        
    except Exception as e:
        logger.error(f"Error updating config file: {e}")
        return False 