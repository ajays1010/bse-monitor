#!/usr/bin/env python3
"""
Simple test to verify quarterly detection is working correctly
"""

import os
import sys

# Add the current directory to the path so we can import ai_service
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_quarterly_detection():
    """Test the quarterly detection function with various examples"""
    
    try:
        from ai_service import is_quarterly_results_document
        print("✅ Successfully imported is_quarterly_results_document")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test cases: (headline, category, expected_result)
    test_cases = [
        ("Unaudited Financial Results for the quarter ended June 30, 2024", "financials", True),
        ("Unaudited Consolidated Financial Results for Q1 FY25", "financials", True),
        ("Quarterly Results for Q4 FY24", "financials", True),
        ("Financial Results for the quarter ended March 31, 2024", "financials", True),
        ("Unaudited Financial Results for the nine months ended December 31, 2024", "financials", True),
        ("Board meeting announcement", "corporate", False),
        ("Dividend declaration", "corporate", False),
        ("Rights issue announcement", "corporate", False),
        ("AGM notice", "corporate", False),
        ("Unaudited Results without category", None, True),  # Should detect from headline
    ]
    
    print("\n🔍 Testing quarterly detection logic:")
    print("=" * 80)
    
    all_passed = True
    
    for i, (headline, category, expected) in enumerate(test_cases, 1):
        result = is_quarterly_results_document(headline, category)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"{i:2d}. {status} | Expected: {expected:5} | Got: {result:5}")
        print(f"    Headline: '{headline}'")
        print(f"    Category: '{category}'")
        print()
        
        if result != expected:
            all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("🎯 All tests PASSED! Quarterly detection is working correctly.")
    else:
        print("⚠️ Some tests FAILED! Check the logic in is_quarterly_results_document.")
    
    return all_passed

def test_database_fix():
    """Test that the database fix is working by simulating the call"""
    
    print("\n🔧 Testing database integration fix:")
    print("=" * 50)
    
    try:
        from ai_service import is_quarterly_results_document
        
        # Simulate the database call with the OLD (broken) parameter order
        print("❌ OLD (broken) call:")
        category = "financials"
        headline = "Unaudited Financial Results for Q1 FY25"
        
        # This would be wrong - category first, headline second
        old_result = is_quarterly_results_document(category, headline)
        print(f"   is_quarterly_results_document('{category}', '{headline}') = {old_result}")
        print("   This should be FALSE because category doesn't match quarterly indicators")
        
        # NEW (fixed) call - headline first, category second
        print("\n✅ NEW (fixed) call:")
        new_result = is_quarterly_results_document(headline, category)
        print(f"   is_quarterly_results_document('{headline}', '{category}') = {new_result}")
        print("   This should be TRUE because headline contains quarterly indicators")
        
        if new_result and not old_result:
            print("\n🎯 Fix is working! The parameter order correction resolved the issue.")
            return True
        else:
            print("\n⚠️ Unexpected results. Double-check the function logic.")
            return False
            
    except Exception as e:
        print(f"❌ Error testing database fix: {e}")
        return False

def main():
    print("🚀 BSE Monitor - Quarterly Detection Test")
    print("Testing the fix for AI summary not being sent to Telegram")
    print()
    
    test1_passed = test_quarterly_detection()
    test2_passed = test_database_fix()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    
    if test1_passed and test2_passed:
        print("🎉 All tests passed! The fix should resolve your issue.")
        print("\n💡 To enable verbose logging and see AI processing in action:")
        print("   1. Add BSE_VERBOSE=1 to your .env file")
        print("   2. Restart your application")
        print("   3. Check the logs when BSE announcements are processed")
        print("\n🔍 Look for log messages starting with 'AI:' to track the process")
    else:
        print("⚠️ Some tests failed. The issue may not be fully resolved.")
        print("Please check the function logic and parameter usage.")

if __name__ == "__main__":
    main()