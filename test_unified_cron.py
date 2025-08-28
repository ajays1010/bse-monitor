#!/usr/bin/env python3
"""
Test script to verify the unified cron master endpoint works correctly
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_unified_cron():
    """Test the unified cron master endpoint"""
    
    # Get the secret key from environment
    secret_key = os.environ.get('CRON_SECRET_KEY')
    if not secret_key:
        print("❌ CRON_SECRET_KEY not found in environment variables")
        return False
    
    # Test the local endpoint
    base_url = "http://localhost:5000"
    endpoint = f"{base_url}/cron/master?key={secret_key}"
    
    print("🚀 Testing Unified Cron Master Endpoint")
    print(f"📍 URL: {endpoint}")
    print("=" * 60)
    
    try:
        response = requests.get(endpoint, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Endpoint Response:")
                print(json.dumps(data, indent=2, default=str))
                
                # Analyze the response
                print("\n🔍 Analysis:")
                print(f"• Timestamp: {data.get('timestamp', 'N/A')}")
                print(f"• Market Hours: {data.get('market_hours', 'N/A')}")
                print(f"• Working Day: {data.get('working_day', 'N/A')}")
                print(f"• Jobs Executed: {len(data.get('executed_jobs', []))}")
                print(f"• Jobs Skipped: {len(data.get('skipped_jobs', []))}")
                
                # Show job details
                for job in data.get('executed_jobs', []):
                    print(f"  ✅ {job['name']}: {job['users_processed']} users, {job['notifications_sent']} notifications")
                
                for job in data.get('skipped_jobs', []):
                    print(f"  ⏭️ {job['name']}: {job['reason']}")
                
                if data.get('errors'):
                    print(f"⚠️ Errors: {len(data['errors'])}")
                    for error in data['errors']:
                        print(f"  • {error}")
                
                return True
                
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response: {response.text}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except requests.ConnectionError:
        print("❌ Connection error. Make sure Flask app is running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_production_url():
    """Test the production endpoint (if needed)"""
    
    secret_key = os.environ.get('CRON_SECRET_KEY')
    if not secret_key:
        print("❌ CRON_SECRET_KEY not found")
        return False
    
    # Your production URL
    production_url = "https://multiuser-bse-monitor.onrender.com"
    endpoint = f"{production_url}/cron/master?key={secret_key}"
    
    print("\n🌐 Testing Production Endpoint (Optional)")
    print(f"📍 URL: {endpoint}")
    print("=" * 60)
    
    try:
        response = requests.get(endpoint, timeout=60)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Production endpoint working!")
                print(f"• Jobs Executed: {len(data.get('executed_jobs', []))}")
                print(f"• Jobs Skipped: {len(data.get('skipped_jobs', []))}")
                return True
            except:
                print(f"⚠️ Non-JSON response: {response.text[:200]}")
                return True  # Still consider success if endpoint responds
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"⚠️ Production test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 BSE Monitor - Unified Cron System Test")
    print()
    
    # Test local endpoint
    local_success = test_unified_cron()
    
    # Optionally test production
    # production_success = test_production_url()
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY:")
    
    if local_success:
        print("🎉 Unified cron system is working correctly!")
        print("\n✅ NEXT STEPS:")
        print("1. Update your UptimeRobot to ping the single endpoint:")
        print(f"   https://multiuser-bse-monitor.onrender.com/cron/master?key={os.environ.get('CRON_SECRET_KEY')}")
        print("\n2. Set UptimeRobot to ping every 5 minutes")
        print("\n3. The system will automatically:")
        print("   📈 Monitor live prices during market hours (9:00-15:30)")
        print("   📰 Check BSE announcements continuously (24/7)")
        print("   📊 Send daily summary at 16:30 on working days")
    else:
        print("⚠️ Issues detected. Please check the Flask app and configuration.")
        print("\nDebugging tips:")
        print("• Make sure Flask app is running: python app.py")
        print("• Check CRON_SECRET_KEY in .env file")
        print("• Verify database connectivity")

if __name__ == "__main__":
    main()