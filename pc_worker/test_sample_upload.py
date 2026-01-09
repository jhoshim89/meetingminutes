"""
Test script to upload sample audio and create pending meeting record
"""
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Config
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SAMPLE_FILE = Path("D:/Productions/meetingminutes/data/sampledata.m4a")

def main():
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Sample file: {SAMPLE_FILE}")
    print(f"File exists: {SAMPLE_FILE.exists()}")

    if not SAMPLE_FILE.exists():
        print("ERROR: Sample file not found!")
        return

    file_size = SAMPLE_FILE.stat().st_size / 1024 / 1024
    print(f"File size: {file_size:.2f} MB")

    # Create Supabase client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client created")

    # Get or create test user using Supabase Auth Admin API
    print("\n0. Getting/creating test user...")
    test_user_id = None
    try:
        # List existing auth users (requires service_role key)
        users_response = client.auth.admin.list_users()
        if users_response:
            test_user_id = users_response[0].id
            print(f"   Using existing auth user: {test_user_id}")
    except Exception as e:
        print(f"   List users error: {e}")

    # If no users exist, create one
    if not test_user_id:
        try:
            print("   Creating test auth user...")
            new_user = client.auth.admin.create_user({
                "email": "test@meetingminutes.local",
                "password": "testpassword123",
                "email_confirm": True
            })
            test_user_id = new_user.user.id
            print(f"   Created test user: {test_user_id}")
        except Exception as e:
            print(f"   Create user error: {e}")
            return

    # Generate unique ID
    meeting_id = str(uuid.uuid4())
    storage_path = f"test/{meeting_id}.m4a"

    print(f"\nMeeting ID: {meeting_id}")
    print(f"Storage path: {storage_path}")

    # Upload file to storage
    print("\n1. Uploading audio file to storage...")
    try:
        with open(SAMPLE_FILE, 'rb') as f:
            response = client.storage.from_('recordings').upload(
                storage_path,
                f,
                file_options={"content-type": "audio/mp4"}
            )
        print(f"   Upload successful!")
    except Exception as e:
        print(f"   Upload error: {e}")
        # Try to continue - bucket might need to be created
        if "Bucket not found" in str(e):
            print("   Creating 'recordings' bucket...")
            client.storage.create_bucket('recordings', {'public': False})
            with open(SAMPLE_FILE, 'rb') as f:
                client.storage.from_('recordings').upload(
                    storage_path,
                    f,
                    file_options={"content-type": "audio/mp4"}
                )
            print("   Upload successful after bucket creation!")

    # Create meeting record
    print("\n2. Creating meeting record...")
    meeting_data = {
        'id': meeting_id,
        'title': 'Test Sample Recording',
        'status': 'pending',
        'audio_url': storage_path,  # Worker generates signed URL from this path
        'user_id': test_user_id,
        'created_at': datetime.now().isoformat(),
    }

    try:
        response = client.table('meetings').insert(meeting_data).execute()
        print(f"   Meeting record created!")
        print(f"   Response: {response.data}")
    except Exception as e:
        print(f"   Error creating meeting: {e}")
        return

    print("\n" + "="*50)
    print("SUCCESS! Worker should pick up this meeting soon.")
    print(f"Meeting ID: {meeting_id}")
    print("="*50)

if __name__ == "__main__":
    main()
