#!/usr/bin/env python3
"""
Quick KPI Consistency Test for OmniLeads Analytics
Tests the critical KPI consistency issue that was just fixed
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

print(f"🔗 Testing KPI consistency at: {BACKEND_URL}")
print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def test_endpoint_with_timeout(endpoint, timeout=30):
    """Test endpoint with timeout"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        print(f"\n🧪 Testing {endpoint} (timeout: {timeout}s)")
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ SUCCESS - Status: {response.status_code}")
                return True, data
            except:
                print(f"   ⚠️  SUCCESS but non-JSON response - Status: {response.status_code}")
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
    print("🎯 KPI CONSISTENCY TEST (CRITICAL)")
    print("="*60)
    
    # Test database connection first
    success_db, _ = test_endpoint_with_timeout('/api/analytics/test', 10)
    if not success_db:
        print("\n❌ Database connection failed - cannot proceed with KPI tests")
        return False
    
    # Test KPIs endpoint with longer timeout due to large dataset
    success_kpis, kpis_data = test_endpoint_with_timeout('/api/analytics/kpis', 60)
    
    # Test detailed calls with pagination to reduce load
    success_detailed, detailed_data = test_endpoint_with_timeout('/api/analytics/llamadas-detalladas?per_page=1', 30)
    
    # Test abandoned calls with pagination
    success_abandoned, abandoned_data = test_endpoint_with_timeout('/api/analytics/llamadas-abandonadas?per_page=1', 30)
    
    if success_kpis and success_detailed and success_abandoned:
        if kpis_data and detailed_data and abandoned_data:
            try:
                # Extract KPI values
                kpi_atendidas = kpis_data.get('llamadas_atendidas', {}).get('valor', 0)
                kpi_abandonadas = kpis_data.get('llamadas_abandonadas', {}).get('valor', 0)
                
                # Extract table counts
                table_atendidas = detailed_data.get('total', 0)
                table_abandonadas = abandoned_data.get('total', 0)
                
                print(f"\n   📊 KPI CONSISTENCY RESULTS:")
                print(f"   📈 Dashboard KPIs:")
                print(f"      - Llamadas Atendidas: {kpi_atendidas:,}")
                print(f"      - Llamadas Abandonadas: {kpi_abandonadas:,}")
                print(f"   📋 Table Counts:")
                print(f"      - Detailed Calls Total: {table_atendidas:,}")
                print(f"      - Abandoned Calls Total: {table_abandonadas:,}")
                
                # Check consistency
                atendidas_match = kpi_atendidas == table_atendidas
                abandonadas_match = kpi_abandonadas == table_abandonadas
                
                if atendidas_match and abandonadas_match:
                    print(f"\n   ✅ KPI CONSISTENCY CHECK PASSED!")
                    print(f"      ✅ Atendidas match: {kpi_atendidas:,}")
                    print(f"      ✅ Abandonadas match: {kpi_abandonadas:,}")
                    print(f"\n🎉 SUCCESS: KPI fix is working correctly!")
                    return True
                else:
                    print(f"\n   ❌ KPI CONSISTENCY CHECK FAILED!")
                    if not atendidas_match:
                        print(f"      ❌ Atendidas mismatch: KPI={kpi_atendidas:,} vs Table={table_atendidas:,}")
                    if not abandonadas_match:
                        print(f"      ❌ Abandonadas mismatch: KPI={kpi_abandonadas:,} vs Table={table_abandonadas:,}")
                    print(f"\n⚠️  ISSUE: KPI consistency problem still exists!")
                    return False
                
            except Exception as e:
                print(f"\n   💥 ERROR parsing KPI data: {str(e)}")
                return False
        else:
            print(f"\n   ⚠️  Some endpoints returned empty data")
            return False
    else:
        print(f"\n   ⚠️  Cannot perform consistency check - one or more endpoints failed")
        if not success_kpis:
            print(f"      - KPIs endpoint failed")
        if not success_detailed:
            print(f"      - Detailed calls endpoint failed")
        if not success_abandoned:
            print(f"      - Abandoned calls endpoint failed")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 KPI consistency test PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️  KPI consistency test FAILED!")
        sys.exit(1)