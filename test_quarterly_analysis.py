#!/usr/bin/env python3
"""
Test script for quarterly results analysis on Adani PDF in multiuser-main directory
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_quarterly_analysis():
    """Test the AI analysis on Adani quarterly results PDF"""
    
    pdf_path = r"D:\BSE monitor\Working one with basic trigger\multiuser-main\adani.pdf"
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    # Check if Gemini API key is set
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set in environment variables")
        print("Please add GEMINI_API_KEY to your .env file")
        return False
    
    try:
        # Import AI service
        from ai_service import analyze_pdf_bytes_with_gemini, is_quarterly_results_document, format_structured_telegram_message
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"📄 Analyzing PDF: {pdf_path}")
        print(f"📊 File size: {len(pdf_bytes):,} bytes")
        
        # Test quarterly results detection
        test_headline = "Unaudited Financial Results for the quarter ended June 30, 2024"
        test_category = "financials"
        
        is_quarterly = is_quarterly_results_document(test_category, test_headline)
        print(f"🔍 Quarterly results detected: {is_quarterly}")
        
        print("🤖 Running AI analysis...")
        
        # Analyze with AI (assuming Adani Enterprises)
        analysis_result = analyze_pdf_bytes_with_gemini(
            pdf_bytes, 
            "adani.pdf", 
            "512599"  # Adani Enterprises BSE code
        )
        
        if not analysis_result:
            print("❌ AI analysis failed or returned no results")
            return False
        
        print("\n✅ AI Analysis Complete!")
        print("="*50)
        
        # Display key results
        print(f"🏢 Company: {analysis_result.get('company_name', 'N/A')}")
        print(f"📋 Document Type: {analysis_result.get('document_type', 'N/A')}")
        print(f"📄 Title: {analysis_result.get('announcement_title', 'N/A')}")
        
        # Check if quarterly data was extracted
        quarterly_data = analysis_result.get('quarterly_financials')
        if quarterly_data:
            print("\n📈 QUARTERLY RESULTS EXTRACTED:")
            print("-" * 30)
            
            current_q = quarterly_data.get('current_quarter', {})
            previous_q = quarterly_data.get('previous_quarter', {})
            growth = quarterly_data.get('growth_analysis', {})
            
            if current_q:
                print(f"📅 Current Quarter: {current_q.get('period', 'N/A')}")
                print(f"  💰 Total Income: ₹{current_q.get('total_income', 'N/A')} Cr")
                print(f"  💸 Total Expenses: ₹{current_q.get('total_expenses', 'N/A')} Cr")
                print(f"  📈 Profit Before Tax: ₹{current_q.get('profit_before_tax', 'N/A')} Cr")
            
            if previous_q:
                print(f"\n📅 Previous Quarter: {previous_q.get('period', 'N/A')}")
                print(f"  💰 Total Income: ₹{previous_q.get('total_income', 'N/A')} Cr")
                print(f"  💸 Total Expenses: ₹{previous_q.get('total_expenses', 'N/A')} Cr")
                print(f"  📈 Profit Before Tax: ₹{previous_q.get('profit_before_tax', 'N/A')} Cr")
            
            if growth:
                print(f"\n📊 Growth Analysis:")
                print(f"  📈 Income Growth (QoQ): {growth.get('income_growth_percent', 'N/A')}%")
                print(f"  📈 Expenses Growth (QoQ): {growth.get('expenses_growth_percent', 'N/A')}%")
                print(f"  📈 PBT Growth (QoQ): {growth.get('pbt_growth_percent', 'N/A')}%")
                
                yoy_income = growth.get('income_growth_yoy_percent')
                yoy_expenses = growth.get('expenses_growth_yoy_percent')
                yoy_pbt = growth.get('pbt_growth_yoy_percent')
                if yoy_income and yoy_income != 'N/A':
                    print(f"  📅 Income Growth (YoY): {yoy_income}%")
                if yoy_expenses and yoy_expenses != 'N/A':
                    print(f"  📅 Expenses Growth (YoY): {yoy_expenses}%")
                if yoy_pbt and yoy_pbt != 'N/A':
                    print(f"  📅 PBT Growth (YoY): {yoy_pbt}%")
        else:
            print("❌ No quarterly financial data extracted")
            print("This might not be a quarterly results document or the format wasn't recognized")
        
        # Show AI recommendation
        recommendation = analysis_result.get('investment_recommendation')
        if recommendation:
            print(f"\n🤖 AI Recommendation: {recommendation}")
        
        sentiment = analysis_result.get('sentiment_analysis')
        if sentiment:
            print(f"📊 Sentiment: {sentiment}")
        
        gist = analysis_result.get('gist')
        if gist:
            print(f"📝 Summary: {gist}")
        
        # Test the Telegram formatting
        print("\n" + "="*50)
        print("📱 TELEGRAM MESSAGE FORMAT:")
        print("="*50)
        
        from datetime import datetime
        
        telegram_msg = format_structured_telegram_message(
            analysis_result,
            "512599",  # Adani Enterprises BSE code
            "Unaudited Financial Results",
            datetime.now()
        )
        
        print(telegram_msg)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install google-generativeai PyPDF2")
        return False
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return False

if __name__ == "__main__":
    print("🚀 BSE Monitor - Quarterly Results Analysis Test (MultiUser)")
    print("Testing with Adani PDF...")
    print()
    
    success = test_quarterly_analysis()
    
    if success:
        print("\n🎯 Test completed successfully!")
    else:
        print("\n⚠️ Test failed. Please check the issues above.")
        sys.exit(1)