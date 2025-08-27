#!/usr/bin/env python3
"""
Debug script to test telegram recipients functionality
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

def test_recipients_functionality():
    """Test if recipients are being added and retrieved correctly"""
    print("🔍 Testing Telegram Recipients Functionality...")
    
    # Import database functions
    import database as db
    
    # Initialize Firebase
    db.initialize_firebase()
    
    # Get a service client
    sb_client = db.get_supabase_client(service_role=True)
    if not sb_client:
        print("❌ Failed to get Supabase client")
        return False
    
    print("✅ Supabase client connected")
    
    # Test user ID (you'll need to replace this with an actual user ID)
    test_user_id = input("Enter a test user ID (or leave blank to skip): ").strip()
    
    if not test_user_id:
        print("⏭️  Skipping user-specific tests - no user ID provided")
        return True
    
    # Test getting existing recipients
    print(f"\n📋 Testing get_user_recipients for user: {test_user_id}")
    try:
        recipients = db.get_user_recipients(sb_client, test_user_id)
        print(f"✅ Found {len(recipients)} recipients: {recipients}")
    except Exception as e:
        print(f"❌ Error getting recipients: {e}")
        return False
    
    # Test adding a recipient
    test_chat_id = "123456789"
    print(f"\n➕ Testing add_user_recipient with chat_id: {test_chat_id}")
    try:
        db.add_user_recipient(sb_client, test_user_id, test_chat_id)
        print("✅ Added recipient successfully")
    except Exception as e:
        print(f"❌ Error adding recipient: {e}")
        return False
    
    # Test getting recipients again
    print(f"\n📋 Testing get_user_recipients again after adding...")
    try:
        recipients_after = db.get_user_recipients(sb_client, test_user_id)
        print(f"✅ Found {len(recipients_after)} recipients: {recipients_after}")
        
        # Check if our test recipient is there
        chat_ids = [r['chat_id'] for r in recipients_after]
        if test_chat_id in chat_ids:
            print(f"✅ Test recipient {test_chat_id} found in results")
        else:
            print(f"❌ Test recipient {test_chat_id} NOT found in results")
    except Exception as e:
        print(f"❌ Error getting recipients after adding: {e}")
        return False
    
    # Test removing the test recipient
    print(f"\n➖ Cleaning up - removing test recipient {test_chat_id}")
    try:
        db.delete_user_recipient(sb_client, test_user_id, test_chat_id)
        print("✅ Removed test recipient successfully")
    except Exception as e:
        print(f"❌ Error removing test recipient: {e}")
    
    return True

def test_database_schema():
    """Test the database schema for telegram_recipients table"""
    print("\n🔍 Testing Database Schema...")
    
    import database as db
    
    # Initialize Firebase
    db.initialize_firebase()
    
    sb_client = db.get_supabase_client(service_role=True)
    if not sb_client:
        print("❌ Failed to get Supabase client")
        return False
    
    try:
        # Try to get all recipients to see the table structure
        result = sb_client.table('telegram_recipients').select('*').limit(5).execute()
        print(f"✅ Table exists with {len(result.data)} sample rows")
        if result.data:
            print(f"📋 Sample row structure: {list(result.data[0].keys())}")
        else:
            print("📋 Table is empty")
    except Exception as e:
        print(f"❌ Error accessing telegram_recipients table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 BSE Monitor Recipients Debug Test\n")
    
    schema_ok = test_database_schema()
    recipients_ok = test_recipients_functionality()
    
    if schema_ok and recipients_ok:
        print("\n🎯 All tests completed!")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        sys.exit(1)