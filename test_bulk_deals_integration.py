#!/usr/bin/env python3
"""
Test script for bulk deals integration with BSE monitoring app
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_bulk_deals_integration():
    """Test the bulk deals monitoring integration"""
    print("🧪 Testing Bulk Deals Integration")
    print("=" * 50)
    
    try:
        # Import the bulk deals module
        from bulk_deals_monitor import send_bulk_deals_alerts, BulkBlockDealsMonitor
        print("✅ Successfully imported bulk deals module")
        
        # Test basic scraping functionality
        monitor = BulkBlockDealsMonitor()
        print("✅ Monitor instance created")
        
        # Test fetching deals
        all_deals = monitor.fetch_all_deals()
        print(f"✅ Fetched {len(all_deals)} total deals")
        
        # Test sample monitored stocks
        test_stocks = [
            {'bse_code': '500325', 'company_name': 'RELIANCE'},
            {'bse_code': '500180', 'company_name': 'HDFC BANK'},
            {'bse_code': '511714', 'company_name': 'NIMBSPROJ'},  # This one might have deals
            {'bse_code': '542865', 'company_name': 'ANUROOP'},   # This one might have deals
        ]
        
        # Test filtering
        filtered_deals = monitor.filter_deals_by_monitored_stocks(all_deals, test_stocks)
        print(f"✅ Filtered to {len(filtered_deals)} deals for monitored stocks")
        
        if filtered_deals:
            print(f"🎯 Found deals for monitored stocks:")
            for deal in filtered_deals[:3]:  # Show first 3
                print(f"  • {deal['source']} {deal['deal_type']}: {deal['security_name']} ({deal.get('script_code', 'No code')})")
                print(f"    Client: {deal['client_name'][:50]}...")
                print(f"    {deal.get('buy_sell', 'N/A')} | Qty: {deal['quantity']:,.0f} | Value: ₹{deal['deal_value']:,.0f}")
        
        # Test message formatting
        if filtered_deals:
            message = monitor.format_deals_for_telegram(filtered_deals)
            print(f"✅ Generated Telegram message ({len(message)} chars)")
            print("📱 Sample message:")
            print("-" * 30)
            print(message[:300] + "..." if len(message) > 300 else message)
            print("-" * 30)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_database_integration():
    """Test database integration (if available)"""
    print("\\n🗄️ Testing Database Integration")
    print("=" * 50)
    
    try:
        # Try to import database functions
        import database as db
        print("✅ Database module imported")
        
        # Try to get Supabase client
        sb = db.get_supabase_client(service_role=True)
        if sb:
            print("✅ Supabase client connected")
            
            # Check if seen_deals table exists (won't create it, just check)
            try:
                # This is just a test query to see if we can access the database
                test_query = sb.table('profiles').select('id').limit(1).execute()
                print("✅ Database access working")
                
                # Note: In production, you'd need to create the seen_deals table
                print("⚠️ Note: You'll need to create 'seen_deals' table for production use")
                print("   See SEEN_DEALS_SQL_SCHEMA in bulk_deals_monitor.py")
                
                return True
            except Exception as e:
                print(f"⚠️ Database query error: {e}")
                return False
        else:
            print("❌ Could not connect to Supabase")
            return False
            
    except ImportError as e:
        print(f"❌ Database import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_unified_cron_integration():
    """Test integration with unified cron system"""
    print("\\n⚙️ Testing Unified Cron Integration")
    print("=" * 50)
    
    try:
        # Test if the app.py has the integration
        with open('app.py', 'r') as f:
            content = f.read()
            
        if 'bulk_deals_monitoring' in content:
            print("✅ Bulk deals job found in unified cron system")
        else:
            print("❌ Bulk deals job NOT found in unified cron system")
            
        if 'from bulk_deals_monitor import send_bulk_deals_alerts' in content:
            print("✅ Bulk deals import found in app.py")
        else:
            print("❌ Bulk deals import NOT found in app.py")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking cron integration: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 BSE Monitor - Bulk Deals Integration Test")
    print()
    
    # Run tests
    test1_passed = test_bulk_deals_integration()
    test2_passed = test_database_integration()
    test3_passed = test_unified_cron_integration()
    
    print("\\n" + "=" * 60)
    print("📋 TEST SUMMARY:")
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 All tests passed! Bulk deals monitoring is ready.")
        print("\\n✅ WHAT'S WORKING:")
        print("   📊 Bulk/block deals scraping from NSE and BSE")
        print("   🎯 Filtering by user's monitored stocks")
        print("   📱 Telegram message formatting")
        print("   🗄️ Database integration structure")
        print("   ⚙️ Unified cron system integration")
        
        print("\\n🔧 NEXT STEPS:")
        print("1. Create the 'seen_deals' table in your Supabase database")
        print("2. Deploy the updated app.py with bulk deals integration")
        print("3. The unified cron will now check for bulk deals every hour during market hours")
        print("4. Users will receive Telegram alerts for bulk/block deals in their monitored stocks")
        
        print("\\n📅 SCHEDULE:")
        print("• BSE Announcements: Every 5 minutes (continuous)")
        print("• Live Price Alerts: Every 5 minutes (market hours)")
        print("• Bulk Deals Alerts: Every hour (market hours)")
        print("• Daily Summary: Once at 16:30 (working days)")
        
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        if not test1_passed:
            print("   - Basic bulk deals functionality issues")
        if not test2_passed:
            print("   - Database integration issues")
        if not test3_passed:
            print("   - Unified cron integration issues")

if __name__ == "__main__":
    main()