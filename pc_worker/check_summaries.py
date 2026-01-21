"""Check transcripts and summaries in Supabase"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
client = create_client(url, key)

# Check completed meetings with transcript counts
print('=== Completed meetings with transcripts ===')
meetings = client.table('meetings').select('id, title, status, created_at').eq('status', 'completed').order('created_at', desc=True).execute()
print(f'Total completed: {len(meetings.data)}')

# Get summaries
summaries = client.table('meeting_summaries').select('meeting_id').execute()
summary_ids = {s['meeting_id'] for s in summaries.data}

for m in meetings.data:
    mid = m['id']
    # Count transcripts for this meeting
    transcripts = client.table('transcripts').select('id', count='exact').eq('meeting_id', mid).execute()
    t_count = transcripts.count if transcripts.count else 0

    has_summary = 'S' if mid in summary_ids else '-'
    has_transcript = 'T' if t_count > 0 else '-'

    title = m['title'][:30] if m['title'] else 'Untitled'
    print(f'  [{has_transcript}][{has_summary}] {mid[:8]}... | {t_count:3d} segs | {title}')
