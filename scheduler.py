#! /usr/bin/env python

import json
import os.path
import sys
import time
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tzlocal import get_localzone

from get_schedule import Schedule
from google_api.api import Calendar
from google_api.cred import Creds

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
dir_path = os.path.dirname(os.path.abspath(__file__))
events_file_path = os.path.join(dir_path, 'events_log.txt')

username = os.environ.get('work_username')
pwd = os.environ.get('work_pw')

class Scheduler:
    def __init__(self, date_now, tz):
        self.date_now = date_now
        self.tz = tz
        self.schedule = Schedule(username, pwd)

    def run(self):
        run = True
        date_now_weekday = self.date_now.weekday()

        try:
            with open(events_file_path,'r') as f:
                # Get last line which is the date and time of last inserted event
                data = f.readlines()[-1]
                date_last_insert = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S.%f')        
        except (IOError, IndexError, TypeError):
            data = None
            date_last_insert = self.date_now

        check_schedule = False
        events_inserted = False
        while run:
            date_last_insert_weekday = date_last_insert.weekday()
            weeks_apart = self.date_now.isocalendar()[1] - date_last_insert.isocalendar()[1]
            fri_sat_weekday = all(x in [4,5] for x in [date_now_weekday, date_last_insert_weekday])            
            if check_schedule:
                events_inserted = self.insert_schedule(weeks_apart, fri_sat_weekday)
                if events_inserted:
                    print('Successfully inserted events.')
                    self.schedule.browser_quit()
                    run = False
                elif events_inserted == None:
                    run = False
                else:
                    self.sleep_time(60 * 5)
            else:
                # Friday is when a new schedule will come out.
                if not data or weeks_apart > 1:
                    check_schedule = True
                else:
                    if date_now_weekday == 4 and self.date_now.hour < 11:
                        self.sleep_time(60)
                        continue
                    if weeks_apart == 1:
                        if (date_now_weekday > 3
                                or (date_now_weekday < 4 and date_last_insert_weekday < 4)):
                            check_schedule = True
                        else:
                            self.been_checked()
                            run = False
                    elif date_last_insert_weekday < 4 and weeks_apart == 0:
                        check_schedule = True
                    else:
                        self.been_checked()
                        run = False

    def sleep_time(self, sec):
        print('Sleeping')
        time.sleep(sec)

    def been_checked(self):
        print('You have already check your schedule.')
        return

    def insert_schedule(self, weeks_apart, fri_sat_weekday):
        tz_date_now = self.tz.localize(self.date_now)
        year_now = self.date_now.year
        date, time =  self.schedule.get_schedule()
        new_log_file = True
        new_schedule = False
        start_sunday = False
        if date and time:
            creds = Creds(SCOPES, dir_path)
            service = creds.credentials()
            calendar = Calendar(service, self.tz)
            for schedule_date, schedule_time in zip(date, time):
                shift_in, shift_out = schedule_time.split('-')
                start_datetime, end_datetime = self.format_schedule(schedule_date, year_now, shift_in, shift_out)
                date_now_isoformat = self.date_now.isoformat()
                start_dt_format = self.tz.localize(start_datetime)

                # Insert event if work date is in upcoming days regarding to the date today
                if tz_date_now < start_dt_format:
                    # Prevents inserting events again in Friday and Saturday if last insert was last week
                    # Friday or Saturday. This skips it until Sunday and start inserting events.
                    if weeks_apart < 2 and fri_sat_weekday and not start_sunday:
                        if start_dt_format.weekday() < 6:
                            continue
                        start_sunday = True
                    new_schedule = True

                    # Add one day to shift_out if shift from pm to am
                    if shift_in[-2:] == 'PM' and shift_out[-2:] == 'AM':
                        end_datetime += timedelta(days=1)

                    start_dt_format = start_dt_format.isoformat()
                    end_dt_format = self.tz.localize(end_datetime).isoformat() 
                    event = calendar.event_body(start_dt_format, end_dt_format)
                    print('Inserting event to calendar.')
                    calendar.insert(event)

                    if new_log_file:
                        with open(events_file_path, 'w') as f:
                            f.write(event)
                        new_log_file = False
                    else:
                        with open(events_file_path, 'a') as f:
                            f.write(event)

            if new_schedule:
                with open(events_file_path, 'a') as f:
                    f.write(f"\n{date_now_isoformat}")
            return new_schedule
        elif date == time == None:
            return None
        return False

    def format_schedule(self, date, year, shift_in, shift_out):
        dt_format = '%Y %a %B %d %I:%M%p'
        start_datetime = datetime.strptime(f'{year} {date} {shift_in}', dt_format)
        end_datetime = datetime.strptime(f'{year} {date} {shift_out}', dt_format)
        return start_datetime, end_datetime
