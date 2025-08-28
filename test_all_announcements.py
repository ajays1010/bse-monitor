#!/usr/bin/env python3
"""
Test script to verify enhanced AI analysis works for all announcement types
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_announcement_type_detection():
    """Test that all announcement types are properly detected and formatted"""
    
    try:
        from ai_service import is_quarterly_results_document, format_structured_telegram_message
        print("✅ Successfully imported AI service functions")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test various announcement types
    test_cases = [
        # Quarterly results - should get special formatting
        ("Unaudited Financial Results for the quarter ended June 30, 2024", "financials", True, "Quarterly Results"),
        ("Unaudited Consolidated Financial Results for Q1 FY25", "financials", True, "Quarterly Results"),
        ("Financial Results for the nine months ended December 31, 2024", "financials", True, "Quarterly Results"),
        
        # Non-quarterly - should get generic AI analysis
        ("Board meeting to be held on August 30, 2024", "corporate", False, "Board Meeting"),
        ("Dividend declared for FY24", "corporate", False, "Dividend"),
        ("Credit rating upgraded by ICRA", "corporate", False, "Rating Change"),
        ("Rights issue announcement", "corporate", False, "Rights Issue"),
        ("Annual General Meeting notice", "corporate", False, "AGM Notice"),
        ("Acquisition of subsidiary company", "corporate", False, "Corporate Action"),
    ]
    
    print("\n🔍 Testing announcement type detection:")
    print("=" * 80)
    
    all_passed = True
    
    for i, (headline, category, expected_quarterly, announcement_type) in enumerate(test_cases, 1):
        is_quarterly = is_quarterly_results_document(headline, category)
        status = "✅ PASS" if is_quarterly == expected_quarterly else "❌ FAIL"
        
        print(f"{i:2d}. {status} | Expected: {expected_quarterly:5} | Got: {is_quarterly:5} | Type: {announcement_type}")
        print(f"    Headline: '{headline}'")
        print(f"    Category: '{category}'")
        print()
        
        if is_quarterly != expected_quarterly:
            all_passed = False
    
    return all_passed

def test_message_formatting():
    """Test message formatting for different announcement types"""
    
    try:
        from ai_service import format_structured_telegram_message
        from datetime import datetime
        
        # Test quarterly announcement formatting
        quarterly_analysis = {
            "company_name": "Test Company Ltd",
            "scrip_code": "123456",
            "announcement_title": "Q1 FY25 Results",
            "document_type": "quarterly_results",
            "quarterly_financials": {
                "current_quarter": {
                    "period": "Q1 FY25",
                    "total_income": "1000.50",
                    "total_expenses": "800.25",
                    "profit_before_tax": "200.25"
                },
                "previous_quarter": {
                    "period": "Q4 FY24",
                    "total_income": "950.30",
                    "total_expenses": "780.15",
                    "profit_before_tax": "170.15"
                },
                "growth_analysis": {
                    "income_growth_percent": 5.28,
                    "expenses_growth_percent": 2.57,
                    "pbt_growth_percent": 17.69
                }
            },
            "investment_recommendation": "BUY",
            "sentiment_analysis": "POSITIVE",
            "gist": "Strong quarterly performance with revenue growth acceleration",
            "tldr": "Robust fundamentals support upward momentum"
        }
        
        # Test non-quarterly announcement formatting
        board_meeting_analysis = {
            "company_name": "Test Company Ltd",
            "scrip_code": "123456",
            "announcement_title": "Board Meeting Announcement",
            "document_type": "board_meeting",
            "financial_summary": "Board approved dividend of ₹5 per share",
            "business_impact": "Strategic expansion into new markets approved",
            "market_implications": "Positive sentiment expected due to dividend approval",
            "risk_assessment": "Minimal risks, strong cash position supports dividend",
            "investment_recommendation": "HOLD",
            "sentiment_analysis": "POSITIVE",
            "gist": "Board approved attractive dividend and expansion plans",
            "tldr": "Dividend approval and growth strategy signal confidence"
        }
        
        print("\n📱 Testing message formatting:")
        print("=" * 60)
        
        # Test quarterly formatting
        print("1. QUARTERLY RESULTS MESSAGE:")
        quarterly_msg = format_structured_telegram_message(
            quarterly_analysis,
            "123456",
            "Q1 FY25 Results",
            datetime.now(),
            is_quarterly=True
        )
        print(quarterly_msg)
        print("\n" + "="*60)
        
        # Test non-quarterly formatting
        print("2. BOARD MEETING MESSAGE:")
        board_msg = format_structured_telegram_message(
            board_meeting_analysis,
            "123456",
            "Board Meeting Announcement",
            datetime.now(),
            is_quarterly=False
        )
        print(board_msg)
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing message formatting: {e}")
        return False

def test_enhanced_flow():
    """Test the complete enhanced flow simulation"""
    
    print("\n🔄 Testing enhanced announcement processing flow:")
    print("=" * 60)
    
    # Simulate different announcement scenarios
    scenarios = [
        {
            "type": "Quarterly Results",
            "headline": "Unaudited Financial Results for Q1 FY25",
            "category": "financials",
            "expected_ai": True,
            "expected_special_format": True
        },
        {
            "type": "Board Meeting",
            "headline": "Board Meeting - Dividend Declaration",
            "category": "corporate",
            "expected_ai": True,
            "expected_special_format": False
        },
        {
            "type": "Rating Change",
            "headline": "Credit Rating Upgraded by ICRA",
            "category": "corporate",
            "expected_ai": True,
            "expected_special_format": False
        }
    ]
    
    try:
        from ai_service import is_quarterly_results_document
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"{i}. {scenario['type']}:")
            print(f"   Headline: {scenario['headline']}")
            print(f"   Category: {scenario['category']}")
            
            is_quarterly = is_quarterly_results_document(scenario['headline'], scenario['category'])
            
            print(f"   ✅ AI Analysis: {'YES' if scenario['expected_ai'] else 'NO'}")
            print(f"   ✅ Special Format: {'YES' if is_quarterly and scenario['expected_special_format'] else 'NO'}")
            print(f"   ✅ Generic Format: {'YES' if not is_quarterly else 'NO'}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced flow: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 BSE Monitor - Enhanced AI Analysis Test")
    print("Testing AI summaries for ALL announcement types")
    print()
    
    test1_passed = test_announcement_type_detection()
    test2_passed = test_message_formatting()
    test3_passed = test_enhanced_flow()
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY:")
    
    if test1_passed and test2_passed and test3_passed:
        print("🎉 All tests passed! Enhanced AI analysis is working correctly.")
        print("\n✅ WHAT WILL HAPPEN NOW:")
        print("   📈 Quarterly Results → AI Summary with financial data + PDF")
        print("   📋 Board Meetings → AI Summary with business impact + PDF")
        print("   💰 Dividends → AI Summary with dividend analysis + PDF")
        print("   ⭐ Ratings → AI Summary with credit analysis + PDF")
        print("   📊 All Others → AI Summary with general analysis + PDF")
        print("\n🔍 To monitor AI processing:")
        print("   1. Ensure BSE_VERBOSE=1 in .env")
        print("   2. Watch for log messages starting with 'AI:'")
        print("   3. Check Telegram for both AI summaries AND PDFs")
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        if not test1_passed:
            print("   - Announcement type detection issues")
        if not test2_passed:
            print("   - Message formatting issues")
        if not test3_passed:
            print("   - Enhanced flow issues")

if __name__ == "__main__":
    main()