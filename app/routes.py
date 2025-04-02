from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
from dateutil.rrule import rrule, DAILY
from .models import Caregiver, Shift, db
from .config import ShiftConfig
from .google_calendar import sync_shifts_to_calendar
import logging
import traceback
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)
views = Blueprint('views', __name__)

@views.route('/')
def index():
    try:
        logger.debug("Rendering index page")
        return render_template('index.html')
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in index route: {e}\nTraceback:\n{error_traceback}")
        raise

@views.route('/calendar')
def calendar_view():
    try:
        logger.debug("Processing calendar view request")
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        dates = list(rrule(DAILY, count=7, dtstart=start_date))
        
        shifts = Shift.query.filter(
            Shift.date >= start_date,
            Shift.date < start_date + timedelta(days=7)
        ).order_by(Shift.date, Shift.shift_type).all()
        
        logger.debug(f"Found {len(shifts)} shifts for the week")
        return render_template('calendar.html', dates=dates, shifts=shifts)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in calendar view: {e}\nTraceback:\n{error_traceback}")
        raise

@views.route('/hourly')
def hourly_view():
    try:
        logger.debug("Processing hourly view request")
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        dates = list(rrule(DAILY, count=7, dtstart=start_date))
        
        # Get all shifts for the week
        shifts = Shift.query.filter(
            Shift.date >= start_date,
            Shift.date < start_date + timedelta(days=7)
        ).join(Caregiver).order_by(Shift.date, Shift.shift_type).all()
        
        logger.debug(f"Found {len(shifts)} shifts for the week")
        return render_template('hourly.html', dates=dates, shifts=shifts)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in hourly view: {e}\nTraceback:\n{error_traceback}")
        return render_template('error.html', error=str(e)), 500

@views.route('/monthly')
def monthly_view():
    try:
        logger.debug("Processing monthly view request")
        # Get the requested month from query parameters, default to April 2025
        month = request.args.get('month', type=int, default=4)  # Default to April
        year = request.args.get('year', type=int, default=2025)  # Default to 2025
        
        # Create a date object for the first day of the month
        first_day = datetime(year, month, 1)
        
        # Get the last day of the month
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Get all dates in the month
        dates = list(rrule(DAILY, dtstart=first_day, until=last_day))
        
        # Get shifts only from April 7th onwards for April 2025
        schedule_start = datetime(2025, 4, 7)
        
        # For months other than April 2025, show all shifts
        if year != 2025 or month != 4:
            schedule_start = first_day
            
        shifts = Shift.query.join(Caregiver).filter(
            Shift.date >= schedule_start.date(),
            Shift.date <= last_day.date()
        ).order_by(Shift.date, Shift.shift_type).all()
        
        logger.debug(f"Found {len(shifts)} shifts for the month")
        
        # Get all months for the dropdown
        months = []
        for i in range(1, 13):
            date = datetime(2025, i, 1)  # Use 2025 as the year
            months.append({
                'value': i,
                'name': date.strftime('%B'),
                'selected': i == month
            })
        
        return render_template('monthly.html', 
                             dates=dates, 
                             shifts=shifts,
                             months=months,
                             current_month=month,
                             current_year=year,
                             schedule_start=schedule_start.date())  # Pass schedule_start to template
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in monthly view: {e}\nTraceback:\n{error_traceback}")
        return render_template('error.html', error=str(e)), 500

@views.route('/caregivers')
def caregiver_view():
    try:
        logger.debug("Processing caregiver view request")
        caregivers = Caregiver.query.all()
        logger.debug(f"Found {len(caregivers)} caregivers")
        
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        end_date = start_date + timedelta(days=7)  # One week
        
        # Get shifts for the current week
        shifts = Shift.query.filter(
            Shift.date >= start_date,
            Shift.date < end_date
        ).order_by(Shift.date, Shift.shift_type).all()
        
        logger.debug(f"Found {len(shifts)} shifts for the week")
        
        # Create a week schedule
        week_dates = list(rrule(DAILY, count=7, dtstart=start_date))
        
        return render_template('caregivers.html', 
                             caregivers=caregivers,
                             week_dates=week_dates,
                             shifts=shifts,
                             shift_types=ShiftConfig.SHIFTS)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in caregiver view: {e}\nTraceback:\n{error_traceback}")
        raise

