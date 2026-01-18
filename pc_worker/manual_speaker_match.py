#!/usr/bin/env python3
"""
Manual Speaker Matching CLI Tool

Match temporary speakers (SPEAKER_00, SPEAKER_01) to pre-registered speakers
by copying their voice embeddings.

Usage:
    python manual_speaker_match.py SPEAKER_00 "김석" -m <meeting_id>
    python manual_speaker_match.py --list-temp -m <meeting_id>
    python manual_speaker_match.py --list-registered
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, logger


class ManualSpeakerMatchCLI:
    """CLI for manually matching speakers"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._user_id: Optional[str] = None

    async def _get_user_id(self) -> str:
        """Get default user ID from profiles table"""
        if self._user_id:
            return self._user_id

        response = await asyncio.to_thread(
            lambda: self.client.table("profiles")
            .select("id")
            .limit(1)
            .execute()
        )

        if response.data:
            self._user_id = response.data[0]["id"]
            return self._user_id
        raise ValueError("No user found in profiles table")

    async def list_temp_speakers(
        self, meeting_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List temporary speakers from a meeting (SPEAKER_XX format)

        Args:
            meeting_id: Meeting ID to search for speakers
            user_id: User ID (uses default if not provided)

        Returns:
            List of temporary speakers with embeddings
        """
        if not user_id:
            user_id = await self._get_user_id()

        # Get speakers that have SPEAKER_XX pattern names
        response = await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .select("id, name, voice_embedding, created_at")
            .eq("user_id", user_id)
            .eq("is_registered", False)
            .like("name", "SPEAKER_%")
            .execute()
        )

        speakers = response.data or []

        # Filter to only those with embeddings (from actual meetings)
        speakers_with_embedding = [s for s in speakers if s.get("voice_embedding")]

        if not speakers_with_embedding:
            print(f"No temporary speakers with embeddings found for meeting {meeting_id}")
            return []

        print(f"\nTemporary Speakers (from recent meetings)")
        print("=" * 50)
        print(f"{'Name':<15} {'Has Embedding':<15} {'Created':<12}")
        print("-" * 50)

        for speaker in speakers_with_embedding:
            name = speaker["name"]
            has_emb = "Yes" if speaker.get("voice_embedding") else "No"
            created = speaker["created_at"][:10] if speaker.get("created_at") else "-"
            print(f"{name:<15} {has_emb:<15} {created:<12}")

        print("=" * 50)
        return speakers_with_embedding

    async def list_registered_speakers(
        self, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all pre-registered speakers

        Args:
            user_id: User ID (uses default if not provided)

        Returns:
            List of registered speakers
        """
        if not user_id:
            user_id = await self._get_user_id()

        response = await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .select("id, name, title, voice_embedding")
            .eq("user_id", user_id)
            .eq("is_registered", True)
            .order("name")
            .execute()
        )

        speakers = response.data or []

        if not speakers:
            print("No pre-registered speakers found.")
            print("Use 'python preregister_speakers.py bulk speakers_preregistered.json' to add speakers.")
            return []

        print(f"\nPre-registered Speakers ({len(speakers)} total)")
        print("=" * 60)
        print(f"{'Name':<15} {'Title':<12} {'Voice Profile':<15}")
        print("-" * 60)

        for speaker in speakers:
            name = speaker["name"]
            title = speaker.get("title") or "-"
            has_voice = "Yes (ready)" if speaker.get("voice_embedding") else "No (need match)"
            print(f"{name:<15} {title:<12} {has_voice:<15}")

        print("=" * 60)
        return speakers

    async def match_speaker(
        self,
        source_name: str,
        target_name: str,
        meeting_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Copy voice embedding from temporary speaker to registered speaker

        Args:
            source_name: Temporary speaker name (e.g., SPEAKER_00)
            target_name: Registered speaker name (e.g., 김석)
            meeting_id: Optional meeting ID to filter source speaker
            user_id: User ID (uses default if not provided)

        Returns:
            True if matching succeeded
        """
        if not user_id:
            user_id = await self._get_user_id()

        print(f"\nMatching: {source_name} -> {target_name}")
        print("-" * 40)

        # Find source speaker (temporary)
        source_query = (
            self.client.table("speakers")
            .select("id, name, voice_embedding, embedding_model, embedding_confidence")
            .eq("user_id", user_id)
            .eq("name", source_name)
        )

        source_response = await asyncio.to_thread(lambda: source_query.execute())

        if not source_response.data:
            print(f"[X] Source speaker not found: {source_name}")
            return False

        source = source_response.data[0]

        if not source.get("voice_embedding"):
            print(f"[X] Source speaker has no voice embedding: {source_name}")
            return False

        print(f"  Found source: {source_name} (embedding available)")

        # Find target speaker (registered)
        target_response = await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .select("id, name, title, voice_embedding")
            .eq("user_id", user_id)
            .eq("name", target_name)
            .eq("is_registered", True)
            .execute()
        )

        if not target_response.data:
            print(f"[X] Target speaker not found (must be pre-registered): {target_name}")
            print("    Use 'python preregister_speakers.py add \"{target_name}\"' first")
            return False

        target = target_response.data[0]
        title_str = f" ({target.get('title')})" if target.get("title") else ""
        print(f"  Found target: {target_name}{title_str}")

        if target.get("voice_embedding"):
            print(f"  [!] Warning: {target_name} already has a voice profile. Overwriting...")

        # Copy embedding using direct update
        update_data = {
            "voice_embedding": source["voice_embedding"],
            "embedding_model": source.get("embedding_model", "pyannote/embedding"),
            "embedding_confidence": source.get("embedding_confidence"),
            "last_embedding_updated": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .update(update_data)
            .eq("id", target["id"])
            .execute()
        )

        print(f"\n[OK] Successfully matched {source_name} -> {target_name}")
        print(f"     {target_name}{title_str} now has a voice profile for automatic recognition")

        return True

    async def match_speaker_rpc(
        self,
        source_id: str,
        target_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Copy voice embedding using RPC function

        Args:
            source_id: Source speaker UUID
            target_id: Target speaker UUID
            user_id: User ID (uses default if not provided)

        Returns:
            True if matching succeeded
        """
        if not user_id:
            user_id = await self._get_user_id()

        response = await asyncio.to_thread(
            lambda: self.client.rpc(
                "copy_speaker_embedding",
                {
                    "p_source_speaker_id": source_id,
                    "p_target_speaker_id": target_id,
                    "p_user_id": user_id,
                }
            ).execute()
        )

        return response.data is True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Manually match temporary speakers to pre-registered speakers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s SPEAKER_00 "김석"              # Match SPEAKER_00 to 김석
  %(prog)s SPEAKER_01 "강창근" -m abc123   # Match with meeting ID filter
  %(prog)s --list-temp -m abc123           # List temp speakers from meeting
  %(prog)s --list-registered               # List all registered speakers

Workflow:
  1. Process a meeting: python meeting_pipeline.py ../data/meeting.m4a
  2. List temp speakers: python manual_speaker_match.py --list-temp -m <meeting_id>
  3. Match speakers:     python manual_speaker_match.py SPEAKER_00 "김석"
  4. Verify:             python preregister_speakers.py list
        """,
    )

    # Positional arguments for matching
    parser.add_argument(
        "source", nargs="?", help="Source speaker name (e.g., SPEAKER_00)"
    )
    parser.add_argument(
        "target", nargs="?", help="Target registered speaker name (e.g., 김석)"
    )

    # Optional flags
    parser.add_argument(
        "-m", "--meeting-id", help="Meeting ID to filter speakers"
    )
    parser.add_argument(
        "--list-temp", action="store_true", help="List temporary speakers"
    )
    parser.add_argument(
        "--list-registered", action="store_true", help="List pre-registered speakers"
    )

    args = parser.parse_args()

    cli = ManualSpeakerMatchCLI()

    async def run():
        if args.list_temp:
            if not args.meeting_id:
                print("Warning: No meeting ID provided. Showing all temporary speakers.")
            await cli.list_temp_speakers(args.meeting_id or "")
        elif args.list_registered:
            await cli.list_registered_speakers()
        elif args.source and args.target:
            await cli.match_speaker(args.source, args.target, args.meeting_id)
        else:
            parser.print_help()

    asyncio.run(run())


if __name__ == "__main__":
    main()
