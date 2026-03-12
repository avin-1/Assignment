from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/forms.body'
]

creds = Credentials.from_service_account_file("Agent/service_account.json", scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

file_metadata = {
    'name': 'Test Form via Drive API',
    'mimeType': 'application/vnd.google-apps.form'
}

try:
    file = drive_service.files().create(body=file_metadata, fields='id').execute()
    form_id = file.get('id')
    print("Drive API created Form ID:", form_id)
    
    # Try updating it via forms api
    forms_service = build('forms', 'v1', credentials=creds)
    form = forms_service.forms().get(formId=form_id).execute()
    print("Forms API retrieved Form URI:", form.get('responderUri'))
except Exception as e:
    import traceback
    traceback.print_exc()
