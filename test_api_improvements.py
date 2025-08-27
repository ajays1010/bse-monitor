#!/usr/bin/env python3
"""
Test script to validate improved Yahoo Finance and BSE API error handling
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Set verbose mode for testing
os.environ['YAHOO_VERBOSE'] = '1'
os.environ['BSE_VERBOSE'] = '1'

import database as db

def test_yahoo_finance_improvements():
    """Test improved Yahoo Finance error handling"""
    print("🧪 Testing Yahoo Finance API Improvements...")
    
    # Test with known problematic symbol
    problematic_symbol = "539195.BO"  # From the error logs
    
    print(f"\n📊 Testing Yahoo chart series for problematic symbol: {problematic_symbol}")
    try:
        result = db.yahoo_chart_series_cached(problematic_symbol, '1d', '1m')
        if result is None:
            print(f"✅ Properly handled - returned None for {problematic_symbol}")
        else:
            print(f"✅ Successfully retrieved data for {problematic_symbol}: {len(result)} points")
    except Exception as e:
        print(f"❌ Exception not caught properly: {e}")
    
    print(f"\n📊 Testing latest CMP for problematic symbol: {problematic_symbol}")
    try:
        price, source = db._latest_cmp(problematic_symbol)
        if price is None:
            print(f"✅ Properly handled - returned None for {problematic_symbol}")
        else:
            print(f"✅ Successfully retrieved price for {problematic_symbol}: ₹{price} (source: {source})")
    except Exception as e:
        print(f"❌ Exception not caught properly: {e}")
    
    # Test with a valid symbol for comparison
    valid_symbol = "RELIANCE.BO"
    print(f"\n📊 Testing with valid symbol for comparison: {valid_symbol}")
    try:
        result = db.yahoo_chart_series_cached(valid_symbol, '1d', '1m')
        if result is None:
            print(f"⚠️  No data returned for {valid_symbol} (might be market hours)")
        else:
            print(f"✅ Successfully retrieved data for {valid_symbol}: {len(result)} points")
    except Exception as e:
        print(f"❌ Exception not caught properly: {e}")

def test_bse_api_improvements():
    """Test improved BSE API error handling"""
    print("\n🧪 Testing BSE API Improvements...")
    
    # Initialize database
    db.initialize_firebase()
    
    # Test with known problematic scrip code
    problematic_scrip = "500043"  # From the error logs
    
    print(f"\n📰 Testing BSE announcements for problematic scrip: {problematic_scrip}")
    try:
        from datetime import timedelta
        since_dt = db.ist_now() - timedelta(days=7)
        result = db.fetch_bse_announcements_for_scrip(problematic_scrip, since_dt)
        if not result:
            print(f"✅ Properly handled - returned empty list for {problematic_scrip}")
        else:
            print(f"✅ Successfully retrieved {len(result)} announcements for {problematic_scrip}")
    except Exception as e:
        print(f"❌ Exception not caught properly: {e}")
    
    # Test with another scrip code
    test_scrip = "500010"  # HDFC Bank
    print(f"\n📰 Testing BSE announcements for test scrip: {test_scrip}")
    try:
        since_dt = db.ist_now() - timedelta(days=7)
        result = db.fetch_bse_announcements_for_scrip(test_scrip, since_dt)
        if not result:
            print(f"ℹ️  No recent announcements for {test_scrip}")
        else:
            print(f"✅ Successfully retrieved {len(result)} announcements for {test_scrip}")
            for ann in result[:3]:  # Show first 3
                print(f"  - {ann['headline']}")
    except Exception as e:
        print(f"❌ Exception not caught properly: {e}")

def test_error_scenarios():
    """Test various error scenarios"""
    print("\n🧪 Testing Error Scenarios...")
    
    # Test invalid symbols
    invalid_symbols = ["INVALID.BO", "NONEXISTENT.NS", "999999.BO"]
    
    for symbol in invalid_symbols:
        print(f"\n📊 Testing invalid symbol: {symbol}")
        try:
            result = db.yahoo_chart_series_cached(symbol, '1d', '1m')
            if result is None:
                print(f"✅ Properly handled invalid symbol {symbol}")
            else:
                print(f"⚠️  Unexpected data for invalid symbol {symbol}")
        except Exception as e:
            print(f"❌ Exception not caught: {e}")

def main():
    print("🚀 Financial API Error Handling Test\n")
    
    print("🔧 Environment Configuration:")
    print(f"  YAHOO_VERBOSE: {os.environ.get('YAHOO_VERBOSE', 'Not set')}")
    print(f"  BSE_VERBOSE: {os.environ.get('BSE_VERBOSE', 'Not set')}")
    
    test_yahoo_finance_improvements()
    test_bse_api_improvements()
    test_error_scenarios()
    
    print("\n🎯 Test completed! Check the output for improved error handling.")

if __name__ == "__main__":
    main()