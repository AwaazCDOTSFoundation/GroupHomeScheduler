from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
from dateutil.rrule import rrule, DAILY
from .models import Caregiver, Shift, db
from .config import ShiftConfig
import logging
import traceback

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
