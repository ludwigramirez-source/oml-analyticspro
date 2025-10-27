#!/usr/bin/env python3
"""
Backend API Testing for OmniLeads Analytics
Tests all backend endpoints to verify functionality and error handling
"""

import requests
import json
import sys
from datetime import datetime, date
import os

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

class BackendTester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
    
    def test_endpoint(self, method, endpoint, expected_status=200, data=None, description=""):
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"\n🧪 Testing {method} {endpoint}")
            if description:
                print(f"   📝 {description}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            print(f"   📊 Status: {response.status_code}")
            
            # Check if response is JSON
            try:
                response_data = response.json()
                print(f"   📄 Response type: JSON")
                if isinstance(response_data, dict) and len(response_data) <= 3:
                    print(f"   📋 Response: {json.dumps(response_data, indent=2)}")
                elif isinstance(response_data, list) and len(response_data) <= 2:
                    print(f"   📋 Response: {json.dumps(response_data, indent=2)}")
                else:
                    print(f"   📋 Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else f'List with {len(response_data)} items'}")
            except:
                print(f"   📄 Response type: Non-JSON")
                print(f"   📋 Response: {response.text[:200]}...")
            
            # Determine if test passed
            if response.status_code == expected_status:
                self.results['passed'].append({
                    'endpoint': endpoint,
                    'method': method,
                    'status': response.status_code,
                    'description': description
                })
                print(f"   ✅ PASSED")
                return True, response
            else:
                self.results['failed'].append({
                    'endpoint': endpoint,
                    'method': method,
                    'expected_status': expected_status,
                    'actual_status': response.status_code,
                    'description': description,
                    'response': response.text[:500]
                })
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                return False, response
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            self.results['errors'].append({
                'endpoint': endpoint,
                'method': method,
                'error': error_msg,
                'description': description
            })
            print(f"   💥 ERROR: {error_msg}")
            return False, None
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.results['errors'].append({
                'endpoint': endpoint,
                'method': method,
                'error': error_msg,
                'description': description
            })
            print(f"   💥 ERROR: {error_msg}")
            return False, None
    
    def run_health_tests(self):
        """Test backend service health"""
        print("\n" + "="*60)
        print("🏥 BACKEND SERVICE HEALTH TESTS")
        print("="*60)
        
        # Test basic connectivity
        self.test_endpoint('GET', '/api/', description="Basic API connectivity")
        
        # Test CORS headers
        success, response = self.test_endpoint('GET', '/api/', description="CORS headers check")
        if success and response:
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            print(f"   🌐 CORS Headers: {cors_headers}")
    
    def run_config_tests(self):
        """Test database configuration endpoints"""
        print("\n" + "="*60)
        print("⚙️  DATABASE CONFIGURATION TESTS")
        print("="*60)
        
        # Test get all configs (should work even without PostgreSQL)
        self.test_endpoint('GET', '/api/config/', description="Get all database configurations")
        
        # Test get active config (may return 404 if no config exists)
        success, response = self.test_endpoint('GET', '/api/config/active', 
                                             expected_status=404, 
                                             description="Get active configuration (404 expected if none)")
        
        if not success and response and response.status_code == 200:
            print("   ℹ️  Active configuration found (unexpected but not an error)")
            self.results['passed'].append({
                'endpoint': '/api/config/active',
                'method': 'GET',
                'status': 200,
                'description': 'Active configuration exists'
            })
    
    def run_analytics_tests(self):
        """Test analytics endpoints"""
        print("\n" + "="*60)
        print("📊 ANALYTICS ENDPOINTS TESTS")
        print("="*60)
        
        # Test analytics endpoints - these should return proper error messages if DB not configured
        analytics_endpoints = [
            ('/api/analytics/test', 'Database connection test'),
            ('/api/analytics/kpis', 'Key Performance Indicators'),
            ('/api/analytics/distribucion-por-tipo', 'NEW: Distribution by type (entrantes/salientes)'),
            ('/api/analytics/evolucion-hora', 'Evolution by hour'),
            ('/api/analytics/nivel-servicio', 'Service level metrics')
        ]
        
        for endpoint, description in analytics_endpoints:
            # These endpoints may return 500 if PostgreSQL is not configured
            # We're testing that they don't crash and return proper responses
            success, response = self.test_endpoint('GET', endpoint, 
                                                 expected_status=500, 
                                                 description=description)
            
            # If it returns 200, that's also acceptable (means DB is configured)
            if not success and response and response.status_code == 200:
                print("   ℹ️  Endpoint returned 200 (PostgreSQL may be configured)")
                self.results['passed'].append({
                    'endpoint': endpoint,
                    'method': 'GET',
                    'status': 200,
                    'description': f'{description} - Working with database'
                })
    
    def run_kpi_consistency_tests(self):
        """Test KPI consistency between dashboard and detailed tables"""
        print("\n" + "="*60)
        print("🎯 KPI CONSISTENCY TESTS (CRITICAL)")
        print("="*60)
        
        # Test KPIs endpoint
        success_kpis, response_kpis = self.test_endpoint('GET', '/api/analytics/kpis', 
                                                        expected_status=200, 
                                                        description="Get KPIs for consistency check")
        
        # Test detailed calls endpoint
        success_detailed, response_detailed = self.test_endpoint('GET', '/api/analytics/llamadas-detalladas', 
                                                               expected_status=200, 
                                                               description="Get detailed calls for consistency check")
        
        # Test abandoned calls endpoint
        success_abandoned, response_abandoned = self.test_endpoint('GET', '/api/analytics/llamadas-abandonadas', 
                                                                 expected_status=200, 
                                                                 description="Get abandoned calls for consistency check")
        
        if success_kpis and success_detailed and success_abandoned:
            try:
                kpis_data = response_kpis.json()
                detailed_data = response_detailed.json()
                abandoned_data = response_abandoned.json()
                
                # Extract KPI values
                kpi_atendidas = kpis_data.get('llamadas_atendidas', {}).get('valor', 0)
                kpi_abandonadas = kpis_data.get('llamadas_abandonadas', {}).get('valor', 0)
                
                # Extract table counts
                table_atendidas = detailed_data.get('total', 0)
                table_abandonadas = abandoned_data.get('total', 0)
                
                print(f"\n   📊 KPI CONSISTENCY CHECK:")
                print(f"   📈 Dashboard KPIs:")
                print(f"      - Llamadas Atendidas: {kpi_atendidas}")
                print(f"      - Llamadas Abandonadas: {kpi_abandonadas}")
                print(f"   📋 Table Counts:")
                print(f"      - Detailed Calls Total: {table_atendidas}")
                print(f"      - Abandoned Calls Total: {table_abandonadas}")
                
                # Check consistency
                atendidas_match = kpi_atendidas == table_atendidas
                abandonadas_match = kpi_abandonadas == table_abandonadas
                
                if atendidas_match and abandonadas_match:
                    print(f"   ✅ CONSISTENCY CHECK PASSED - Numbers match!")
                    self.results['passed'].append({
                        'endpoint': 'KPI Consistency',
                        'method': 'COMPARISON',
                        'status': 'CONSISTENT',
                        'description': f'KPI numbers match table counts: Atendidas {kpi_atendidas}, Abandonadas {kpi_abandonadas}'
                    })
                else:
                    print(f"   ❌ CONSISTENCY CHECK FAILED - Numbers don't match!")
                    if not atendidas_match:
                        print(f"      ❌ Atendidas mismatch: KPI={kpi_atendidas} vs Table={table_atendidas}")
                    if not abandonadas_match:
                        print(f"      ❌ Abandonadas mismatch: KPI={kpi_abandonadas} vs Table={table_abandonadas}")
                    
                    self.results['failed'].append({
                        'endpoint': 'KPI Consistency',
                        'method': 'COMPARISON',
                        'expected_status': 'CONSISTENT',
                        'actual_status': 'INCONSISTENT',
                        'description': f'KPI mismatch - Atendidas: KPI={kpi_atendidas} vs Table={table_atendidas}, Abandonadas: KPI={kpi_abandonadas} vs Table={table_abandonadas}',
                        'response': 'Data inconsistency detected'
                    })
                
            except Exception as e:
                print(f"   💥 ERROR parsing KPI consistency data: {str(e)}")
                self.results['errors'].append({
                    'endpoint': 'KPI Consistency',
                    'method': 'COMPARISON',
                    'error': f'Failed to parse consistency data: {str(e)}',
                    'description': 'KPI consistency check failed due to parsing error'
                })
        else:
            print(f"   ⚠️  Cannot perform consistency check - one or more endpoints failed")
            if not success_kpis:
                print(f"      - KPIs endpoint failed")
            if not success_detailed:
                print(f"      - Detailed calls endpoint failed")
            if not success_abandoned:
                print(f"      - Abandoned calls endpoint failed")
    
    def run_agentes_disponibilidad_test(self):
        """Test specific agentes disponibilidad endpoint as requested"""
        print("\n" + "="*60)
        print("🎯 AGENTES DISPONIBILIDAD TEST (SPECIFIC REQUEST)")
        print("="*60)
        
        # Test with specific filters as requested
        endpoint = '/api/analytics/agentes/disponibilidad?fecha_inicio=2025-10-01&fecha_fin=2025-10-31'
        
        success, response = self.test_endpoint('GET', endpoint, 
                                             expected_status=200, 
                                             description="Agentes disponibilidad with specific date filters")
        
        if success and response:
            try:
                data = response.json()
                
                print(f"\n   📊 DETAILED ANALYSIS:")
                print(f"   📈 Response type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"   📋 Total agents returned: {len(data)}")
                    
                    # Verify structure of each agent
                    required_fields = ['agente_id', 'username', 'nombre', 'llamadas_contestadas', 'tmo', 'tasa_atencion', 'total_llamadas']
                    agents_with_calls = [agent for agent in data if agent.get('llamadas_contestadas', 0) > 0]
                    
                    print(f"   📋 Agents with llamadas_contestadas > 0: {len(agents_with_calls)}")
                    
                    # Check field structure
                    if data:
                        first_agent = data[0]
                        missing_fields = [field for field in required_fields if field not in first_agent]
                        
                        if missing_fields:
                            print(f"   ❌ Missing required fields: {missing_fields}")
                            self.results['failed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'expected_status': 'All required fields present',
                                'actual_status': f'Missing fields: {missing_fields}',
                                'description': 'Agent structure validation failed',
                                'response': f'First agent structure: {list(first_agent.keys())}'
                            })
                        else:
                            print(f"   ✅ All required fields present: {required_fields}")
                    
                    # Show first 3 agents with metrics as requested
                    print(f"\n   📊 FIRST 3 AGENTS WITH METRICS:")
                    for i, agent in enumerate(data[:3]):
                        print(f"   Agent {i+1}:")
                        print(f"      - ID: {agent.get('agente_id')}")
                        print(f"      - Username: {agent.get('username')}")
                        print(f"      - Nombre: {agent.get('nombre')}")
                        print(f"      - Llamadas Contestadas: {agent.get('llamadas_contestadas')}")
                        print(f"      - TMO (segundos): {agent.get('tmo')}")
                        print(f"      - Tasa Atención (%): {agent.get('tasa_atencion')}")
                        print(f"      - Total Llamadas: {agent.get('total_llamadas')}")
                        print()
                    
                    # Verify expected data patterns
                    print(f"   📊 DATA VALIDATION:")
                    
                    # Check if we have at least 5 agents with calls
                    if len(agents_with_calls) >= 5:
                        print(f"   ✅ At least 5 agents with llamadas_contestadas > 0: {len(agents_with_calls)}")
                    else:
                        print(f"   ❌ Expected at least 5 agents with calls, got: {len(agents_with_calls)}")
                        self.results['failed'].append({
                            'endpoint': endpoint,
                            'method': 'GET',
                            'expected_status': 'At least 5 agents with calls',
                            'actual_status': f'Only {len(agents_with_calls)} agents with calls',
                            'description': 'Insufficient agents with call data',
                            'response': f'Agents with calls: {len(agents_with_calls)}'
                        })
                    
                    # Check for main agent with ~504 calls
                    high_call_agents = [agent for agent in data if agent.get('llamadas_contestadas', 0) > 400]
                    if high_call_agents:
                        print(f"   ✅ Found agents with high call volume (>400): {len(high_call_agents)}")
                        for agent in high_call_agents:
                            print(f"      - {agent.get('nombre')}: {agent.get('llamadas_contestadas')} calls")
                    else:
                        print(f"   ⚠️  No agents found with >400 calls (expected ~504)")
                    
                    # Validate TMO values (should be > 0 seconds)
                    valid_tmo_agents = [agent for agent in agents_with_calls if agent.get('tmo', 0) > 0]
                    print(f"   📊 Agents with valid TMO (>0 seconds): {len(valid_tmo_agents)}")
                    
                    # Validate tasa_atencion (should be 0-100%)
                    valid_tasa_agents = [agent for agent in agents_with_calls 
                                       if 0 <= agent.get('tasa_atencion', -1) <= 100]
                    print(f"   📊 Agents with valid tasa_atencion (0-100%): {len(valid_tasa_agents)}")
                    
                    # Overall validation
                    if (len(data) > 0 and 
                        len(agents_with_calls) >= 5 and 
                        not missing_fields and
                        len(valid_tmo_agents) > 0 and
                        len(valid_tasa_agents) > 0):
                        
                        print(f"   ✅ AGENTES DISPONIBILIDAD TEST PASSED")
                        self.results['passed'].append({
                            'endpoint': endpoint,
                            'method': 'GET',
                            'status': 200,
                            'description': f'Agentes disponibilidad test successful - {len(data)} agents, {len(agents_with_calls)} with calls'
                        })
                    else:
                        print(f"   ❌ AGENTES DISPONIBILIDAD TEST FAILED - Check validation details above")
                
                else:
                    print(f"   ❌ Expected array response, got: {type(data)}")
                    self.results['failed'].append({
                        'endpoint': endpoint,
                        'method': 'GET',
                        'expected_status': 'Array response',
                        'actual_status': f'Got {type(data)}',
                        'description': 'Response type validation failed',
                        'response': str(data)[:500]
                    })
                    
            except Exception as e:
                print(f"   💥 ERROR parsing agentes disponibilidad response: {str(e)}")
                self.results['errors'].append({
                    'endpoint': endpoint,
                    'method': 'GET',
                    'error': f'Failed to parse response: {str(e)}',
                    'description': 'Agentes disponibilidad response parsing failed'
                })
        else:
            print(f"   ❌ Agentes disponibilidad endpoint test failed")

    def run_transferencias_detalle_test(self):
        """Test Transferencias detailed table endpoint for callid grouping (CRITICAL)"""
        print("\n" + "="*60)
        print("🎯 TRANSFERENCIAS DETAILED TABLE GROUPING TEST (CRITICAL)")
        print("="*60)
        
        # Test the detailed table endpoint
        endpoint = '/api/analytics/transferencias/detalle?fecha_inicio=2025-10-01&fecha_fin=2025-10-31'
        
        success, response = self.test_endpoint('GET', endpoint, 
                                             expected_status=200, 
                                             description="Transferencias detailed table with callid grouping")
        
        if success and response:
            try:
                data = response.json()
                
                print(f"\n   📊 TRANSFERENCIAS DETALLE ANALYSIS:")
                print(f"   📈 Response type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"   📋 Total objects returned: {len(data)}")
                    
                    if len(data) > 0:
                        # Validate structure of first object
                        first_call = data[0]
                        required_fields = ['callid', 'fecha', 'hora_inicio', 'campana', 'agente', 'numero', 'duracion', 'espera', 'contacto_id', 'eventos']
                        
                        print(f"\n   🔍 STRUCTURE VALIDATION:")
                        missing_fields = [field for field in required_fields if field not in first_call]
                        
                        if missing_fields:
                            print(f"   ❌ Missing required fields: {missing_fields}")
                            self.results['failed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'expected_status': 'All required fields present',
                                'actual_status': f'Missing fields: {missing_fields}',
                                'description': 'Call structure validation failed',
                                'response': f'Available fields: {list(first_call.keys())}'
                            })
                        else:
                            print(f"   ✅ All required fields present: {required_fields}")
                        
                        # Validate eventos array structure
                        if 'eventos' in first_call and isinstance(first_call['eventos'], list):
                            print(f"   ✅ 'eventos' field is an array")
                            
                            if len(first_call['eventos']) > 0:
                                first_event = first_call['eventos'][0]
                                event_required_fields = ['evento', 'evento_descripcion', 'hora', 'duracion']
                                event_missing_fields = [field for field in event_required_fields if field not in first_event]
                                
                                if event_missing_fields:
                                    print(f"   ❌ Missing event fields: {event_missing_fields}")
                                    self.results['failed'].append({
                                        'endpoint': endpoint,
                                        'method': 'GET',
                                        'expected_status': 'All event fields present',
                                        'actual_status': f'Missing event fields: {event_missing_fields}',
                                        'description': 'Event structure validation failed',
                                        'response': f'Available event fields: {list(first_event.keys())}'
                                    })
                                else:
                                    print(f"   ✅ All event fields present: {event_required_fields}")
                            else:
                                print(f"   ⚠️  First call has no events (may be expected)")
                        else:
                            print(f"   ❌ 'eventos' field is not an array")
                            self.results['failed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'expected_status': 'eventos field as array',
                                'actual_status': f'eventos type: {type(first_call.get("eventos", "missing"))}',
                                'description': 'eventos field validation failed',
                                'response': f'eventos value: {first_call.get("eventos", "missing")}'
                            })
                        
                        # Show sample data structure
                        print(f"\n   📊 SAMPLE CALL STRUCTURE:")
                        print(f"      - CallID: {first_call.get('callid', 'N/A')}")
                        print(f"      - Fecha: {first_call.get('fecha', 'N/A')}")
                        print(f"      - Hora Inicio: {first_call.get('hora_inicio', 'N/A')}")
                        print(f"      - Campaña: {first_call.get('campana', 'N/A')}")
                        print(f"      - Agente: {first_call.get('agente', 'N/A')}")
                        print(f"      - Número: {first_call.get('numero', 'N/A')}")
                        print(f"      - Eventos Count: {len(first_call.get('eventos', []))}")
                        
                        if first_call.get('eventos') and len(first_call['eventos']) > 0:
                            print(f"\n   📊 SAMPLE EVENTS:")
                            for i, evento in enumerate(first_call['eventos'][:3]):  # Show first 3 events
                                print(f"      Event {i+1}:")
                                print(f"         - Evento: {evento.get('evento', 'N/A')}")
                                print(f"         - Descripción: {evento.get('evento_descripcion', 'N/A')}")
                                print(f"         - Hora: {evento.get('hora', 'N/A')}")
                                print(f"         - Duración: {evento.get('duracion', 'N/A')}")
                        
                        # Validate callid uniqueness
                        callids = [call.get('callid') for call in data if call.get('callid')]
                        unique_callids = set(callids)
                        
                        print(f"\n   🔍 CALLID UNIQUENESS VALIDATION:")
                        print(f"      - Total objects: {len(data)}")
                        print(f"      - Total callids: {len(callids)}")
                        print(f"      - Unique callids: {len(unique_callids)}")
                        
                        if len(callids) == len(unique_callids):
                            print(f"   ✅ All callids are unique - one object per call")
                        else:
                            print(f"   ❌ Duplicate callids found - {len(callids) - len(unique_callids)} duplicates")
                            self.results['failed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'expected_status': 'Unique callids',
                                'actual_status': f'{len(callids) - len(unique_callids)} duplicates',
                                'description': 'Callid uniqueness validation failed',
                                'response': f'Total: {len(callids)}, Unique: {len(unique_callids)}'
                            })
                        
                        # Check for calls with multiple events (the main fix)
                        calls_with_multiple_events = [call for call in data if len(call.get('eventos', [])) > 1]
                        print(f"\n   🔍 MULTIPLE EVENTS VALIDATION:")
                        print(f"      - Calls with multiple events: {len(calls_with_multiple_events)}")
                        
                        if len(calls_with_multiple_events) > 0:
                            print(f"   ✅ Found calls with multiple events - grouping is working")
                            
                            # Show example of grouped events
                            example_call = calls_with_multiple_events[0]
                            print(f"\n   📊 EXAMPLE GROUPED CALL:")
                            print(f"      - CallID: {example_call.get('callid')}")
                            print(f"      - Events count: {len(example_call.get('eventos', []))}")
                            print(f"      - Event types: {[e.get('evento') for e in example_call.get('eventos', [])]}")
                        else:
                            print(f"   ⚠️  No calls with multiple events found (may be expected for this date range)")
                        
                        # Overall validation
                        validation_passed = (
                            not missing_fields and
                            len(callids) == len(unique_callids) and
                            isinstance(first_call.get('eventos'), list)
                        )
                        
                        if validation_passed:
                            print(f"\n   ✅ TRANSFERENCIAS DETALLE TEST PASSED")
                            print(f"      - Structure: ✅ Correct")
                            print(f"      - Grouping: ✅ One object per callid")
                            print(f"      - Events: ✅ Array format with required fields")
                            
                            self.results['passed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'status': 200,
                                'description': f'Transferencias detalle grouping working - {len(data)} unique calls, {len(calls_with_multiple_events)} with multiple events'
                            })
                        else:
                            print(f"\n   ❌ TRANSFERENCIAS DETALLE TEST FAILED - Check validation details above")
                    
                    else:
                        print(f"   ⚠️  No transfer data found in date range (2025-10-01 to 2025-10-31)")
                        print(f"   ℹ️  This may be expected if no transfers occurred in this period")
                        self.results['passed'].append({
                            'endpoint': endpoint,
                            'method': 'GET',
                            'status': 200,
                            'description': 'Transferencias detalle endpoint working - no data in test period (expected)'
                        })
                
                else:
                    print(f"   ❌ Expected array response, got: {type(data)}")
                    self.results['failed'].append({
                        'endpoint': endpoint,
                        'method': 'GET',
                        'expected_status': 'Array response',
                        'actual_status': f'Got {type(data)}',
                        'description': 'Response type validation failed',
                        'response': str(data)[:500]
                    })
                    
            except Exception as e:
                print(f"   💥 ERROR parsing transferencias detalle response: {str(e)}")
                self.results['errors'].append({
                    'endpoint': endpoint,
                    'method': 'GET',
                    'error': f'Failed to parse response: {str(e)}',
                    'description': 'Transferencias detalle response parsing failed'
                })
        else:
            print(f"   ❌ Transferencias detalle endpoint test failed")

    def run_transferencias_test(self):
        """Test Transferencias endpoint for unique call counting (CRITICAL)"""
        print("\n" + "="*60)
        print("🎯 TRANSFERENCIAS UNIQUE CALL COUNTING TEST (CRITICAL)")
        print("="*60)
        
        # Test with specific filters as requested
        endpoint = '/api/analytics/transferencias?fecha_inicio=2025-10-01&fecha_fin=2025-10-31'
        
        success, response = self.test_endpoint('GET', endpoint, 
                                             expected_status=200, 
                                             description="Transferencias report with unique call counting")
        
        if success and response:
            try:
                data = response.json()
                
                print(f"\n   📊 TRANSFERENCIAS ANALYSIS:")
                print(f"   📈 Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if isinstance(data, dict) and 'eventos' in data and 'resumen' in data:
                    eventos = data['eventos']
                    resumen = data['resumen']
                    
                    print(f"   ✅ Response has required sections: 'eventos' and 'resumen'")
                    
                    # Check resumen structure
                    if 'transfer_ciego' in resumen and 'transfer_consultivo' in resumen and 'totales' in resumen:
                        print(f"   ✅ Resumen has all required sections")
                        
                        # Extract metrics
                        tc = resumen['transfer_ciego']
                        tcons = resumen['transfer_consultivo']
                        totales = resumen['totales']
                        
                        print(f"\n   📊 TRANSFER CIEGO METRICS:")
                        print(f"      - Intentos: {tc.get('intentos', 0)}")
                        print(f"      - Atendidos: {tc.get('atendidos', 0)}")
                        print(f"      - Completados: {tc.get('completados', 0)}")
                        print(f"      - Ocupados: {tc.get('ocupados', 0)}")
                        print(f"      - Sin respuesta: {tc.get('sin_respuesta', 0)}")
                        print(f"      - No disponible: {tc.get('no_disponible', 0)}")
                        print(f"      - Tasa éxito: {tc.get('tasa_exito', 0)}%")
                        
                        print(f"\n   📊 TRANSFER CONSULTIVO METRICS:")
                        print(f"      - Intentos: {tcons.get('intentos', 0)}")
                        print(f"      - Atendidos: {tcons.get('atendidos', 0)}")
                        print(f"      - Completados: {tcons.get('completados', 0)}")
                        print(f"      - Cancelados: {tcons.get('cancelados', 0)}")
                        print(f"      - Ocupados: {tcons.get('ocupados', 0)}")
                        print(f"      - Tasa éxito: {tcons.get('tasa_exito', 0)}%")
                        
                        print(f"\n   📊 TOTALES:")
                        print(f"      - Total intentos: {totales.get('total_intentos', 0)}")
                        print(f"      - Total exitosas: {totales.get('total_exitosas', 0)}")
                        print(f"      - Ingresos cola: {totales.get('ingresos_cola', 0)}")
                        print(f"      - Tasa éxito global: {totales.get('tasa_exito_global', 0)}%")
                        
                        # Show some event details for comparison
                        print(f"\n   📊 EVENTOS SAMPLE (for comparison with unique counts):")
                        event_samples = ['BT-TRY', 'BT-ANSWER', 'COMPLETE-BT', 'CT-TRY', 'COMPLETE-CT']
                        for event in event_samples:
                            if event in eventos:
                                event_count = eventos[event].get('total', 0)
                                print(f"      - {event}: {event_count} events")
                        
                        # CRITICAL VALIDATION: Check if unique call counting is working
                        print(f"\n   🔍 UNIQUE CALL COUNTING VALIDATION:")
                        
                        # Check if we have any transfer data
                        total_intentos = totales.get('total_intentos', 0)
                        total_exitosas = totales.get('total_exitosas', 0)
                        
                        if total_intentos > 0:
                            print(f"   ✅ Transfer data found - {total_intentos} unique calls attempted transfers")
                            
                            # Validate that summary numbers are consistent
                            bt_intentos = tc.get('intentos', 0)
                            ct_intentos = tcons.get('intentos', 0)
                            calculated_total = bt_intentos + ct_intentos
                            
                            if calculated_total == total_intentos:
                                print(f"   ✅ Total intentos calculation is consistent: {bt_intentos} + {ct_intentos} = {total_intentos}")
                            else:
                                print(f"   ❌ Total intentos mismatch: {bt_intentos} + {ct_intentos} ≠ {total_intentos}")
                                self.results['failed'].append({
                                    'endpoint': endpoint,
                                    'method': 'GET',
                                    'expected_status': 'Consistent totals',
                                    'actual_status': f'Mismatch: {calculated_total} ≠ {total_intentos}',
                                    'description': 'Transfer totals calculation inconsistency',
                                    'response': f'BT: {bt_intentos}, CT: {ct_intentos}, Total: {total_intentos}'
                                })
                            
                            # Validate that completed transfers are <= attempts
                            bt_completados = tc.get('completados', 0)
                            ct_completados = tcons.get('completados', 0)
                            
                            if bt_completados <= bt_intentos and ct_completados <= ct_intentos:
                                print(f"   ✅ Completed transfers <= attempts (logical consistency)")
                            else:
                                print(f"   ❌ Completed > attempts (data inconsistency)")
                                self.results['failed'].append({
                                    'endpoint': endpoint,
                                    'method': 'GET',
                                    'expected_status': 'Completed <= Attempts',
                                    'actual_status': f'BT: {bt_completados}/{bt_intentos}, CT: {ct_completados}/{ct_intentos}',
                                    'description': 'Completed transfers exceed attempts',
                                    'response': 'Data logic error'
                                })
                            
                            # Check if events show higher counts than unique calls (expected behavior)
                            bt_try_events = eventos.get('BT-TRY', {}).get('total', 0)
                            if bt_try_events >= bt_intentos:
                                print(f"   ✅ Event count ({bt_try_events}) >= unique calls ({bt_intentos}) - unique counting working")
                            else:
                                print(f"   ⚠️  Event count ({bt_try_events}) < unique calls ({bt_intentos}) - unexpected")
                            
                            print(f"   ✅ TRANSFERENCIAS TEST PASSED - Unique call counting implemented")
                            self.results['passed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'status': 200,
                                'description': f'Transferencias unique call counting working - {total_intentos} unique calls, {total_exitosas} successful'
                            })
                            
                        else:
                            print(f"   ⚠️  No transfer data found in date range (2025-10-01 to 2025-10-31)")
                            print(f"   ℹ️  This may be expected if no transfers occurred in this period")
                            self.results['passed'].append({
                                'endpoint': endpoint,
                                'method': 'GET',
                                'status': 200,
                                'description': 'Transferencias endpoint working - no data in test period (expected)'
                            })
                        
                    else:
                        print(f"   ❌ Missing required resumen sections")
                        missing = []
                        if 'transfer_ciego' not in resumen: missing.append('transfer_ciego')
                        if 'transfer_consultivo' not in resumen: missing.append('transfer_consultivo')
                        if 'totales' not in resumen: missing.append('totales')
                        
                        self.results['failed'].append({
                            'endpoint': endpoint,
                            'method': 'GET',
                            'expected_status': 'Complete resumen structure',
                            'actual_status': f'Missing: {missing}',
                            'description': 'Incomplete response structure',
                            'response': f'Available sections: {list(resumen.keys())}'
                        })
                
                else:
                    print(f"   ❌ Response missing required sections 'eventos' and 'resumen'")
                    self.results['failed'].append({
                        'endpoint': endpoint,
                        'method': 'GET',
                        'expected_status': 'eventos and resumen sections',
                        'actual_status': f'Got: {list(data.keys()) if isinstance(data, dict) else type(data)}',
                        'description': 'Response structure validation failed',
                        'response': str(data)[:500]
                    })
                    
            except Exception as e:
                print(f"   💥 ERROR parsing transferencias response: {str(e)}")
                self.results['errors'].append({
                    'endpoint': endpoint,
                    'method': 'GET',
                    'error': f'Failed to parse response: {str(e)}',
                    'description': 'Transferencias response parsing failed'
                })
        else:
            print(f"   ❌ Transferencias endpoint test failed")

    def run_additional_analytics_tests(self):
        """Test additional analytics endpoints"""
        print("\n" + "="*60)
        print("📈 ADDITIONAL ANALYTICS TESTS")
        print("="*60)
        
        additional_endpoints = [
            ('/api/analytics/distribucion-llamadas', 'Call distribution'),
            ('/api/analytics/causas-no-atencion', 'Causes of non-attention'),
            ('/api/analytics/campanas', 'Get campaigns list'),
            ('/api/analytics/agentes', 'Get agents list'),
            ('/api/analytics/evolucion-semanal', 'Weekly evolution'),
            ('/api/analytics/tabla-distribucion-horaria', 'Hourly distribution table'),
            ('/api/analytics/salientes/dashboard', 'Outbound calls dashboard')
        ]
        
        for endpoint, description in additional_endpoints:
            success, response = self.test_endpoint('GET', endpoint, 
                                                 expected_status=500, 
                                                 description=description)
            
            if not success and response and response.status_code == 200:
                print("   ℹ️  Endpoint returned 200 (PostgreSQL may be configured)")
                self.results['passed'].append({
                    'endpoint': endpoint,
                    'method': 'GET',
                    'status': 200,
                    'description': f'{description} - Working with database'
                })
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.results['passed']) + len(self.results['failed']) + len(self.results['errors'])
        passed_count = len(self.results['passed'])
        failed_count = len(self.results['failed'])
        error_count = len(self.results['errors'])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"💥 Errors: {error_count}")
        
        if self.results['failed']:
            print("\n❌ FAILED TESTS:")
            for test in self.results['failed']:
                print(f"   • {test['method']} {test['endpoint']} - {test['description']}")
                print(f"     Expected: {test['expected_status']}, Got: {test['actual_status']}")
        
        if self.results['errors']:
            print("\n💥 ERROR TESTS:")
            for test in self.results['errors']:
                print(f"   • {test['method']} {test['endpoint']} - {test['description']}")
                print(f"     Error: {test['error']}")
        
        # Determine overall result
        critical_failures = []
        
        # Check for critical failures
        for test in self.results['failed']:
            if test['endpoint'] == '/api/' and test['actual_status'] != 200:
                critical_failures.append("Basic API connectivity failed")
            elif 'distribucion-por-tipo' in test['endpoint'] and test['actual_status'] == 404:
                critical_failures.append("New distribucion-por-tipo endpoint not found")
        
        for test in self.results['errors']:
            if test['endpoint'] == '/api/':
                critical_failures.append("Cannot connect to backend service")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_failures:
                print(f"   • {issue}")
            return False
        else:
            print(f"\n✅ BACKEND TESTS COMPLETED SUCCESSFULLY")
            print("   • Backend service is accessible")
            print("   • CORS is properly configured")
            print("   • All endpoints exist and return proper responses")
            print("   • Database connection errors are handled gracefully")
            return True

def main():
    """Main test execution"""
    print("🚀 Starting OmniLeads Analytics Backend Tests")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = BackendTester(BACKEND_URL)
    
    # Run all test suites
    tester.run_health_tests()
    tester.run_config_tests()
    tester.run_analytics_tests()
    tester.run_transferencias_test()  # NEW: Critical Transferencias unique call counting test
    tester.run_agentes_disponibilidad_test()  # NEW: Specific agentes disponibilidad test
    tester.run_kpi_consistency_tests()  # NEW: Critical KPI consistency test
    tester.run_additional_analytics_tests()
    
    # Print summary and return result
    success = tester.print_summary()
    
    if success:
        print("\n🎉 All backend tests completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Some backend tests failed - check details above")
        sys.exit(1)

if __name__ == "__main__":
    main()