"""Generate summaries for recent meetings without summaries"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from hybrid_summarizer import HybridSummarizer
from logger import get_logger

logger = get_logger("generate_summaries")

async def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')
    client = create_client(url, key)

    # Get meetings without summaries (recent 3)
    print("=== Finding meetings without summaries ===")

    # Get all summaries
    summaries = client.table('meeting_summaries').select('meeting_id').execute()
    summary_ids = {s['meeting_id'] for s in summaries.data}

    # Get completed meetings with transcripts, ordered by created_at desc
    meetings = client.table('meetings').select('id, title').eq('status', 'completed').order('created_at', desc=True).execute()

    # Find meetings with transcripts but no summary
    targets = []
    for m in meetings.data:
        if m['id'] in summary_ids:
            continue
        # Check if has transcripts
        t = client.table('transcripts').select('id', count='exact').eq('meeting_id', m['id']).execute()
        if t.count and t.count > 0:
            targets.append(m)
            if len(targets) >= 3:
                break

    if not targets:
        print("No meetings need summaries!")
        return

    print(f"Found {len(targets)} meetings to process:")
    for t in targets:
        print(f"  - {t['id'][:8]}... : {t['title']}")

    # Initialize summarizer
    print("\n=== Initializing HybridSummarizer ===")
    summarizer = HybridSummarizer()
    print("Summarizer initialized!")

    # Process each meeting
    for meeting in targets:
        meeting_id = meeting['id']
        title = meeting['title']
        print(f"\n=== Processing: {title} ===")

        # Get transcripts
        transcripts = client.table('transcripts').select('*').eq('meeting_id', meeting_id).order('start_time').execute()

        if not transcripts.data:
            print(f"  No transcripts found, skipping...")
            continue

        # Build full transcript text
        full_text = ""
        for seg in transcripts.data:
            speaker = seg.get('speaker_label', 'Unknown')
            text = seg.get('text', '')
            full_text += f"[{speaker}]: {text}\n"

        print(f"  Transcript length: {len(full_text)} chars, {len(transcripts.data)} segments")

        # Generate summary
        print(f"  Generating summary...")
        try:
            result = summarizer.summarize(full_text, verbose=True)

            if result:
                # HybridSummary -> meeting_summaries table mapping
                # Build summary text from timeline_summaries and agenda_items
                summary_parts = []
                if result.agenda_items:
                    summary_parts.append("## 주요 안건")
                    for item in result.agenda_items[:5]:
                        title = item.get('title', '')
                        summary_parts.append(f"- {title}")
                if result.timeline_summaries:
                    summary_parts.append("\n## 회의 진행")
                    for ts in result.timeline_summaries[:5]:
                        summary_parts.append(f"- {ts.get('summary', '')}")

                summary_text = "\n".join(summary_parts) if summary_parts else result.raw_text[:500]

                summary_data = {
                    'meeting_id': meeting_id,
                    'summary': summary_text,
                    'key_points': result.main_topics[:10],
                    'action_items': result.action_items[:10],
                    'topics': result.main_topics[:5],
                }

                client.table('meeting_summaries').insert(summary_data).execute()
                print(f"  SUCCESS! Summary saved.")
                print(f"  Topics: {result.main_topics[:3]}")
                print(f"  Actions: {result.action_items[:2]}")
            else:
                print(f"  FAILED: No summary generated")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n=== Done! ===")

if __name__ == "__main__":
    asyncio.run(main())
