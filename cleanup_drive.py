"""
Fast cleanup: deletes ALL files from Service Account Drive to free quota.
"""
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file("Agent/service_account.json", scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

print("Listing files...")
deleted = 0

# Keep fetching and deleting until nothing is left
while True:
    response = drive.files().list(
        spaces='drive',
        fields="files(id, name)",
        pageSize=100
    ).execute()
    
    files = response.get('files', [])
    if not files:
        print("No more files found.")
        break
    
    for f in files:
        try:
            drive.files().delete(fileId=f['id']).execute()
            print(f"  Deleted: {f['name']} ({f['id']})")
            deleted += 1
        except Exception as e:
            print(f"  Error deleting {f['id']}: {e}")

# Empty trash
try:
    drive.files().emptyTrash().execute()
    print("Trash emptied.")
except Exception as e:
    print(f"Could not empty trash: {e}")

print(f"\nDone! Deleted {deleted} file(s).")
sys.stdout.flush()
