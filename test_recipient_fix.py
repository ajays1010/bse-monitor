#!/usr/bin/env python3
"""
Test script to verify the fix for add_user_recipient function
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import database as db

def test_recipient_fix():
    """Test the updated add_user_recipient function returns proper error messages"""
    
    user_id = "877ec22a-df31-4bf3-86b1-1b76e4293abf"
    chat_id = "453652457"  # This chat_id is already used by another user
    
    # Initialize Firebase
    db.initialize_firebase()
    
    # Get service client
    sb_client = db.get_supabase_client(service_role=True)
    if not sb_client:
        print("❌ Failed to get Supabase client")
        return
    
    print(f"🧪 Testing add_user_recipient fix for user {user_id} with chat_id {chat_id}")
    print(f"   (This chat_id is already used by another user, should get proper error message)")
    
    # Test the updated function
    result = db.add_user_recipient(sb_client, user_id, chat_id)
    
    print(f"\n📋 Result from add_user_recipient:")
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")
    
    if not result['success']:
        print(f"\n✅ Fix working correctly - user gets clear error message about constraint")
    else:
        print(f"\n❌ Unexpected success - this should have failed due to unique constraint")

if __name__ == "__main__":
    test_recipient_fix()