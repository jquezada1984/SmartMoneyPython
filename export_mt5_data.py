#!/usr/bin/env python3
"""
Script para exportar datos de MetaTrader 5 a CSV
Este script conecta con MT5, obtiene datos históricos y los exporta a archivos CSV
para su uso en análisis y generación de GIFs


python tests/generate_gif_enhanced.py# Exportar EURUSD 15M
python export_mt5_data.py --symbol EURUSD --timeframe 15m --bars 1000

# Exportación masiva
python export_mt5_data.py --batch
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import argparse

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from connectors.mt5_connector import MT5Connector

def export_data_to_csv(symbol: str, timeframe: str, bars: int = 10000, 
                       start_date: datetime = None, end_date: datetime = None,
                       output_dir: str = "tests/test_data") -> str:
    """
    Exporta datos de MetaTrader 5 a CSV
    
    Parámetros:
    symbol: str - Símbolo a exportar (ej: "EURUSD")
    timeframe: str - Timeframe ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M")
    bars: int - Número de barras a obtener
    start_date: datetime - Fecha de inicio (opcional)
    end_date: datetime - Fecha de fin (opcional)
    output_dir: str - Directorio de salida
    
    Retorna:
    str: Ruta del archivo CSV generado
    """
    
    print(f"🚀 Iniciando exportación de datos de MetaTrader 5")
    print(f"📊 Símbolo: {symbol}")
    print(f"⏰ Timeframe: {timeframe}")
    print(f"📈 Barras: {bars}")
    
    # Conectar a MT5
    print("\n📡 Conectando a MetaTrader 5...")
    mt5 = MT5Connector()
    
    if not mt5.connected:
        print("❌ No se pudo conectar a MT5. Verifica que MT5 esté abierto.")
        return None
    
    # Obtener datos
    print(f"\n📊 Obteniendo datos de {symbol}...")
    df = mt5.get_data(symbol, timeframe, bars, start_date, end_date)
    
    if df.empty:
        print("❌ No se pudieron obtener datos")
        mt5.disconnect()
        return None
    
    print(f"✅ Datos obtenidos: {len(df)} barras")
    print(f"   Rango: {df.index[0]} a {df.index[-1]}")
    print(f"   Precio actual: {df['close'].iloc[-1]:.5f}")
    
    # Crear directorio de salida si no existe
    symbol_dir = os.path.join(output_dir, symbol)
    os.makedirs(symbol_dir, exist_ok=True)
    
    # Generar nombre de archivo
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    timeframe_clean = timeframe.replace("m", "M").replace("h", "H").replace("d", "D")
    
    if start_date and end_date:
        filename = f"{symbol}_{timeframe_clean}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    else:
        filename = f"{symbol}_{timeframe_clean}_{current_time}.csv"
    
    filepath = os.path.join(symbol_dir, filename)
    
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
    
    return filepath

def export_multiple_symbols(symbols: list, timeframes: list, bars: int = 1000,
                           output_dir: str = "tests/test_data"):
    """
    Exporta datos de múltiples símbolos y timeframes
    
    Parámetros:
    symbols: list - Lista de símbolos
    timeframes: list - Lista de timeframes
    bars: int - Número de barras por exportación
    output_dir: str - Directorio de salida
    """
    
    print(f"🚀 Iniciando exportación masiva de datos")
    print(f"📊 Símbolos: {symbols}")
    print(f"⏰ Timeframes: {timeframes}")
    
    exported_files = []
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                filepath = export_data_to_csv(symbol, timeframe, bars, output_dir=output_dir)
                if filepath:
                    exported_files.append(filepath)
            except Exception as e:
                print(f"❌ Error exportando {symbol} {timeframe}: {e}")
    
    print(f"\n✅ Exportación completada")
    print(f"📁 Archivos generados: {len(exported_files)}")
    for filepath in exported_files:
        print(f"   - {filepath}")

def main():
    """Función principal del script"""
    
    parser = argparse.ArgumentParser(description="Exportar datos de MetaTrader 5 a CSV")
    parser.add_argument("--symbol", default="EURUSD", help="Símbolo a exportar")
    parser.add_argument("--timeframe", default="15m", help="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)")
    parser.add_argument("--bars", type=int, default=1000, help="Número de barras")
    parser.add_argument("--start-date", help="Fecha de inicio (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Fecha de fin (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default="tests/test_data", help="Directorio de salida")
    parser.add_argument("--batch", action="store_true", help="Exportar múltiples símbolos")
    
    args = parser.parse_args()
    
    # Procesar fechas si se proporcionan
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    if args.batch:
        # Exportación masiva
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        timeframes = ["15m", "1h", "4h"]
        export_multiple_symbols(symbols, timeframes, args.bars, args.output_dir)
    else:
        # Exportación individual
        filepath = export_data_to_csv(
            args.symbol, 
            args.timeframe, 
            args.bars, 
            start_date, 
            end_date, 
            args.output_dir
        )
        
        if filepath:
            print(f"\n🎉 ¡Exportación completada!")
            print(f"📁 Archivo generado: {filepath}")
            print(f"\n💡 Para usar en generate_gif_enhanced.py:")
            print(f"   csv_path = \"{filepath}\"")

if __name__ == "__main__":
    main() 