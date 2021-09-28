import json
import os.path
import time
from datetime import datetime, timedelta

from get_schedule import Schedule
from google_api.api import Calendar
from google_api.cred import Creds

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
dir_path = os.path.dirname(os.path.abspath(__file__))
events_file_path = os.path.join(dir_path, 'events_log.txt')
events_insert_json = os.path.join(dir_path, 'events_insert_log.json')

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
             with open(events_insert_json, 'r') as f:
                # Get last line which is the date and time of last inserted event
                data = json.load(f)
                date_last_insert_json = data['schedule'][-1]['end']['dateTime']
                date_last_insert = datetime.strptime(date_last_insert_json, '%Y-%m-%dT%H:%M:%S%z')
        except (IOError, IndexError, TypeError):
            data = None
            date_last_insert = self.date_now

        events_inserted = False
        while run:
            if not date_now_weekday == 4 and (self.date_now.date() < date_last_insert.date() and data):
                self.been_checked()
                run = False
            else:
                if date_now_weekday == 4 and self.date_now.hour < 11:
                    self.sleep_time(60)
                    continue
                events_inserted = self.insert_schedule(date_last_insert)
                if events_inserted:
                    print('Successfully inserted events.')
                    self.schedule.browser_quit()
                    run = False
                elif events_inserted == None:
                    run = False
                    self.been_checked()
                else:
                    self.sleep_time(60 * 5)

    def sleep_time(self, sec):
        print('Sleeping')
        time.sleep(sec)

    def been_checked(self):
        print('You have already check your schedule.')
        return

    def insert_schedule(self, date_last_insert):
        year_now = self.date_now.year
        date, time =  self.schedule.get_schedule()
        new_log_file = True
        new_schedule = False
        if date and time:
            creds = Creds(SCOPES, dir_path)
            service = creds.credentials()
            calendar = Calendar(service, self.tz)
            for schedule_date, schedule_time in zip(date, time):
                shift_in, shift_out = schedule_time.split('-')
                start_datetime, end_datetime = self.format_schedule(schedule_date, year_now, shift_in, shift_out)
                start_dt_format = self.tz.localize(start_datetime)
                
                if date_last_insert.date() < start_dt_format.date():
                    # Add one day to shift_out if shift from pm to am
                    if shift_in[-2:] == 'PM' and shift_out[-2:] == 'AM':
                        end_datetime += timedelta(days=1)

                    start_dt_format = start_dt_format.isoformat()
                    end_dt_format = self.tz.localize(end_datetime).isoformat() 
                    event = calendar.insert(start_dt_format, end_dt_format)

                    if new_log_file:
                        event_json = {'schedule': [event]}
                        self.write_json(event_json, events_insert_json)
                        new_log_file = False
                        new_schedule = True
                    else:
                        with open(events_insert_json) as f:
                            data = json.load(f)
                            temp = data['schedule']
                            temp.append(event)
                        self.write_json(data, events_insert_json)
            return new_schedule
        elif date == time == None:
            return None
        return False

    def write_json(self, data, filename):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def format_schedule(self, date, year, shift_in, shift_out):
        dt_format = '%Y %a %B %d %I:%M%p'
        start_datetime = datetime.strptime(f'{year} {date} {shift_in}', dt_format)
        end_datetime = datetime.strptime(f'{year} {date} {shift_out}', dt_format)
        return start_datetime, end_datetime
