#!/usr/bin/env python3
"""
Test script for Gemini API configuration
"""

import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gemini_api():
    """Test Gemini API configuration and connectivity"""
    print("🔍 Testing Gemini API Configuration...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check API key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ No Gemini API key found in environment variables")
        print("   Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file")
        return False
    
    print(f"✅ API key found: {api_key[:10]}***")
    
    # Test import
    try:
        import google.generativeai as genai
        print("✅ google-generativeai library imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import google-generativeai: {e}")
        print("   Install with: pip install google-generativeai")
        return False
    
    # Test API configuration
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured successfully")
    except Exception as e:
        print(f"❌ Failed to configure Gemini API: {e}")
        return False
    
    # Test model initialization
    try:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        print(f"✅ Model '{model_name}' initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize model: {e}")
        return False
    
    # Test simple text generation
    try:
        print("🧪 Testing simple text generation...")
        response = model.generate_content("Say hello in a professional manner")
        if response and response.text:
            print(f"✅ Text generation successful: {response.text[:100]}...")
        else:
            print("❌ No response from model")
            return False
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False
    
    print("\n🎉 Gemini API is working correctly!")
    return True

def test_ai_service():
    """Test the AI service module"""
    print("\n🔍 Testing AI Service Module...")
    
    try:
        from ai_service import analyze_pdf_bytes_with_gemini, format_analysis_for_display
        print("✅ AI service module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AI service: {e}")
        return False
    
    # Test with dummy PDF data (just to check function signature)
    try:
        dummy_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        result = analyze_pdf_bytes_with_gemini(dummy_pdf_bytes, "test.pdf", "500001")
        print("✅ AI service function call completed (may return None without valid PDF)")
    except Exception as e:
        print(f"❌ AI service function call failed: {e}")
        return False
    
    print("✅ AI service module is working correctly!")
    return True

if __name__ == "__main__":
    print("🚀 BSE Monitor AI Service Test\n")
    
    gemini_ok = test_gemini_api()
    ai_service_ok = test_ai_service()
    
    if gemini_ok and ai_service_ok:
        print("\n🎯 All tests passed! AI PDF analysis should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        sys.exit(1)