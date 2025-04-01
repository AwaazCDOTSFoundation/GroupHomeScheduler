from datetime import datetime, timedelta
from .models import db, Caregiver, Shift
from . import create_app
import random

class ScheduleConstraints:
    def __init__(self):
        self.shifts_per_week = 5  # Each caregiver works 5 days
        self.hours_per_shift = 8  # Each shift is 8 hours
        self.hours_per_week = 40  # Total weekly hours per caregiver

def get_caregiver_weekly_shifts(caregiver, start_date, end_date):
    return Shift.query.filter(
        Shift.caregiver_id == caregiver.id,
        Shift.date >= start_date,
        Shift.date < end_date
    ).count()

def get_least_scheduled_caregivers(caregivers, used_today, start_date, end_date, count=1):
    available = []
    shift_counts = {}
    
    for cg in caregivers:
        if cg.id not in used_today:
            shifts = get_caregiver_weekly_shifts(cg, start_date, end_date)
            shift_counts[cg] = shifts
            if shifts < 5:  # Max 5 shifts per week
                available.append(cg)
    
    # Sort by number of shifts (least to most)
    available.sort(key=lambda x: shift_counts[x])
    return available[:count] if count > 1 else available[0] if available else None

def generate_schedule(start_date, num_weeks=1):
    # Clear existing shifts
    Shift.query.delete()
    db.session.commit()

    constraints = ScheduleConstraints()
    caregivers = Caregiver.query.all()
    current_date = start_date
    end_date = start_date + timedelta(days=7)

    # Pre-calculate required shifts for the week
    total_shifts = {
        'A': 7,   # 1 per day * 7 days
        'B': 12,  # 2 per day * 6 days (no Saturday)
        'C': 7,   # 1 per day * 7 days
        'G': 14   # 2 per day * 7 days
    }

    for day in range(7):
        used_caregivers_today = set()
        
        # Assign A shift (1 caregiver)
        cg = get_least_scheduled_caregivers(caregivers, used_caregivers_today, start_date, end_date)
        if cg:
            used_caregivers_today.add(cg.id)
            shift = Shift(date=current_date, shift_type='A', caregiver=cg)
            db.session.add(shift)

        # Assign G shift (2 caregivers)
        for _ in range(2):
            cg = get_least_scheduled_caregivers(caregivers, used_caregivers_today, start_date, end_date)
            if cg:
                used_caregivers_today.add(cg.id)
                shift = Shift(date=current_date, shift_type='G', caregiver=cg)
                db.session.add(shift)

        # Assign B shift (2 caregivers, except Saturday)
        if current_date.weekday() != 5:  # Not Saturday
            for _ in range(2):
                cg = get_least_scheduled_caregivers(caregivers, used_caregivers_today, start_date, end_date)
                if cg:
                    used_caregivers_today.add(cg.id)
                    shift = Shift(date=current_date, shift_type='B', caregiver=cg)
                    db.session.add(shift)

        # Assign C shift (1 caregiver)
        cg = get_least_scheduled_caregivers(caregivers, used_caregivers_today, start_date, end_date)
        if cg:
            used_caregivers_today.add(cg.id)
            shift = Shift(date=current_date, shift_type='C', caregiver=cg)
            db.session.add(shift)

        current_date += timedelta(days=1)
        db.session.commit()  # Commit after each day to maintain consistency

    # Validate and fix any missing shifts
    fix_missing_shifts(start_date)
    print("Schedule generation completed. Validating schedule...")
    validate_schedule(start_date)

def fix_missing_shifts(start_date):
    end_date = start_date + timedelta(days=7)
    current_date = start_date
    
    for day in range(7):
        # Check each shift type
        for shift_type in ['A', 'G', 'B', 'C']:
            if shift_type == 'B' and current_date.weekday() == 5:  # Skip B shift on Saturday
                continue
                
            expected_count = 2 if shift_type in ['G', 'B'] else 1
            actual_shifts = Shift.query.filter(
                Shift.date == current_date,
                Shift.shift_type == shift_type
            ).count()
            
            if actual_shifts < expected_count:
                # Find caregivers with less than 5 shifts who aren't working this day
                used_today = set(s.caregiver_id for s in Shift.query.filter(Shift.date == current_date).all())
                available = []
                
                for cg in Caregiver.query.all():
                    if (cg.id not in used_today and 
                        get_caregiver_weekly_shifts(cg, start_date, end_date) < 5):
                        available.append(cg)
                
                # Assign missing shifts
                for _ in range(expected_count - actual_shifts):
                    if available:
                        cg = min(available, key=lambda x: get_caregiver_weekly_shifts(x, start_date, end_date))
                        available.remove(cg)
                        shift = Shift(date=current_date, shift_type=shift_type, caregiver=cg)
                        db.session.add(shift)
                        
        current_date += timedelta(days=1)
    db.session.commit()

def validate_schedule(start_date):
    caregivers = Caregiver.query.all()
    end_date = start_date + timedelta(days=7)

    print("\nSchedule Validation Report:")
    print("-" * 50)
    
    for caregiver in caregivers:
        weekly_shifts = get_caregiver_weekly_shifts(caregiver, start_date, end_date)
        weekly_hours = weekly_shifts * 8
        
        print(f"\n{caregiver.name}:")
        print(f"Weekly Shifts: {weekly_shifts}/5")
        print(f"Weekly Hours: {weekly_hours}/40")
        
        if weekly_hours != 40:
            print(f"WARNING: {caregiver.name} has {weekly_hours} hours instead of 40")
        if weekly_shifts > 5:
            print(f"WARNING: {caregiver.name} has {weekly_shifts} shifts (more than 5 days/week)")

    # Print shift distribution
    print("\nShift Distribution:")
    print("-" * 50)
    current = start_date
    for day in range(7):
        print(f"\n{current.strftime('%A')}:")
        for shift_type in ['A', 'G', 'B', 'C']:
            shifts = Shift.query.filter(
                Shift.date == current,
                Shift.shift_type == shift_type
            ).all()
            print(f"{shift_type} Shift: {', '.join(s.caregiver.name for s in shifts)}")
        current += timedelta(days=1)

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        start_date = datetime.now().date()
        start_date = start_date - timedelta(days=start_date.weekday())  # Start from Monday
        generate_schedule(start_date) 