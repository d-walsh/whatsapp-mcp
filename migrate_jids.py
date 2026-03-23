#!/usr/bin/env python3
"""
migrate_jids.py — One-time migration to merge split chats caused by the
LID/phone JID split bug.

WhatsApp migrates contacts from phone-based JIDs (@s.whatsapp.net) to
LID-based JIDs (@lid). Before the normalization fix, the Go bridge stored
messages under whatever JID WhatsApp sent — so the same conversation could
be split into two separate rows in the `chats` table and two groups of rows
in the `messages` table.

This script:
1. Backs up the SQLite database
2. For each phone-JID chat that has a LID equivalent (via /api/resolve-jid):
   a. Ensures the LID chat row exists in `chats`
   b. Re-parents all messages from phone JID → LID JID
   c. Re-parents all reactions from phone JID → LID JID
   d. Deletes the now-empty phone JID chat row
3. Reports a summary of what was merged

Usage:
    python3 migrate_jids.py [--db PATH] [--api URL] [--dry-run]

Options:
    --db      Path to messages.db (default: whatsapp-bridge/store/messages.db)
    --api     Bridge API base URL (default: http://localhost:8081/api)
    --dry-run Print what would be changed without modifying the database
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

import requests


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--db",
        default=os.path.join(os.path.dirname(__file__), "whatsapp-bridge", "store", "messages.db"),
        help="Path to messages.db",
    )
    parser.add_argument(
        "--api",
        default="http://localhost:8081/api",
        help="Bridge API base URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without modifying the database",
    )
    return parser.parse_args()


def resolve_phone_to_lid(api_base: str, phone_jid: str) -> str | None:
    """Call /api/resolve-jid to get LID for a phone JID. Returns None if no mapping."""
    try:
        resp = requests.get(f"{api_base}/resolve-jid", params={"jid": phone_jid}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("lid")  # None if no mapping
    except Exception as e:
        print(f"  Warning: resolve-jid request failed for {phone_jid}: {e}")
    return None


def backup_db(db_path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{ts}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def get_phone_chats(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Return all non-group chats stored under phone JIDs (@s.whatsapp.net)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT jid, name, last_message_time
        FROM chats
        WHERE jid LIKE '%@s.whatsapp.net'
        ORDER BY last_message_time DESC
    """)
    return cursor.fetchall()


def chat_exists(conn: sqlite3.Connection, jid: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM chats WHERE jid = ?", (jid,))
    return cursor.fetchone() is not None


def merge_chat(conn: sqlite3.Connection, phone_jid: str, lid_jid: str, phone_name: str, phone_last_time: str, dry_run: bool) -> dict:
    """Merge all data from phone_jid into lid_jid. Returns counts of rows affected."""
    cursor = conn.cursor()

    # Count messages and reactions we'll be moving
    cursor.execute("SELECT COUNT(*) FROM messages WHERE chat_jid = ?", (phone_jid,))
    msg_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reactions WHERE target_chat_jid = ?", (phone_jid,))
    reaction_count = cursor.fetchone()[0]

    if dry_run:
        print(f"  [dry-run] Would merge {phone_jid} → {lid_jid}: {msg_count} messages, {reaction_count} reactions")
        return {"messages": msg_count, "reactions": reaction_count}

    # Ensure LID chat row exists (upsert: keep existing name/time if better)
    if not chat_exists(conn, lid_jid):
        cursor.execute(
            "INSERT INTO chats (jid, name, last_message_time) VALUES (?, ?, ?)",
            (lid_jid, phone_name, phone_last_time),
        )
    else:
        # Update last_message_time to whichever is more recent
        cursor.execute("""
            UPDATE chats
            SET last_message_time = MAX(last_message_time, ?)
            WHERE jid = ?
        """, (phone_last_time, lid_jid))
        # If LID chat has no name but phone chat does, copy it
        if phone_name:
            cursor.execute("""
                UPDATE chats SET name = ?
                WHERE jid = ? AND (name IS NULL OR name = '')
            """, (phone_name, lid_jid))

    # Re-parent messages: phone_jid → lid_jid
    # Use INSERT OR REPLACE to handle any (id, chat_jid) PK conflicts gracefully
    cursor.execute("""
        INSERT OR REPLACE INTO messages
            (id, chat_jid, sender, content, timestamp, is_from_me,
             media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length)
        SELECT
            id, ? as chat_jid, sender, content, timestamp, is_from_me,
            media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length
        FROM messages
        WHERE chat_jid = ?
    """, (lid_jid, phone_jid))

    # Re-parent reactions
    cursor.execute("""
        INSERT OR REPLACE INTO reactions
            (target_message_id, target_chat_jid, reactor_sender, reaction_text, timestamp)
        SELECT
            target_message_id, ? as target_chat_jid, reactor_sender, reaction_text, timestamp
        FROM reactions
        WHERE target_chat_jid = ?
    """, (lid_jid, phone_jid))

    # Delete old phone-JID messages and reactions (they're now under lid_jid)
    cursor.execute("DELETE FROM messages WHERE chat_jid = ?", (phone_jid,))
    cursor.execute("DELETE FROM reactions WHERE target_chat_jid = ?", (phone_jid,))

    # Delete the phone-JID chat row
    cursor.execute("DELETE FROM chats WHERE jid = ?", (phone_jid,))

    return {"messages": msg_count, "reactions": reaction_count}


def main():
    args = parse_args()

    if not os.path.exists(args.db):
        print(f"Error: database not found at {args.db}")
        sys.exit(1)

    print(f"Database: {args.db}")
    print(f"API:      {args.api}")
    print(f"Dry-run:  {args.dry_run}")
    print()

    # Verify bridge is reachable
    try:
        resp = requests.get(f"{args.api}/resolve-jid", params={"jid": "test@s.whatsapp.net"}, timeout=5)
        print(f"Bridge reachable (HTTP {resp.status_code})")
    except Exception as e:
        print(f"Error: bridge not reachable at {args.api}: {e}")
        print("The bridge must be running to perform JID resolution.")
        sys.exit(1)

    # Back up the database (even for dry-run, it's harmless and reassuring)
    if not args.dry_run:
        backup_path = backup_db(args.db)
        print(f"Backup created: {backup_path}")
    print()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = OFF")  # We manage FK integrity manually

    try:
        phone_chats = get_phone_chats(conn)
        print(f"Found {len(phone_chats)} phone-JID chats to evaluate\n")

        merged = 0
        skipped_no_lid = 0
        total_messages = 0
        total_reactions = 0

        for phone_jid, name, last_time in phone_chats:
            print(f"Checking: {phone_jid} ({name or 'no name'})")
            lid_jid = resolve_phone_to_lid(args.api, phone_jid)

            if not lid_jid:
                print(f"  → No LID mapping found, skipping (contact not yet migrated)")
                skipped_no_lid += 1
                continue

            print(f"  → LID: {lid_jid}")
            counts = merge_chat(conn, phone_jid, lid_jid, name, last_time, args.dry_run)
            total_messages += counts["messages"]
            total_reactions += counts["reactions"]
            merged += 1

        if not args.dry_run:
            conn.commit()

        print()
        print("=" * 50)
        print(f"Summary:")
        print(f"  Chats merged:            {merged}")
        print(f"  Chats skipped (no LID):  {skipped_no_lid}")
        print(f"  Messages re-parented:    {total_messages}")
        print(f"  Reactions re-parented:   {total_reactions}")
        if args.dry_run:
            print()
            print("Dry-run complete. No changes made.")
        else:
            print()
            print("Migration complete.")

    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


if __name__ == "__main__":
    main()
