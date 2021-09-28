import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class Creds():
    def __init__(self, SCOPES, dir_path):
        self.SCOPES = SCOPES
        self.dir_path = os.path.join(dir_path, 'google_api') # os.path.dirname(os.path.abspath(__file__))
        self.creds_file_path = os.path.join(self.dir_path, 'credentials.json')
        self.token_file_path = os.path.join(self.dir_path, 'token.pickle')

    def credentials(self):
        # From google calendar api quickstart
        creds = None

        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.token_file_path):
            with open(self.token_file_path, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.creds_file_path, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_file_path, 'wb') as token:
                pickle.dump(creds, token)

        return build('calendar', 'v3', credentials=creds)
