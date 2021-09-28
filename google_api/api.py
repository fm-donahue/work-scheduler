import json

class Calendar:
    def __init__(self, service, tz):
        self.service = service
        self.tz = tz

    def insert(self, start_date, end_date):
        event = self.event_body(start_date, end_date)
        event = json.loads(event)
        self.service.events().insert(calendarId='primary', body=event).execute()
        print('Inserting event to calendar.')
        return event

    def event_body(self, start_date, end_date):
        event = {
                    'summary': 'Work Schedule',
                    'start': {
                        'dateTime': f'{start_date}',
                        'timeZone': '',
                    },
                    'end': {
                        'dateTime': f'{end_date}',
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
        event['start']['timeZone'] = event['end']['timeZone'] = str(self.tz)
        return json.dumps(event)
