from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
from dotenv import load_dotenv

from backend.assistant_app.api_integration.google_token_store import load_credentials

load_dotenv()

def get_calendar_service(user_email: str):
    """Get Google Calendar service for a user."""
    creds = load_credentials(user_email)
    if not creds:
        raise ValueError(f"No valid credentials found for {user_email}")
    return build("calendar", "v3", credentials=creds)

def list_calendar_events(user_email: str, calendar_id: str = "primary", max_results: int = 10,
                        time_min: Optional[str] = None, time_max: Optional[str] = None) -> str:
    """
    List calendar events for a user.

    Args:
        user_email: The user's email address
        calendar_id: Calendar ID (default: "primary")
        max_results: Maximum number of events to return (default: 10)
        time_min: Start time in ISO format (default: now)
        time_max: End time in ISO format (default: 7 days from now)

    Returns:
        str: JSON-formatted list of events
    """
    try:
        service = get_calendar_service(user_email)

        # Set default time range if not provided
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return json.dumps({
                "message": "No upcoming events found",
                "time_range": f"{time_min} to {time_max}",
                "events": []
            })

        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            formatted_event = {
                "id": event['id'],
                "summary": event.get('summary', 'No title'),
                "description": event.get('description', ''),
                "start": start,
                "end": end,
                "location": event.get('location', ''),
                "attendees": [attendee['email'] for attendee in event.get('attendees', [])],
                "html_link": event.get('htmlLink', ''),
                "status": event.get('status', '')
            }
            formatted_events.append(formatted_event)

        return json.dumps({
            "message": f"Found {len(formatted_events)} events",
            "time_range": f"{time_min} to {time_max}",
            "events": formatted_events
        }, indent=2)

    except HttpError as error:
        return json.dumps({
            "error": f"Calendar API error: {error}",
            "events": []
        })
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "events": []
        })

def create_calendar_event(user_email: str, summary: str, start_time: str, end_time: str,
                         description: Optional[str] = None, location: Optional[str] = None,
                         attendees: Optional[List[str]] = None, calendar_id: str = "primary") -> str:
    """
    Create a new calendar event.

    Args:
        user_email: The user's email address
        summary: Event title/summary
        start_time: Start time in ISO format (e.g., "2024-01-15T10:00:00Z")
        end_time: End time in ISO format (e.g., "2024-01-15T11:00:00Z")
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)
        calendar_id: Calendar ID (default: "primary")

    Returns:
        str: JSON response with event details or error message
    """
    try:
        service = get_calendar_service(user_email)

        event = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            sendUpdates='all' if attendees else 'none'
        ).execute()

        return json.dumps({
            "message": "Event created successfully",
            "event": {
                "id": event['id'],
                "summary": event.get('summary', ''),
                "description": event.get('description', ''),
                "start": event['start'].get('dateTime', event['start'].get('date')),
                "end": event['end'].get('dateTime', event['end'].get('date')),
                "location": event.get('location', ''),
                "html_link": event.get('htmlLink', ''),
                "attendees": [attendee['email'] for attendee in event.get('attendees', [])]
            }
        }, indent=2)

    except HttpError as error:
        return json.dumps({
            "error": f"Calendar API error: {error}",
            "details": "Failed to create event"
        })
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "details": "Failed to create event"
        })

def update_calendar_event(user_email: str, event_id: str, summary: Optional[str] = None,
                         start_time: Optional[str] = None, end_time: Optional[str] = None,
                         description: Optional[str] = None, location: Optional[str] = None,
                         attendees: Optional[List[str]] = None, calendar_id: str = "primary") -> str:
    """
    Update an existing calendar event.

    Args:
        user_email: The user's email address
        event_id: The ID of the event to update
        summary: New event title/summary (optional)
        start_time: New start time in ISO format (optional)
        end_time: New end time in ISO format (optional)
        description: New event description (optional)
        location: New event location (optional)
        attendees: New list of attendee email addresses (optional)
        calendar_id: Calendar ID (default: "primary")

    Returns:
        str: JSON response with updated event details or error message
    """
    try:
        service = get_calendar_service(user_email)

        # First, get the existing event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update only the provided fields
        if summary is not None:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location
        if start_time is not None:
            # Preserve the timezone from the existing event
            if 'timeZone' in event['start']:
                event['start'] = {
                    'dateTime': start_time,
                    'timeZone': event['start']['timeZone']
                }
            else:
                event['start']['dateTime'] = start_time
        if end_time is not None:
            # Preserve the timezone from the existing event
            if 'timeZone' in event['end']:
                event['end'] = {
                    'dateTime': end_time,
                    'timeZone': event['end']['timeZone']
                }
            else:
                event['end']['dateTime'] = end_time
        if attendees is not None:
            event['attendees'] = [{'email': email} for email in attendees]

        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event,
            sendUpdates='all' if attendees else 'none'
        ).execute()

        return json.dumps({
            "message": "Event updated successfully",
            "event": {
                "id": updated_event['id'],
                "summary": updated_event.get('summary', ''),
                "description": updated_event.get('description', ''),
                "start": updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                "end": updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                "location": updated_event.get('location', ''),
                "html_link": updated_event.get('htmlLink', ''),
                "attendees": [attendee['email'] for attendee in updated_event.get('attendees', [])]
            }
        }, indent=2)

    except HttpError as error:
        if error.resp.status == 404:
            return json.dumps({
                "error": "Event not found",
                "details": f"Event with ID {event_id} does not exist"
            })
        return json.dumps({
            "error": f"Calendar API error: {error}",
            "details": "Failed to update event"
        })
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "details": "Failed to update event"
        })

