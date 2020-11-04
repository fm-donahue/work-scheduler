#! /usr/bin/env python

import json
import os.path
import pickle
import sys
import time
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tzlocal import get_localzone

from get_schedule import get_schedule

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
dir_path = os.path.dirname(os.path.abspath(__file__))
events_file_path = os.path.join(dir_path, 'events_log.txt')


def google_credentials():
    creds_file_path = os.path.join(dir_path, 'credentials.json')
    token_file_path = os.path.join(dir_path, 'token.pickle')

    # From google calendar api quickstart
    creds = None

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file_path):
        with open(token_file_path, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_file_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)

def format_schedule(date, year, shift_in, shift_out):
    dt_format = '%Y %a %B %d %I:%M%p'
    start_datetime = datetime.strptime(f'{year} {date} {shift_in}', dt_format)
    end_datetime = datetime.strptime(f'{year} {date} {shift_out}', dt_format)
    return start_datetime, end_datetime


def insert_events(date_now, weeks_apart, fri_sat_weekday):
    tz = get_localzone()
    tz_date_now = tz.localize(date_now)
    year_now = date_now.year
    date , time = get_schedule()
    new_log_file = True
    new_schedule = False
    start_sunday = False
    if date and time:
        service = google_credentials()
        for schedule_date, schedule_time in zip(date, time):
            shift_in, shift_out = schedule_time.split('-')
            start_datetime, end_datetime = format_schedule(schedule_date, year_now, shift_in, shift_out)
            date_now_isoformat = date_now.isoformat()
            start_dt_format = tz.localize(start_datetime)

            # Insert event if work date is in upcoming days regarding to the date today
            if tz_date_now < start_dt_format:
                # Prevents inserting events again in Friday and Saturday if last insert was last week
                # Friday or Saturday. This skips it until Sunday and start inserting events.
                if weeks_apart < 2 and fri_sat_weekday and not start_sunday:
                    if start_datetime.weekday() != 6:
                        continue
                    start_sunday = True
                new_schedule = True
                start_dt_format = start_dt_format.isoformat()
                end_dt_format = tz.localize(end_datetime).isoformat() 

                # Add one day to shift_out if shift from pm to am
                if shift_in[-2:] == 'PM' and shift_out[-2:] == 'AM':
                    end_datetime += timedelta(days=1)

                event = {
                    'summary': 'Work Schedule',
                    'start': {
                        'dateTime': f'{start_dt_format}',
                        'timeZone': '',
                    },
                    'end': {
                        'dateTime': f'{end_dt_format}',
                        'timeZone': '',
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                                {'method': 'popup', 'minutes': 840},
                        ],
                    },
                    'colorId': '9',
                }
                event['start']['timeZone'] = event['end']['timeZone'] = str(tz)
                event = json.dumps(event, indent=4)
                json_event = json.loads(event)
                if new_log_file:
                    with open(events_file_path, 'w') as f:
                        f.write(event)
                    new_log_file = False
                else:
                    with open(events_file_path, 'a') as f:
                        f.write(event)
                print('Inserting event to calendar.')
                event = service.events().insert(calendarId='primary', body=json_event).execute()
        if new_schedule:
            with open(events_file_path, 'a') as f:
                f.write(f"\n{date_now_isoformat}")
        return new_schedule
    return False


def stop_program():
    print('You have already check your schedule.')
    return


def main():
     while True:
        date_now = datetime.now()
        date_now_weekday = date_now.weekday()
        check_schedule = False
        events_inserted = False

        try :
            with open(events_file_path,'r') as f:
                # Get last line which is the date and time of last inserted event
                data = f.readlines()[-1]
                date_last_insert = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S.%f')
                
        except IOError:
            data = None
            date_last_insert = date_now

        date_last_insert_weekday = date_last_insert.weekday()
        weeks_apart = date_now.isocalendar()[1] - date_last_insert.isocalendar()[1]
        fri_sat_weekday = all(x in [4,5] for x in [date_now_weekday, date_last_insert_weekday])

        if not data:
            check_schedule = True

        elif date_now_weekday >= 4:
            if weeks_apart == 0 and date_last_insert_weekday >= 4:
                stop_program()
            elif date_now_weekday == 4 and date_now.hour < 11:
                print('Sleeping')
                time.sleep(60)
                continue
            else:
                check_schedule = True
        else:
            if (weeks_apart == 0 and date_last_insert_weekday < 4) or weeks_apart > 1:
                check_schedule = True
            else:
                stop_program()
        if check_schedule:
            events_inserted = insert_events(date_now, weeks_apart, fri_sat_weekday)
        else:
            break
        if events_inserted:
            print('Successfully inserted events.')
            break
        else:
            print('Sleeping')
            time.sleep(60 * 5)

if __name__ == '__main__':
    main()
