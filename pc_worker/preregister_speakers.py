#!/usr/bin/env python3
"""
Speaker Pre-registration CLI Tool

Manage pre-registered speakers for automatic recognition in meetings.

Usage:
    python preregister_speakers.py add "김석" -t "학장"
    python preregister_speakers.py bulk ../data/speakers_preregistered.json
    python preregister_speakers.py list
    python preregister_speakers.py delete "김석"
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, logger


class SpeakerPreregistrationCLI:
    """CLI for managing pre-registered speakers"""

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

    async def add_speaker(
        self, name: str, title: Optional[str] = None, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a single pre-registered speaker

        Args:
            name: Speaker's name
            title: Job title (optional)
            user_id: User ID (uses default if not provided)

        Returns:
            Created speaker data
        """
        if not user_id:
            user_id = await self._get_user_id()

        # Check if speaker already exists
        existing = await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .select("id, name, title, is_registered")
            .eq("user_id", user_id)
            .eq("name", name)
            .eq("is_registered", True)
            .execute()
        )

        if existing.data:
            speaker = existing.data[0]
            print(f"  [!] Speaker already exists: {name}")
            if title and speaker.get("title") != title:
                # Update title if different
                await asyncio.to_thread(
                    lambda: self.client.table("speakers")
                    .update({"title": title, "updated_at": datetime.now().isoformat()})
                    .eq("id", speaker["id"])
                    .execute()
                )
                print(f"      Updated title: {title}")
            return speaker

        # Create new speaker
        speaker_data = {
            "user_id": user_id,
            "name": name,
            "title": title,
            "is_registered": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        response = await asyncio.to_thread(
            lambda: self.client.table("speakers").insert(speaker_data).execute()
        )

        if response.data:
            speaker = response.data[0]
            title_str = f" ({title})" if title else ""
            print(f"  [+] Added: {name}{title_str}")
            return speaker

        raise ValueError(f"Failed to create speaker: {name}")

    async def bulk_add_speakers(self, json_path: Path) -> List[Dict[str, Any]]:
        """
        Add multiple speakers from JSON file

        Args:
            json_path: Path to JSON file with speakers list

        Returns:
            List of created/updated speakers
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        speakers_data = data.get("speakers", [])
        if not speakers_data:
            print("No speakers found in JSON file")
            return []

        print(f"Processing {len(speakers_data)} speakers from {json_path.name}...")
        print("-" * 40)

        results = []
        for speaker_info in speakers_data:
            name = speaker_info.get("name")
            title = speaker_info.get("title")
            if name:
                result = await self.add_speaker(name, title)
                results.append(result)

        print("-" * 40)
        print(f"Total: {len(results)} speakers processed")
        return results

    async def list_speakers(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all pre-registered speakers

        Args:
            user_id: User ID (uses default if not provided)

        Returns:
            List of speakers
        """
        if not user_id:
            user_id = await self._get_user_id()

        response = await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .select("id, name, title, is_registered, voice_embedding, created_at")
            .eq("user_id", user_id)
            .eq("is_registered", True)
            .order("name")
            .execute()
        )

        speakers = response.data or []

        if not speakers:
            print("No pre-registered speakers found.")
            return []

        print(f"\nPre-registered Speakers ({len(speakers)} total)")
        print("=" * 60)
        print(f"{'Name':<15} {'Title':<12} {'Voice':<8} {'Created':<12}")
        print("-" * 60)

        for speaker in speakers:
            name = speaker["name"]
            title = speaker.get("title") or "-"
            has_voice = "yes" if speaker.get("voice_embedding") else "no"
            created = speaker["created_at"][:10] if speaker.get("created_at") else "-"

            # Voice profile icon
            voice_icon = "yes" if has_voice == "yes" else "no"

            print(f"{name:<15} {title:<12} {voice_icon:<8} {created:<12}")

        print("=" * 60)
        return speakers

    async def delete_speaker(
        self, name: str, user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a pre-registered speaker

        Args:
            name: Speaker's name
            user_id: User ID (uses default if not provided)

        Returns:
            True if deleted successfully
        """
        if not user_id:
            user_id = await self._get_user_id()

        # Find speaker
        existing = await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .select("id, name")
            .eq("user_id", user_id)
            .eq("name", name)
            .eq("is_registered", True)
            .execute()
        )

        if not existing.data:
            print(f"Speaker not found: {name}")
            return False

        speaker_id = existing.data[0]["id"]

        # Delete speaker
        await asyncio.to_thread(
            lambda: self.client.table("speakers")
            .delete()
            .eq("id", speaker_id)
            .execute()
        )

        print(f"Deleted speaker: {name}")
        return True

    async def get_preregistered_rpc(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get pre-registered speakers using RPC function

        Args:
            user_id: User ID (uses default if not provided)

        Returns:
            List of speakers from RPC
        """
        if not user_id:
            user_id = await self._get_user_id()

        response = await asyncio.to_thread(
            lambda: self.client.rpc(
                "get_preregistered_speakers",
                {"p_user_id": user_id}
            ).execute()
        )

        return response.data or []


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Manage pre-registered speakers for meeting recognition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add "김석" -t "학장"       # Add speaker with title
  %(prog)s add "홍길동"               # Add speaker without title
  %(prog)s bulk speakers_preregistered.json  # Bulk add from JSON
  %(prog)s list                       # List all speakers
  %(prog)s delete "김석"              # Delete a speaker
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a single speaker")
    add_parser.add_argument("name", help="Speaker's name")
    add_parser.add_argument("-t", "--title", help="Job title (e.g., 학장, 부학장)")

    # Bulk command
    bulk_parser = subparsers.add_parser("bulk", help="Bulk add from JSON file")
    bulk_parser.add_argument("json_file", type=Path, help="Path to JSON file")

    # List command
    subparsers.add_parser("list", help="List all pre-registered speakers")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a speaker")
    delete_parser.add_argument("name", help="Speaker's name to delete")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = SpeakerPreregistrationCLI()

    async def run():
        if args.command == "add":
            await cli.add_speaker(args.name, args.title)
        elif args.command == "bulk":
            if not args.json_file.exists():
                print(f"File not found: {args.json_file}")
                return
            await cli.bulk_add_speakers(args.json_file)
        elif args.command == "list":
            await cli.list_speakers()
        elif args.command == "delete":
            await cli.delete_speaker(args.name)

    asyncio.run(run())


if __name__ == "__main__":
    main()
