#!/usr/bin/env python3
"""
Debug script to test AI analysis and Telegram sending for BSE announcements
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_telegram_connection():
    """Test if Telegram bot token is working"""
    print("🔍 Testing Telegram connection...")
    
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment variables")
        return False
    
    telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}"
    
    try:
        # Test getMe endpoint
        response = requests.get(f"{telegram_api_url}/getMe", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                bot_info = result.get('result', {})
                print(f"✅ Telegram bot connected: {bot_info.get('first_name', 'Unknown')} (@{bot_info.get('username', 'Unknown')})")
                return True
            else:
                print(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        return False

def test_ai_analysis():
    """Test AI analysis functionality"""
    print("\n🧠 Testing AI analysis...")
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in environment variables")
        return False, None
    
    try:
        from ai_service import is_quarterly_results_document, analyze_pdf_bytes_with_gemini, format_structured_telegram_message
        print("✅ AI service imported successfully")
        
        # Test quarterly results detection
        test_cases = [
            ("Unaudited Financial Results for the quarter ended June 30, 2024", "financials"),
            ("Unaudited Consolidated Financial Results for Q1 FY25", "financials"),
            ("Board meeting announcement", "corporate"),
            ("Dividend declaration", "corporate"),
        ]
        
        print("\n🔍 Testing quarterly results detection:")
        for headline, category in test_cases:
            is_quarterly = is_quarterly_results_document(category, headline)
            print(f"  {'✅' if is_quarterly else '❌'} '{headline}' -> {is_quarterly}")
        
        # Test with a sample PDF if available
        pdf_path = r"D:\BSE monitor\Working one with basic trigger\multiuser-main\adani.pdf"
        if os.path.exists(pdf_path):
            print(f"\n📄 Testing AI analysis with {pdf_path}...")
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            try:
                analysis_result = analyze_pdf_bytes_with_gemini(
                    pdf_bytes, 
                    "adani.pdf", 
                    "512599"  # Adani Enterprises BSE code
                )
                
                if analysis_result:
                    print("✅ AI analysis successful")
                    
                    # Generate telegram message
                    from datetime import datetime
                    telegram_msg = format_structured_telegram_message(
                        analysis_result,
                        "512599",
                        "Unaudited Financial Results",
                        datetime.now()
                    )
                    
                    print("✅ Telegram message formatted successfully")
                    return True, telegram_msg
                else:
                    print("❌ AI analysis returned no results")
                    return False, None
            except Exception as e:
                print(f"❌ AI analysis failed: {e}")
                return False, None
        else:
            print("⚠️ No test PDF found, skipping AI analysis test")
            return True, "🏢 Test Company (TEST123)\n📄 Test Announcement\n📅 27/08/24 02:30 PM\n💹 ₹100.00 🔼 +2.35%\n\n🤖 AI Analysis: Test message"
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False, None

def test_telegram_sending(test_message):
    """Test sending a message to Telegram"""
    print("\n📱 Testing Telegram message sending...")
    
    telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return False
    
    telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}"
    
    # Get a test chat ID (you need to configure this)
    test_chat_id = os.environ.get("TEST_CHAT_ID", "")
    if not test_chat_id:
        print("⚠️ TEST_CHAT_ID not set in environment variables")
        print("To test sending, add TEST_CHAT_ID=your_chat_id to .env file")
        print("You can get your chat ID by messaging @userinfobot on Telegram")
        return True  # Don't fail the test if chat ID not provided
    
    try:
        response = requests.post(
            f"{telegram_api_url}/sendMessage",
            json={
                'chat_id': test_chat_id,
                'text': f"🧪 BSE Monitor AI Test\n\n{test_message}",
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Test message sent to Telegram successfully")
                return True
            else:
                print(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

def test_database_recipients():
    """Test getting Telegram recipients from database"""
    print("\n💾 Testing database recipients...")
    
    try:
        from database import get_supabase_client
        
        sb = get_supabase_client()
        recipients = sb.table('telegram_recipients').select('user_id, chat_id').limit(5).execute()
        
        if recipients.data:
            print(f"✅ Found {len(recipients.data)} telegram recipients in database:")
            for rec in recipients.data:
                print(f"  - User: {rec.get('user_id', 'N/A')[:8]}... Chat: {rec.get('chat_id', 'N/A')}")
            return True
        else:
            print("⚠️ No telegram recipients found in database")
            return False
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return False

def debug_bse_announcement_flow():
    """Debug the complete BSE announcement flow"""
    print("\n🔄 Testing complete BSE announcement flow...")
    
    try:
        # Import required functions
        from database import send_bse_announcements_consolidated, get_supabase_client
        from ai_service import is_quarterly_results_document
        
        # Create a mock announcement item
        mock_item = {
            'news_id': 'TEST123',
            'scrip_code': '512599',  # Adani Enterprises
            'headline': 'Unaudited Financial Results for the quarter ended June 30, 2024',
            'pdf_name': 'test_document.pdf',
            'ann_dt': 'test_date',
            'category': 'financials'
        }
        
        # Test quarterly detection
        is_quarterly = is_quarterly_results_document(
            mock_item.get('category', ''), 
            mock_item.get('headline', '')
        )
        print(f"🔍 Mock announcement quarterly detection: {is_quarterly}")
        
        if is_quarterly:
            print("✅ Mock announcement would trigger AI analysis")
        else:
            print("❌ Mock announcement would NOT trigger AI analysis")
            print("   This might be why your real announcements aren't being processed")
        
        return True
    except Exception as e:
        print(f"❌ Error in flow test: {e}")
        return False

def main():
    """Main debug function"""
    print("🚀 BSE Monitor - AI & Telegram Debug Script")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test 1: Telegram connection
    telegram_ok = test_telegram_connection()
    all_tests_passed = all_tests_passed and telegram_ok
    
    # Test 2: AI analysis
    ai_ok, test_message = test_ai_analysis()
    all_tests_passed = all_tests_passed and ai_ok
    
    # Test 3: Database recipients
    db_ok = test_database_recipients()
    all_tests_passed = all_tests_passed and db_ok
    
    # Test 4: Telegram sending (if we have a test message)
    if test_message:
        telegram_send_ok = test_telegram_sending(test_message)
        all_tests_passed = all_tests_passed and telegram_send_ok
    
    # Test 5: BSE announcement flow
    flow_ok = debug_bse_announcement_flow()
    all_tests_passed = all_tests_passed and flow_ok
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎯 All tests passed! The issue might be:")
        print("   1. No quarterly results documents being detected")
        print("   2. AI analysis failing silently in production")
        print("   3. Check BSE_VERBOSE=1 in your .env for more logging")
    else:
        print("⚠️ Some tests failed. Please fix the issues above.")
    
    print("\n💡 Debugging tips:")
    print("   - Set BSE_VERBOSE=1 in .env for detailed logging")
    print("   - Check your .env file has GEMINI_API_KEY and TELEGRAM_BOT_TOKEN")
    print("   - Verify your announcements match quarterly detection criteria")

if __name__ == "__main__":
    main()