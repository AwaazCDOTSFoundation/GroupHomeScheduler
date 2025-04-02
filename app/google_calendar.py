from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import os.path
import pickle
import logging

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Get an authorized Calendar API service instance."""
    creds = None
    # Look for token file in the same directory as credentials.json
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'token.pickle')
    credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'credentials.json')
    
    logger.debug(f"Looking for token at: {token_path}")
    logger.debug(f"Looking for credentials at: {credentials_path}")
    
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists(token_path):
        logger.debug("Found existing token.pickle")
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            creds = None
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.debug("Refreshing expired credentials")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console "
                    "and place it in the project root directory."
                )
            
            logger.debug("Starting new OAuth flow")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Error in OAuth flow: {e}")
                raise
        
        # Save the credentials for the next run
        try:
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            logger.debug("Saved new token.pickle")
        except Exception as e:
            logger.error(f"Error saving token: {e}")
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        logger.debug("Successfully built calendar service")
        return service
    except Exception as e:
        logger.error(f"Error building calendar service: {e}")
        raise

def get_shift_color(shift_type):
    """Return the Google Calendar color ID for each shift type."""
    # Google Calendar color IDs:
    # 1: Blue, 2: Green, 3: Purple, 4: Red, 5: Yellow, 
    # 6: Orange, 7: Turquoise, 8: Gray, 9: Bold Blue, 10: Bold Green
    color_map = {
        'A': '1',    # Blue
        'B': '2',    # Green
        'C': '3',    # Purple
        'G1': '6',   # Orange
        'G2': '7',   # Turquoise
    }
    return color_map.get(shift_type, '8')  # Default to gray

def get_shift_times(shift_type, date):
    """Get start and end times for a shift."""
    shift_times = {
        'A': {'start_hour': 6, 'start_minute': 0, 'end_hour': 14, 'end_minute': 0},     # 6 AM - 2 PM
        'B': {'start_hour': 16, 'start_minute': 0, 'end_hour': 0, 'end_minute': 0},     # 4 PM - 12 AM
        'C': {'start_hour': 0, 'start_minute': 0, 'end_hour': 8, 'end_minute': 0},      # 12 AM - 8 AM
        'G1': {'start_hour': 12, 'start_minute': 0, 'end_hour': 20, 'end_minute': 0},   # 12 PM - 8 PM
        'G2': {'start_hour': 9, 'start_minute': 0, 'end_hour': 17, 'end_minute': 0},    # 9 AM - 5 PM
    }
    
    times = shift_times[shift_type]
    
    # Handle shifts that cross midnight (B and C shifts)
    if shift_type == 'B':
        # B shift starts on given date at 4 PM and ends at midnight (next day 12 AM)
        start_time = datetime.combine(
            date,
            datetime.min.time().replace(hour=times['start_hour'], minute=times['start_minute'])
        )
        end_time = datetime.combine(
            date + timedelta(days=1),
            datetime.min.time().replace(hour=times['end_hour'], minute=times['end_minute'])
        )
    elif shift_type == 'C':
        # C shift starts at midnight and ends at 8 AM same day
        start_time = datetime.combine(
            date,
            datetime.min.time().replace(hour=times['start_hour'], minute=times['start_minute'])
        )
        end_time = datetime.combine(
            date,
            datetime.min.time().replace(hour=times['end_hour'], minute=times['end_minute'])
        )
    else:
        # Regular shifts that don't cross midnight (A, G1, G2)
        start_time = datetime.combine(
            date,
            datetime.min.time().replace(hour=times['start_hour'], minute=times['start_minute'])
        )
        end_time = datetime.combine(
            date,
            datetime.min.time().replace(hour=times['end_hour'], minute=times['end_minute'])
        )
    
    return start_time, end_time

def sync_shifts_to_calendar(shifts, calendar_id='primary'):
    """Sync shifts to Google Calendar."""
    try:
        service = get_calendar_service()
        logger.info("Connected to Google Calendar API")
        
        # Get existing events in the date range to avoid duplicates
        start_min = min(shift.date for shift in shifts)
        end_max = max(shift.date for shift in shifts) + timedelta(days=1)
        
        # Format dates in RFC3339 format with UTC timezone
        time_min = datetime.combine(start_min, datetime.min.time()).astimezone().isoformat()
        time_max = datetime.combine(end_max, datetime.min.time()).astimezone().isoformat()
        
        logger.debug(f"Fetching events between {time_min} and {time_max}")
        
        # Delete existing events in the date range
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True
            ).execute()
            
            for event in events_result.get('items', []):
                try:
                    service.events().delete(
                        calendarId=calendar_id,
                        eventId=event['id']
                    ).execute()
                    logger.debug(f"Deleted existing event: {event.get('summary')}")
                except HttpError as e:
                    logger.error(f"Error deleting event {event.get('id')}: {e}")
        except HttpError as e:
            logger.error(f"Error listing events: {e}")
            if e.resp.status == 400:
                logger.error(f"Bad Request - Request details: {e.content}")
            raise
        
        # Create new events for each shift
        events_created = 0
        for shift in shifts:
            try:
                start_time, end_time = get_shift_times(shift.shift_type, shift.date)
                
                # Convert to local timezone and format for Google Calendar
                event = {
                    'summary': f"{shift.shift_type} - {shift.caregiver.name}",
                    'description': f"Shift Type: {shift.shift_type}\nCaregiver: {shift.caregiver.name}",
                    'start': {
                        'dateTime': start_time.astimezone().isoformat(),
                        'timeZone': 'America/New_York',
                    },
                    'end': {
                        'dateTime': end_time.astimezone().isoformat(),
                        'timeZone': 'America/New_York',
                    },
                    'colorId': get_shift_color(shift.shift_type),
                    'reminders': {
                        'useDefault': True
                    }
                }
                
                logger.debug(f"Creating event: {event}")
                event = service.events().insert(calendarId=calendar_id, body=event).execute()
                events_created += 1
                logger.debug(f"Created event: {event.get('htmlLink')}")
            except HttpError as e:
                logger.error(f"Error creating event for shift {shift.id}: {e}")
                if e.resp.status == 400:
                    logger.error(f"Bad Request - Event details: {event}")
                    logger.error(f"Response content: {e.content}")
                continue  # Continue with next shift if one fails
        
        logger.info(f"Successfully synced {events_created} shifts to Google Calendar")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing to Google Calendar: {str(e)}")
        raise 