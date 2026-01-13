import uuid
import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load env
from dotenv import load_dotenv

load_dotenv()

from supabase_client import get_supabase_client
from models import MeetingStatus


async def run_pipeline_test():
    supabase = get_supabase_client()

    # 1. Check/Generate Audio
    audio_file = Path("test_audio.wav")
    if not audio_file.exists():
        print("Error: test_audio.wav not found. Run generate_dummy_audio.py first.")
        return

    print("=" * 60)
    print("[TEST] Triggering End-to-End Pipeline Test")
    print("=" * 60)

    # 2. Upload Audio
    # Get a valid user_id from DB
    try:
        existing_meeting = (
            supabase.client.table("meetings").select("user_id").limit(1).execute()
        )
        if existing_meeting.data:
            user_id = existing_meeting.data[0]["user_id"]
            print(f"   Using existing User UUID: {user_id}")
        else:
            print("   [FAIL] No existing users found in 'meetings' table to test with.")
            # Fallback to a hardcoded ID if you know one, otherwise this will fail
            return
    except Exception as e:
        print(f"   [FAIL] Could not fetch existing user: {e}")
        return

    meeting_id = str(uuid.uuid4())
    print(f"   Generated Meeting UUID: {meeting_id}")

    storage_path = f"users/{user_id}/meetings/{meeting_id}/test_audio.wav"

    print(f"1. Uploading audio to 'recordings' bucket...")
    print(f"   Path: {storage_path}")

    with open(audio_file, "rb") as f:
        file_bytes = f.read()

    try:
        # Upload binary
        res = supabase.client.storage.from_("recordings").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "audio/wav", "upsert": "true"},
        )
        print("   [OK] Upload successful")
    except Exception as e:
        print(f"   [FAIL] Upload failed: {e}")
        return

    # Construct public URL (mimicking Flutter app behavior)
    # Start with base URL from env (assuming it's loaded)
    supabase_url = os.getenv("SUPABASE_URL")
    # publicUrl format: {supabaseUrl}/storage/v1/object/public/{bucket}/{path}
    audio_url = f"{supabase_url}/storage/v1/object/public/recordings/{storage_path}"
    print(f"   Generated Audio URL: {audio_url}")

    # 3. Create Meeting Record
    print(f"2. Creating meeting record (Status: PENDING)...")
    meeting_data = {
        "id": meeting_id,
        "user_id": user_id,
        "title": "Pipeline Test Meeting",
        "status": "pending",
        "audio_url": audio_url,
        "metadata": {
            "storage_path": storage_path,
            "file_size": 0,
            "upload_started_at": datetime.now().isoformat(),
            "upload_completed_at": datetime.now().isoformat(),
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    try:
        data = supabase.client.table("meetings").insert(meeting_data).execute()
        print(f"   [OK] Meeting created: {meeting_id}")
    except Exception as e:
        print(f"   [FAIL] DB Insert failed: {e}")
        return

    # 4. Monitor Status
    print(f"3. Monitoring status (Timeout: 300s)...")
    start_time = time.time()
    last_status = "pending"

    while (time.time() - start_time) < 300:
        try:
            # Poll meeting status
            response = (
                supabase.client.table("meetings")
                .select("*")
                .eq("id", meeting_id)
                .single()
                .execute()
            )
            meeting = response.data
            current_status = meeting["status"]

            if current_status != last_status:
                print(f"   [STATUS] Status changed: {last_status} -> {current_status}")
                last_status = current_status

            if current_status == "processing":
                sys.stdout.write(".")
                sys.stdout.flush()

            if current_status == "completed":
                print("\n   [OK] Pipeline COMPLETED successfully!")
                # Print results
                transcripts = (
                    supabase.client.table("transcripts")
                    .select("*")
                    .eq("meeting_id", meeting_id)
                    .execute()
                )
                print(f"   - Transcripts: {len(transcripts.data)} segments")

                summary = (
                    supabase.client.table("meeting_summaries")
                    .select("*")
                    .eq("meeting_id", meeting_id)
                    .execute()
                )
                if summary.data:
                    print(f"   - Summary generated: Yes")
                else:
                    print(f"   - No summary found")
                return

            if current_status == "failed":
                print(f"\n   [FAIL] Pipeline FAILED")
                print(f"   Error: {meeting.get('error_message')}")
                return

            time.sleep(2)

        except Exception as e:
            print(f"Error polling status: {e}")
            time.sleep(2)

    print("\n[FAIL] Test Timed Out")


if __name__ == "__main__":
    asyncio.run(run_pipeline_test())