def delete_calendar_event(user_email: str, event_id: str, calendar_id: str = "primary") -> str:
    """
    Delete a calendar event.

    Args:
        user_email: The user's email address
        event_id: The ID of the event to delete
        calendar_id: Calendar ID (default: "primary")

    Returns:
        str: JSON response with success or error message
    """
    try:
        service = get_calendar_service(user_email)

        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        return json.dumps({
            "message": "Event deleted successfully",
            "event_id": event_id
        })

    except HttpError as error:
        if error.resp.status == 404:
            return json.dumps({
                "error": "Event not found",
                "details": f"Event with ID {event_id} does not exist"
            })
        return json.dumps({
            "error": f"Calendar API error: {error}",
            "details": "Failed to delete event"
        })
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "details": "Failed to delete event"
        })

def search_calendar_events(user_email: str, query: str, calendar_id: str = "primary",
                          max_results: int = 10) -> str:
    """
    Search for calendar events using a text query.

    Args:
        user_email: The user's email address
        query: Search query (e.g., "meeting", "lunch", "conference")
        calendar_id: Calendar ID (default: "primary")
        max_results: Maximum number of events to return (default: 10)

    Returns:
        str: JSON-formatted list of matching events
    """
    try:
        service = get_calendar_service(user_email)

        # Set time range for search (past 30 days to future 30 days)
        time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=calendar_id,
            q=query,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return json.dumps({
                "message": f"No events found matching '{query}'",
                "search_query": query,
                "time_range": f"{time_min} to {time_max}",
                "events": []
            })

        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            formatted_event = {
                "id": event['id'],
                "summary": event.get('summary', 'No title'),
                "description": event.get('description', ''),
                "start": start,
                "end": end,
                "location": event.get('location', ''),
                "attendees": [attendee['email'] for attendee in event.get('attendees', [])],
                "html_link": event.get('htmlLink', ''),
                "status": event.get('status', '')
            }
            formatted_events.append(formatted_event)

        return json.dumps({
            "message": f"Found {len(formatted_events)} events matching '{query}'",
            "search_query": query,
            "time_range": f"{time_min} to {time_max}",
            "events": formatted_events
        }, indent=2)

    except HttpError as error:
        return json.dumps({
            "error": f"Calendar API error: {error}",
            "events": []
        })
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "events": []
        })

def get_calendar_list(user_email: str) -> str:
    """
    Get list of available calendars for a user.

    Args:
        user_email: The user's email address

    Returns:
        str: JSON-formatted list of calendars
    """
    try:
        service = get_calendar_service(user_email)

        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])

        if not calendars:
            return json.dumps({
                "message": "No calendars found",
                "calendars": []
            })

        formatted_calendars = []
        for calendar in calendars:
            formatted_calendar = {
                "id": calendar['id'],
                "summary": calendar.get('summary', ''),
                "description": calendar.get('description', ''),
                "primary": calendar.get('primary', False),
                "access_role": calendar.get('accessRole', ''),
                "selected": calendar.get('selected', False)
            }
            formatted_calendars.append(formatted_calendar)

        return json.dumps({
            "message": f"Found {len(formatted_calendars)} calendars",
            "calendars": formatted_calendars
        }, indent=2)

    except HttpError as error:
        return json.dumps({
            "error": f"Calendar API error: {error}",
            "calendars": []
        })
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "calendars": []
        })