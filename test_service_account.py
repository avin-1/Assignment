from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# When a Service Account creates a Form, it places it in its invisible Google Drive.
# Historically, this sometimes triggers a 500 Error if the Drive API scope is omitted.
SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/drive'
]

# The path to your securely saved json credentials file
SERVICE_ACCOUNT_FILE = 'Agent/service_account.json'

def create_form_with_service_account():
    print("Initiating Service Account Authentication...")
    try:
        # Load the credentials directly from the file; NO user authorization required!
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('forms', 'v1', credentials=creds)

        print("Authentication successful! Bot is attempting to silently create a Google Form...")

        # Define the basic form body
        form = {
            "info": {
                "title": "Automated OmniMise Form",
                "documentTitle": "Created dynamically by API Backend"
            }
        }
        
        # Execute creation directly
        result = service.forms().create(body=form).execute()
        print(f"\n====================================")
        print(f"Success! Form created autonomously!")
        print(f"Responder URL (Give this to users): {result.get('responderUri')}")
        print(f"Editor ID (For fetching responses): {result.get('formId')}")
        print(f"====================================\n")
        
    except Exception as e:
        print(f"Error executing Service Account form request: {str(e)}")

if __name__ == '__main__':
    create_form_with_service_account()
