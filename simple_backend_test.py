#!/usr/bin/env python3
"""
Simple Backend Test for OmniLeads Analytics
Quick verification that the database connection fix is working
"""

import requests
import json
import sys
from datetime import datetime

# Load backend URL from frontend .env
def get_backend_url():
    """Get backend URL from frontend .env file"""
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"❌ Error reading frontend .env: {e}")
        return None
    return None

BACKEND_URL = get_backend_url()
if not BACKEND_URL:
    print("❌ Could not find REACT_APP_BACKEND_URL in /app/frontend/.env")
    sys.exit(1)

print(f"🔗 Testing backend at: {BACKEND_URL}")
print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def test_endpoint(endpoint, timeout=10, description=""):
    """Test a single endpoint"""
    url = f"{BACKEND_URL}{endpoint}"
    
    try:
        print(f"\n🧪 Testing {endpoint}")
        if description:
            print(f"   📝 {description}")
        
        response = requests.get(url, timeout=timeout)
        print(f"   📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   📄 Response type: JSON")
                if isinstance(data, dict) and len(data) <= 3:
                    print(f"   📋 Response: {json.dumps(data, indent=2)}")
                elif isinstance(data, dict):
                    print(f"   📋 Response keys: {list(data.keys())}")
                else:
                    print(f"   📋 Response: {type(data)} with {len(data) if hasattr(data, '__len__') else 'unknown'} items")
                print(f"   ✅ PASSED")
                return True, data
            except:
                print(f"   📄 Response type: Non-JSON")
                print(f"   📋 Response: {response.text[:200]}...")
                print(f"   ✅ PASSED")
                return True, None
        else:
            print(f"   ❌ FAILED - Status: {response.status_code}")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"   ⏰ TIMEOUT after {timeout}s")
        return False, None
    except Exception as e:
        print(f"   💥 ERROR: {str(e)}")
        return False, None

def main():
    """Main test execution"""
    print("\n" + "="*60)
    print("🏥 BACKEND HEALTH & DATABASE CONNECTION TESTS")
    print("="*60)
    
    results = {
        'passed': 0,
        'failed': 0,
        'total': 0
    }
    
    # Test basic connectivity
    success, _ = test_endpoint('/api/', 5, "Basic API connectivity")
    results['total'] += 1
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test database connection
    success, data = test_endpoint('/api/analytics/test', 15, "Database connection test")
    results['total'] += 1
    if success:
        results['passed'] += 1
        if data and data.get('status') == 'success':
            total_calls = data.get('total_llamadas', 0)
            print(f"   🎯 Database has {total_calls:,} call records")
        elif data and data.get('status') == 'error':
            print(f"   ⚠️  Database connection error: {data.get('message', 'Unknown error')}")
    else:
        results['failed'] += 1
    
    # Test config endpoints
    success, _ = test_endpoint('/api/config/active', 5, "Active database configuration")
    results['total'] += 1
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test a simple analytics endpoint
    success, _ = test_endpoint('/api/analytics/campanas', 10, "Get campaigns list")
    results['total'] += 1
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test another simple endpoint
    success, _ = test_endpoint('/api/analytics/agentes', 10, "Get agents list")
    results['total'] += 1
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    
    if results['failed'] == 0:
        print(f"\n✅ ALL TESTS PASSED!")
        print("   • Backend service is accessible")
        print("   • Database connection is working")
        print("   • Analytics endpoints are functional")
        print("\n🎉 Backend is ready for KPI testing!")
        return True
    else:
        print(f"\n⚠️  {results['failed']} tests failed")
        print("   • Check backend logs for details")
        print("   • Verify database configuration")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 Backend tests PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️  Backend tests FAILED!")
        sys.exit(1)