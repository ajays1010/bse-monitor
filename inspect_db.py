#!/usr/bin/env python3
"""
Quick script to inspect database content for the specific user
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import database as db

def inspect_user_data():
    """Inspect database content for user 877ec22a-df31-4bf3-86b1-1b76e4293abf"""
    
    user_id = "877ec22a-df31-4bf3-86b1-1b76e4293abf"
    
    # Initialize Firebase
    db.initialize_firebase()
    
    # Get service client
    sb_client = db.get_supabase_client(service_role=True)
    if not sb_client:
        print("❌ Failed to get Supabase client")
        return
    
    print(f"🔍 Inspecting data for user: {user_id}\n")
    
    # Check all recipients in the table (to see if any exist)
    print("📋 ALL recipients in telegram_recipients table:")
    try:
        all_recipients = sb_client.table('telegram_recipients').select('*').execute()
        print(f"Total recipients in database: {len(all_recipients.data)}")
        for r in all_recipients.data:
            print(f"  - User: {r['user_id']}, Chat: {r['chat_id']}")
    except Exception as e:
        print(f"❌ Error getting all recipients: {e}")
    
    print()
    
    # Check recipients for this specific user
    print(f"📋 Recipients for user {user_id}:")
    try:
        user_recipients = db.get_user_recipients(sb_client, user_id)
        print(f"Found {len(user_recipients)} recipients: {user_recipients}")
    except Exception as e:
        print(f"❌ Error getting user recipients: {e}")
    
    print()
    
    # Check if there's a recipient with chat_id 453652457 anywhere
    print("🔍 Searching for chat_id 453652457 anywhere in database:")
    try:
        search_result = sb_client.table('telegram_recipients').select('*').eq('chat_id', '453652457').execute()
        print(f"Found {len(search_result.data)} entries with chat_id 453652457:")
        for r in search_result.data:
            print(f"  - User: {r['user_id']}, Chat: {r['chat_id']}, Created: {r.get('created_at', 'N/A')}")
    except Exception as e:
        print(f"❌ Error searching for chat_id: {e}")

if __name__ == "__main__":
    inspect_user_data()