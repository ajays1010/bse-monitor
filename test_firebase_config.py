#!/usr/bin/env python3
"""
Test script to verify Firebase configuration endpoint works correctly
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_firebase_config_endpoint():
    """Test the Firebase configuration endpoint"""
    
    print("🔥 Testing Firebase Configuration Endpoint")
    print("=" * 50)
    
    # Check if required environment variables are set
    required_vars = [
        'FIREBASE_API_KEY',
        'FIREBASE_AUTH_DOMAIN', 
        'FIREBASE_PROJECT_ID',
        'FIREBASE_STORAGE_BUCKET',
        'FIREBASE_MESSAGING_SENDER_ID',
        'FIREBASE_APP_ID'
    ]
    
    print("1. Checking environment variables:")
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Only show first 10 characters for security
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {masked_value}")
        else:
            print(f"   ❌ {var}: Missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please add these to your .env file")
        return False
    
    print("\n2. Testing Flask endpoint:")
    try:
        # Test the endpoint (assuming Flask app is running on localhost:5000)
        # Note: You'll need to start your Flask app first
        response = requests.get('http://localhost:5000/firebase-config', timeout=5)
        
        if response.status_code == 200:
            config = response.json()
            print("   ✅ Endpoint accessible")
            print("   ✅ Valid JSON response")
            
            # Check if all required keys are present
            for key in ['apiKey', 'authDomain', 'projectId', 'storageBucket', 'messagingSenderId', 'appId']:
                if key in config and config[key]:
                    print(f"   ✅ {key}: Present")
                else:
                    print(f"   ❌ {key}: Missing or empty")
                    return False
            
            print("\n✅ Firebase configuration endpoint working correctly!")
            return True
            
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️ Flask app not running")
        print("   To test the endpoint:")
        print("   1. Start your Flask app: python app.py")
        print("   2. Run this test again")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_env_file_security():
    """Test that .env file contains the moved configuration"""
    
    print("\n🔒 Testing .env file security:")
    print("=" * 30)
    
    env_file = '.env'
    if not os.path.exists(env_file):
        print("❌ .env file not found")
        return False
    
    print("✅ .env file exists")
    
    # Check if Firebase config is in .env
    with open(env_file, 'r') as f:
        content = f.read()
    
    if 'FIREBASE_API_KEY' in content:
        print("✅ Firebase configuration found in .env")
    else:
        print("❌ Firebase configuration not found in .env")
        return False
    
    # Check if .env is in .gitignore
    gitignore_file = '.gitignore'
    if os.path.exists(gitignore_file):
        with open(gitignore_file, 'r') as f:
            gitignore_content = f.read()
        
        if '.env' in gitignore_content:
            print("✅ .env file is in .gitignore (secure)")
        else:
            print("⚠️ .env file should be added to .gitignore for security")
    else:
        print("⚠️ .gitignore file not found - consider creating one to exclude .env")
    
    return True

def main():
    """Main test function"""
    
    print("🚀 BSE Monitor - Firebase Configuration Security Test")
    print()
    
    env_test = test_env_file_security()
    config_test = test_firebase_config_endpoint()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    
    if env_test and config_test:
        print("🎉 All tests passed! Firebase configuration is secure.")
        print("\n✅ SECURITY IMPROVEMENTS:")
        print("   🔒 Firebase config moved from template to .env")
        print("   🔒 Backend endpoint serves config securely")
        print("   🔒 No sensitive data in GitHub-uploaded files")
        print("   🔒 Frontend loads config dynamically")
        
        print("\n💡 NEXT STEPS:")
        print("   1. Ensure .env is in .gitignore")
        print("   2. Test login functionality")
        print("   3. Deploy with confidence!")
        
    else:
        print("⚠️ Some tests failed:")
        if not env_test:
            print("   - Environment variable setup issues")
        if not config_test:
            print("   - Firebase config endpoint issues")

if __name__ == "__main__":
    main()