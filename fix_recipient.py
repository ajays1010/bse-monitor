#!/usr/bin/env python3
"""
Script to add recipient 453652457 to user 877ec22a-df31-4bf3-86b1-1b76e4293abf
This handles the case where the chat_id might already exist for another user
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import database as db

def fix_recipient_issue():
    """Add the recipient properly by handling existing constraints"""
    
    user_id = "877ec22a-df31-4bf3-86b1-1b76e4293abf"
    chat_id = "453652457"
    
    # Initialize Firebase
    db.initialize_firebase()
    
    # Get service client
    sb_client = db.get_supabase_client(service_role=True)
    if not sb_client:
        print("❌ Failed to get Supabase client")
        return
    
    print(f"🔧 Attempting to add chat_id {chat_id} to user {user_id}")
    
    # Check if this exact pair already exists
    try:
        existing = (
            sb_client.table('telegram_recipients')
            .select('user_id')
            .eq('user_id', user_id)
            .eq('chat_id', chat_id)
            .limit(1)
            .execute()
        )
        
        if existing.data:
            print(f"✅ Recipient {chat_id} already exists for this user")
            return
        
        print(f"ℹ️  Recipient {chat_id} does not exist for this user, attempting to add...")
        
        # Try direct insert, bypassing the existing logic
        result = sb_client.table('telegram_recipients').insert({
            'user_id': user_id, 
            'chat_id': chat_id
        }).execute()
        
        print(f"✅ Successfully added recipient {chat_id} to user {user_id}")
        
        # Verify the addition
        recipients = db.get_user_recipients(sb_client, user_id)
        print(f"✅ Verification: User now has {len(recipients)} recipients: {recipients}")
        
    except Exception as e:
        error_msg = str(e).lower()
        if '409' in error_msg or 'conflict' in error_msg or 'unique' in error_msg:
            print(f"⚠️  Database constraint prevents adding this chat_id")
            print(f"   This suggests chat_id {chat_id} has a unique constraint in the database schema")
            print(f"   The same Telegram chat_id cannot be used by multiple users")
            print(f"   Solution: The user needs to use a different Telegram chat_id")
        else:
            print(f"❌ Error adding recipient: {e}")

if __name__ == "__main__":
    fix_recipient_issue()