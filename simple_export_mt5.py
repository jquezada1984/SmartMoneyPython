#!/usr/bin/env python3
"""
Script simple para exportar datos de MetaTrader 5 a CSV
Este script exporta datos de EURUSD 5M para usar con generate_gif_enhanced.py
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smartmoneyconcepts.mt5_connector import MT5Connector

def main():
    """Función principal - exporta datos de EURUSD 5M"""
    
    print("🚀 Exportando datos de MetaTrader 5 para generate_gif_enhanced.py")
    print("=" * 60)
    
    # Configuración
    symbol = "EURUSD"
    timeframe = "5m"
    bars = 1000  # Últimas 1000 barras
    
    print(f"📊 Símbolo: {symbol}")
    print(f"⏰ Timeframe: {timeframe}")
    print(f"📈 Barras: {bars}")
    
    # Conectar a MT5
    print("\n📡 Conectando a MetaTrader 5...")
    mt5 = MT5Connector()
    
    if not mt5.connected:
        print("❌ No se pudo conectar a MT5. Verifica que MT5 esté abierto.")
        print("💡 Asegúrate de que MetaTrader 5 esté ejecutándose")
        return
    
    # Obtener datos
    print(f"\n📊 Obteniendo datos de {symbol}...")
    df = mt5.get_data(symbol, timeframe, bars)
    
    if df.empty:
        print("❌ No se pudieron obtener datos")
        mt5.disconnect()
        return
    
    print(f"✅ Datos obtenidos: {len(df)} barras")
    print(f"   Rango: {df.index[0]} a {df.index[-1]}")
    print(f"   Precio actual: {df['close'].iloc[-1]:.5f}")
    
    # Crear directorio de salida
    output_dir = "tests/test_data/EURUSD"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generar nombre de archivo
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"EURUSD_5M_{current_time}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Exportar a CSV
    print(f"\n💾 Exportando datos a CSV...")
    print(f"📁 Archivo: {filepath}")
    
    # Agregar columna datetime para compatibilidad
    df_export = df.reset_index()
    df_export.rename(columns={'time': 'datetime'}, inplace=True)
    
    # Renombrar 'real_volume' a 'volume' para compatibilidad con librerías
    if 'real_volume' in df_export.columns:
        df_export = df_export.rename(columns={'real_volume': 'volume'})
    
    # Asegurar que las columnas estén en el orden correcto
    columns_order = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df_export = df_export[columns_order]
    
    # Exportar
    df_export.to_csv(filepath, index=False)
    
    print(f"✅ Datos exportados exitosamente")
    print(f"📊 Resumen del archivo:")
    print(f"   - Registros: {len(df_export)}")
    print(f"   - Columnas: {list(df_export.columns)}")
    print(f"   - Tamaño: {os.path.getsize(filepath) / 1024:.1f} KB")
    
    # Desconectar de MT5
    mt5.disconnect()
    
    print(f"\n🎉 ¡Exportación completada!")
    print(f"📁 Archivo generado: {filepath}")
    print(f"\n💡 Para usar en generate_gif_enhanced.py:")
    print(f"   Cambia la línea 859 en generate_gif_enhanced.py:")
    print(f"   csv_path = \"{filepath}\"")
    
    # También crear un enlace simbólico con el nombre esperado
    expected_filename = "EURUSD_5M_2025_filtrado_fast.csv"
    expected_filepath = os.path.join(output_dir, expected_filename)
    
    try:
        # Crear una copia con el nombre esperado
        df_export.to_csv(expected_filepath, index=False)
        print(f"\n📋 También creado: {expected_filepath}")
        print(f"   Este archivo es compatible con generate_gif_enhanced.py sin cambios")
    except Exception as e:
        print(f"⚠️ No se pudo crear el archivo con nombre esperado: {e}")

if __name__ == "__main__":
    main() 