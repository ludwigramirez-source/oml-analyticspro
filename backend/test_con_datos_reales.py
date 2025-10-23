"""
Script para validar cálculos con datos reales del CSV
"""
import pandas as pd

# Datos del CSV compartido
print("=" * 80)
print("VALIDACIÓN DE DATOS SEGÚN REPORTES OFICIALES")
print("=" * 80)

# Datos de llamadas_por_tipo.csv
print("\n1. LLAMADAS POR TIPO (según reporte oficial):")
print("-" * 80)
datos_oficiales = {
    'Manual': {
        'total': 239,
        'conectadas': 150,
        'no_conectadas': 88,
        'atendidas': None,
        'no_atendidas': None
    },
    'Dialer': {
        'total': 0,
        'conectadas': 0,
        'no_conectadas': 0,
        'atendidas': None,
        'no_atendidas': None
    },
    'Entrante': {
        'total': 2138,
        'conectadas': None,
        'no_conectadas': None,
        'atendidas': 1669,
        'no_atendidas': 179,
        'expiradas': 0,
        'abandonadas': 290
    }
}

for tipo, datos in datos_oficiales.items():
    print(f"\n{tipo}:")
    for key, value in datos.items():
        if value is not None:
            print(f"  {key}: {value}")

print("\n" + "=" * 80)
print("VALIDACIONES:")
print("=" * 80)

# Validar que los números cuadren
print("\n2. ENTRANTES - Validación:")
entrantes = datos_oficiales['Entrante']
total_entrantes = entrantes['atendidas'] + entrantes['no_atendidas'] + entrantes['abandonadas'] + entrantes['expiradas']
print(f"  Atendidas + No Atendidas + Abandonadas + Expiradas:")
print(f"  {entrantes['atendidas']} + {entrantes['no_atendidas']} + {entrantes['abandonadas']} + {entrantes['expiradas']} = {total_entrantes}")
print(f"  Total reportado: {entrantes['total']}")
print(f"  Diferencia: {entrantes['total'] - total_entrantes}")
print(f"  ⚠️ NOTA: La diferencia podría ser por llamadas en otros estados")

print("\n3. SALIENTES - Validación:")
manuales = datos_oficiales['Manual']
total_manuales = manuales['conectadas'] + manuales['no_conectadas']
print(f"  Conectadas + No Conectadas:")
print(f"  {manuales['conectadas']} + {manuales['no_conectadas']} = {total_manuales}")
print(f"  Total reportado: {manuales['total']}")
print(f"  Diferencia: {manuales['total'] - total_manuales}")
print(f"  ⚠️ Falta 1 llamada - probablemente en otro estado (BUSY, etc.)")

print("\n" + "=" * 80)
print("EVENTOS QUE DEBEN CONTARSE:")
print("=" * 80)

eventos_conteo = {
    'ENTRANTES': {
        'Atendidas': ['COMPLETEAGENT', 'COMPLETEOUTNUM'],
        'Abandonadas': ['ABANDON', 'ABANDONWEL', 'ABANDON-CTOUT'],
        'Expiradas': ['EXITWITHTIMEOUT'],
        'No Atendidas': ['Otros eventos finales entrantes']
    },
    'SALIENTES': {
        'Conectadas': ['COMPLETEAGENT', 'COMPLETEOUTNUM'],
        'No Conectadas': ['CANCEL', 'NOANSWER', 'BUSY', 'CHANUNAVAIL', 'NONDIALPLAN']
    }
}

for tipo, categorias in eventos_conteo.items():
    print(f"\n{tipo}:")
    for categoria, eventos in categorias.items():
        print(f"  {categoria}:")
        for evento in eventos:
            print(f"    - {evento}")

print("\n" + "=" * 80)
print("CÁLCULOS ESPERADOS EN EL DASHBOARD:")
print("=" * 80)

print("\nKPI: Total Llamadas")
print(f"  Esperado: {datos_oficiales['Manual']['total'] + datos_oficiales['Entrante']['total']} llamadas")
print(f"  (Manual: {datos_oficiales['Manual']['total']} + Entrante: {datos_oficiales['Entrante']['total']})")

print("\nKPI: Llamadas Atendidas")
print(f"  Esperado: {datos_oficiales['Manual']['conectadas'] + datos_oficiales['Entrante']['atendidas']} llamadas")
print(f"  (Manual Conectadas: {datos_oficiales['Manual']['conectadas']} + Entrantes Atendidas: {datos_oficiales['Entrante']['atendidas']})")

print("\nKPI: Llamadas Abandonadas")
print(f"  Esperado: {datos_oficiales['Entrante']['abandonadas']} llamadas")
print(f"  (Solo las entrantes se abandonan)")

print("\nKPI: Nivel de Atención")
atendidas_total = datos_oficiales['Manual']['conectadas'] + datos_oficiales['Entrante']['atendidas']
total_llamadas = datos_oficiales['Manual']['total'] + datos_oficiales['Entrante']['total']
nivel_atencion = round(atendidas_total / total_llamadas * 100, 2)
print(f"  Esperado: {nivel_atencion}%")
print(f"  ({atendidas_total} atendidas / {total_llamadas} total)")

print("\n" + "=" * 80)
