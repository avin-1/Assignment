import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/forms.responses.readonly', 'https://www.googleapis.com/auth/forms.body.readonly']

# Reconstruct a client_secret.json programmatically from the given credentials
client_config = {
    "installed": {
        "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID", "formapi-453516"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        "redirect_uris": ["http://localhost:8080/"]
    }
}

def authenticate_and_fetch_form():
    print("Initiating OAuth 2.0 Flow...")
    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=8080)
        
        print("Authentication successful! Testing if we can fetch form details...")
        service = build('forms', 'v1', credentials=creds)

        # The ID from the user's URL: https://docs.google.com/forms/d/e/1FAIpQLSdSsZjQurCbM1PizpjSIjbv0Y_0bJs0se19hS4SImyXmuz5Jw/viewform
        # Wait, the ID in the /e/ path is a responder ID, not the edit form ID.
        # Let's try to fetch it, but usually the API needs the actual Form ID (from /d/ID/edit).
        form_id = "1FAIpQLSdSsZjQurCbM1PizpjSIjbv0Y_0bJs0se19hS4SImyXmuz5Jw"
        
        result = service.forms().get(formId=form_id).execute()
        print(f"Success! Form details fetched:")
        print(result)
        
    except Exception as e:
        print(f"Error testing credentials: {str(e)}")

if __name__ == '__main__':
    authenticate_and_fetch_form()
