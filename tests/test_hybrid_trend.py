#!/usr/bin/env python3
"""
Script de prueba para verificar la función de tendencia híbrida
"""

import sys
import os
import pandas as pd
import numpy as np

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_test_data():
    """Cargar datos de prueba"""
    csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: No se encontró el archivo {csv_path}")
        return None
    
    print(f"📊 Cargando datos desde: {csv_path}")
    
    # Leer el CSV
    df = pd.read_csv(csv_path, index_col="datetime")
    
    # Convertir todas las columnas a float
    df = df.astype(float)
    
    # Asegurar que las columnas estén en el orden correcto
    df = df[["open", "high", "low", "close", "volume"]]
    
    # Convertir el índice a datetime
    df.index = pd.to_datetime(df.index)
    
    print(f"✅ Datos cargados: {len(df)} registros")
    print(f"   Rango: {df.index[0]} a {df.index[-1]}")
    
    return df

def resample_data(df, timeframe):
    """Resamplear datos a un timeframe específico"""
    if timeframe == '15min':
        rule = '15min'
    elif timeframe == '1h':
        rule = '1h'
    elif timeframe == '4h':
        rule = '4h'
    else:
        raise ValueError(f"Timeframe no válido: {timeframe}")
    
    # Crear copia temporal para resamplear
    df_temp = df.copy()
    
    # Resamplear OHLCV
    df_resampled = df_temp.resample(rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # Eliminar filas con NaN
    df_resampled = df_resampled.dropna()
    
    return df_resampled

def test_hybrid_trend():
    """Probar la función de tendencia híbrida"""
    print("🚀 PRUEBA DE FUNCIÓN DE TENDENCIA HÍBRIDA")
    print("=" * 60)
    
    # 1. Cargar datos
    df_5m = load_test_data()
    if df_5m is None:
        return
    
    # 2. Resamplear a diferentes timeframes
    print("\n🔄 Resampleando datos...")
    
    df_15m = resample_data(df_5m, '15min')
    df_1h = resample_data(df_5m, '1h')
    df_4h = resample_data(df_5m, '4h')
    
    print(f"✅ 15M: {len(df_15m)} registros")
    print(f"✅ 1H: {len(df_1h)} registros")
    print(f"✅ 4H: {len(df_4h)} registros")
    
    # 3. Probar función híbrida
    print("\n🔍 Probando función de tendencia híbrida...")
    
    try:
        # Importar la función desde smart01.py
        from tests.smart01 import calculate_hybrid_trend
        print("✅ Función importada correctamente")
        
        # Probar con cada timeframe
        timeframes = [
            ("15M", df_15m),
            ("1H", df_1h),
            ("4H", df_4h)
        ]
        
        for tf_name, df_tf in timeframes:
            print(f"\n📊 Probando {tf_name}:")
            print("-" * 40)
            
            # Mostrar últimos 5 precios
            last_5_prices = df_tf['close'].tail(5)
            print(f"Últimos 5 precios: {[f'{p:.5f}' for p in last_5_prices.values]}")
            
            # Calcular tendencia híbrida
            hybrid_trend = calculate_hybrid_trend(df_tf, tf_name)
            
            # Mostrar resultados
            if hybrid_trend is not None:
                current_trend = hybrid_trend['trend'].iloc[-1]
                current_strength = hybrid_trend['strength'].iloc[-1]
                current_confidence = hybrid_trend['confidence'].iloc[-1]
                
                trend_text = "🟢 ALCISTA" if current_trend == 1 else "🔴 BAJISTA" if current_trend == -1 else "🟡 LATERAL"
                
                print(f"   Tendencia: {trend_text}")
                print(f"   Fuerza: {current_strength:.1f}/100")
                print(f"   Confianza: {current_confidence:.1f}/100")
            else:
                print("   ❌ Error: No se pudo calcular la tendencia")
        
        print("\n✅ Prueba completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_trend()