@views.route('/add_shift', methods=['POST'])
def add_shift():
    try:
        logger.debug("Processing add shift request")
        caregiver_id = request.form.get('caregiver_id')
        shift_type = request.form.get('shift_type')
        date_str = request.form.get('date')
        
        logger.debug(f"Received request to add shift: caregiver_id={caregiver_id}, shift_type={shift_type}, date={date_str}")
        
        if not all([caregiver_id, shift_type, date_str]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Convert date string to date object
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Check if shift already exists
        existing_shift = Shift.query.filter_by(
            date=date,
            shift_type=shift_type
        ).first()
        
        if existing_shift:
            return jsonify({'error': 'Shift already assigned'}), 400
            
        # Check if shift type is valid
        if shift_type not in ShiftConfig.SHIFTS:
            return jsonify({'error': 'Invalid shift type'}), 400
            
        # Create new shift
        new_shift = Shift(
            date=date,
            shift_type=shift_type,
            caregiver_id=caregiver_id
        )
        
        db.session.add(new_shift)
        db.session.commit()
        logger.debug("Successfully added new shift")
        
        return jsonify({'message': 'Shift added successfully'})
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error adding shift: {e}\nTraceback:\n{error_traceback}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@views.route('/remove_shift', methods=['POST'])
def remove_shift():
    try:
        logger.debug("Processing remove shift request")
        shift_id = request.form.get('shift_id')
        if not shift_id:
            return jsonify({'error': 'Missing shift ID'}), 400
            
        shift = Shift.query.get(shift_id)
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404
            
        db.session.delete(shift)
        db.session.commit()
        logger.debug(f"Successfully removed shift with ID {shift_id}")
        
        return jsonify({'message': 'Shift removed successfully'})
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error removing shift: {e}\nTraceback:\n{error_traceback}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@views.route('/manage-caregivers')
def manage_caregivers():
    try:
        caregivers = Caregiver.query.order_by(Caregiver.id).all()
        return render_template('manage_caregivers.html', caregivers=caregivers)
    except Exception as e:
        logger.error(f"Error in manage_caregivers route: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API endpoints for caregiver management
@views.route('/api/caregivers', methods=['POST'])
def add_caregiver():
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
            
        caregiver = Caregiver(name=name)
        db.session.add(caregiver)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Caregiver added successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding caregiver: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@views.route('/api/caregivers/<int:caregiver_id>', methods=['PUT'])
def update_caregiver(caregiver_id):
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
            
        caregiver = Caregiver.query.get_or_404(caregiver_id)
        caregiver.name = name
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Caregiver updated successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating caregiver: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@views.route('/api/caregivers/<int:caregiver_id>', methods=['DELETE'])
def delete_caregiver(caregiver_id):
    try:
        caregiver = Caregiver.query.get_or_404(caregiver_id)
        
        # Check if caregiver has any shifts
        if caregiver.shifts:
            return jsonify({'success': False, 'message': 'Cannot delete caregiver with assigned shifts'}), 400
            
        db.session.delete(caregiver)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Caregiver deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting caregiver: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@views.route('/grant')
def grant_view():
    try:
        logger.debug("Processing grant view request")
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start from Monday
        dates = list(rrule(DAILY, count=7, dtstart=start_date))
        
        # Get all shifts for the week with caregiver information
        shifts = Shift.query.filter(
            Shift.date >= start_date,
            Shift.date < start_date + timedelta(days=7)
        ).join(Caregiver).order_by(Shift.date, Shift.shift_type).all()
        
        logger.debug(f"Found {len(shifts)} shifts for the week")
        return render_template('grant.html', dates=dates, shifts=shifts)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in grant view: {e}\nTraceback:\n{error_traceback}")
        return render_template('error.html', error=str(e)), 500

def generate_shifts_for_date_range(start_date, end_date):
    """Generate shifts for the given date range."""
    try:
        # Get all caregivers
        caregivers = Caregiver.query.all()
        if not caregivers:
            raise ValueError("No caregivers found in the system")
            
        # Delete existing shifts in the date range
        Shift.query.filter(
            Shift.date >= start_date,
            Shift.date <= end_date
        ).delete()
        
        # Get all dates in the range
        current_date = start_date
        while current_date <= end_date:
            used_caregivers_today = set()
            caregiver_index = 0
            
            # Assign A shift (1 caregiver)
            new_shift = Shift(
                date=current_date.date(),
                shift_type='A',
                caregiver_id=caregivers[caregiver_index].id
            )
            db.session.add(new_shift)
            used_caregivers_today.add(caregivers[caregiver_index].id)
            caregiver_index = (caregiver_index + 1) % len(caregivers)
            
            # Assign G shifts (2 caregivers - G1 and G2)
            for g_type in ['G1', 'G2']:
                while caregivers[caregiver_index].id in used_caregivers_today:
                    caregiver_index = (caregiver_index + 1) % len(caregivers)
                new_shift = Shift(
                    date=current_date.date(),
                    shift_type=g_type,
                    caregiver_id=caregivers[caregiver_index].id
                )
                db.session.add(new_shift)
                used_caregivers_today.add(caregivers[caregiver_index].id)
                caregiver_index = (caregiver_index + 1) % len(caregivers)
            
            # Assign B shift (2 caregivers, except Saturday)
            if current_date.weekday() != 5:  # Not Saturday
                for b_num in range(2):
                    while caregivers[caregiver_index].id in used_caregivers_today:
                        caregiver_index = (caregiver_index + 1) % len(caregivers)
                    new_shift = Shift(
                        date=current_date.date(),
                        shift_type='B',
                        caregiver_id=caregivers[caregiver_index].id
                    )
                    db.session.add(new_shift)
                    used_caregivers_today.add(caregivers[caregiver_index].id)
                    caregiver_index = (caregiver_index + 1) % len(caregivers)
            
            # Assign C shift (1 caregiver)
            while caregivers[caregiver_index].id in used_caregivers_today:
                caregiver_index = (caregiver_index + 1) % len(caregivers)
            new_shift = Shift(
                date=current_date.date(),
                shift_type='C',
                caregiver_id=caregivers[caregiver_index].id
            )
            db.session.add(new_shift)
            
            current_date += timedelta(days=1)
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating shifts: {e}")
        raise

@views.route('/fill-schedule', methods=['POST'])
def fill_schedule():
    try:
        logger.debug("Starting schedule fill operation")
        # Define the weekly pattern from the image
        weekly_pattern = {
            0: {  # Monday
                'A': 'MB',
                'G1': 'Teontae',
                'G2': 'MG',
                'B': 'Amanda',  # Will be skipped for 4/28
                'C': 'Michelle'
            },
            1: {  # Tuesday
                'A': 'Fatima',
                'G1': 'MG',
                'G2': 'Teontae',
                'B': 'Michelle',
                'C': 'Kisha'
            },
            2: {  # Wednesday
                'A': 'MB',
                'G1': 'MG',
                'G2': 'Teontae',
                'B': 'Kisha',
                'C': 'Amanda'  # Will be skipped for 4/30
            },
            3: {  # Thursday
                'A': 'Fatima',
                'G1': 'MB',
                'G2': 'Teontae',
                'B': 'Kisha',
                'C': 'Amanda'  # Will be skipped for 5/1
            },
            4: {  # Friday
                'A': 'MB',
                'G1': 'Kisha',
                'G2': 'Teontae',
                'B': 'Fatima',
                'C': 'Amanda'  # Will be skipped for 5/2
            },
            5: {  # Saturday
                'A': 'MG',
                'G2': 'Teontae',
                'G1': 'Fatima',
                'B': 'Kisha',
                'C': 'Michelle'
            },
            6: {  # Sunday
                'A': 'MG',
                'G2': 'Teontae',
                'G1': 'Michelle',
                'B': 'Fatima',
                'C': 'Amanda'
            }
        }

        # Get all caregivers to map names to IDs
        caregivers = {c.name: c.id for c in Caregiver.query.all()}
        logger.debug(f"Found caregivers: {list(caregivers.keys())}")
        
        # Delete existing shifts from April 7th onwards
        schedule_start = datetime(2025, 4, 7)  # Monday
        schedule_end = datetime(2025, 5, 31)  # Saturday
        
        deleted_count = Shift.query.filter(
            Shift.date >= schedule_start.date(),
            Shift.date <= schedule_end.date()
        ).delete()
        logger.debug(f"Deleted {deleted_count} existing shifts")

        # Function to create shifts for a date range
        def create_shifts_for_range(start_date, end_date):
            current_date = start_date
            shifts_created = 0
            
            while current_date <= end_date:
                # Get the day pattern based on weekday (0 = Monday, 6 = Sunday)
                day_pattern = weekly_pattern[current_date.weekday()]
                logger.debug(f"Creating shifts for {current_date.date()}, pattern: {day_pattern}")
                
                for shift_type, caregiver_name in day_pattern.items():
                    # Skip Amanda's shifts during her time off
                    if (caregiver_name == 'Amanda' and 
                        datetime(2025, 4, 28) <= current_date <= datetime(2025, 5, 2)):
                        logger.debug(f"Skipping shift for Amanda's time off on {current_date.date()}")
                        continue
                    
                    if caregiver_name not in caregivers:
                        raise ValueError(f"Caregiver {caregiver_name} not found in database")
                    
                    new_shift = Shift(
                        date=current_date.date(),
                        shift_type=shift_type,
                        caregiver_id=caregivers[caregiver_name]
                    )
                    db.session.add(new_shift)
                    shifts_created += 1
                    logger.debug(f"Created {shift_type} shift for {caregiver_name} on {current_date.date()}")
                
                current_date += timedelta(days=1)
            
            return shifts_created

        # Create shifts for April (7th-30th)
        april_shifts = create_shifts_for_range(schedule_start, datetime(2025, 4, 30))
        logger.debug(f"Created {april_shifts} shifts for April")
        
        # Create shifts for May (entire month including May 31st)
        may_start = datetime(2025, 5, 1)
        may_shifts = create_shifts_for_range(may_start, schedule_end)
        logger.debug(f"Created {may_shifts} shifts for May (including May 31st)")
        
        db.session.commit()
        total_shifts = april_shifts + may_shifts
        logger.debug(f"Successfully created total of {total_shifts} shifts")
        
        # Double check May 31st shifts were created
        may_31_shifts = Shift.query.filter(
            Shift.date == datetime(2025, 5, 31).date()
        ).all()
        logger.debug(f"May 31st shifts created: {[f'{s.shift_type}:{s.caregiver.name}' for s in may_31_shifts]}")
        
        return jsonify({
            'success': True, 
            'message': f'Schedule filled successfully with {total_shifts} shifts'
        })
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        logger.error(f"Error filling schedule: {error_msg}")
        return jsonify({
            'success': False, 
            'message': f'Error filling schedule: {error_msg}'
        }), 500

@views.route('/caregiver-schedule/<caregiver_name>')
def caregiver_schedule(caregiver_name):
    try:
        logger.debug(f"Retrieving schedule for caregiver: {caregiver_name}")
        # Get the caregiver
        caregiver = Caregiver.query.filter_by(name=caregiver_name).first_or_404()
        logger.debug(f"Found caregiver with ID: {caregiver.id}")
        
        # Get all shifts for April-May 2025
        start_date = datetime(2025, 4, 7)  # Schedule starts from April 7th
        end_date = datetime(2025, 5, 31, 23, 59, 59)  # Include full last day
        
        # Get shifts ordered by date
        shifts = Shift.query.filter(
            Shift.caregiver_id == caregiver.id,
            Shift.date >= start_date.date(),
            Shift.date <= end_date.date()
        ).order_by(Shift.date).all()  # Removed shift_type from order_by to ensure proper date ordering
        
        logger.debug(f"Found {len(shifts)} shifts for {caregiver_name}")
        for shift in shifts:
            logger.debug(f"Shift on {shift.date}: {shift.shift_type} ({shift.start_hour}:00-{shift.end_hour}:00)")
        
        # Sort shifts by date and start hour after fetching
        shifts.sort(key=lambda x: (x.date, x.start_hour))
        
        # Calculate weekly hours
        weekly_hours = {}
        total_hours = 0
        current_week = None
        
        for shift in shifts:
            # Get the Monday of the current week
            monday = shift.date - timedelta(days=shift.date.weekday())
            if monday != current_week:
                current_week = monday
                weekly_hours[monday] = 0
            weekly_hours[monday] += shift.duration_hours
            total_hours += shift.duration_hours
            
        logger.debug(f"Weekly hours for {caregiver_name}: {weekly_hours}")
        logger.debug(f"Total hours for {caregiver_name}: {total_hours}")
        
        # Group shifts by month for easy display
        shifts_by_month = {}
        for shift in shifts:
            month_key = shift.date.strftime('%B %Y')
            if month_key not in shifts_by_month:
                shifts_by_month[month_key] = []
            shifts_by_month[month_key].append(shift)
            
        # Sort shifts within each month
        for month_shifts in shifts_by_month.values():
            month_shifts.sort(key=lambda x: (x.date, x.start_hour))
        
        # Verify if May 31st shifts are included
        may_31_shifts = [s for s in shifts if s.date == datetime(2025, 5, 31).date()]
        logger.debug(f"May 31st shifts for {caregiver_name}: {len(may_31_shifts)}")
        
        return render_template(
            'caregiver_schedule.html',
            caregiver=caregiver,
            shifts_by_month=shifts_by_month,
            weekly_hours=weekly_hours,
            total_hours=total_hours
        )
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error in caregiver schedule view: {e}\nTraceback:\n{error_traceback}")
        return render_template('error.html', error=str(e)), 500

@views.route('/test-calendar-connection', methods=['GET'])
def test_calendar_connection():
    try:
        service = get_calendar_service()
        # Try to get calendar list as a simple test
        calendar_list = service.calendarList().list().execute()
        
        return jsonify({
            'success': True,
            'message': 'Successfully connected to Google Calendar API',
            'calendars': [cal['summary'] for cal in calendar_list.get('items', [])]
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error testing calendar connection: {error_msg}")
        return jsonify({
            'success': False,
            'message': f'Error connecting to Google Calendar: {error_msg}'
        }), 500

@views.route('/sync-to-calendar', methods=['POST'])
def sync_to_calendar():
    try:
        logger.debug("Starting Google Calendar sync")
        
        # Get shifts for April-May 2025
        start_date = datetime(2025, 4, 7)  # Schedule starts from April 7th
        end_date = datetime(2025, 5, 31)  # Include May 31st
        
        shifts = Shift.query.filter(
            Shift.date >= start_date.date(),
            Shift.date <= end_date.date()
        ).order_by(Shift.date).all()
        
        logger.debug(f"Found {len(shifts)} shifts to sync")
        
        if not shifts:
            return jsonify({
                'success': False,
                'message': 'No shifts found to sync'
            }), 400
        
        # Log some sample shifts for debugging
        sample_shifts = shifts[:3]
        for shift in sample_shifts:
            logger.debug(f"Sample shift: Date={shift.date}, Type={shift.shift_type}, "
                       f"Caregiver={shift.caregiver.name}")
        
        # Sync shifts to Google Calendar
        sync_shifts_to_calendar(shifts)
        
        return jsonify({
            'success': True,
            'message': f'Successfully synced {len(shifts)} shifts to Google Calendar'
        })
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error syncing to Google Calendar: {error_msg}")
        return jsonify({
            'success': False,
            'message': f'Error syncing to Google Calendar: {error_msg}'
        }), 500
