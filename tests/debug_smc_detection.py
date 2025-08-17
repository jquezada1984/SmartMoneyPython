#!/usr/bin/env python3
"""
Script de diagnóstico para investigar por qué la detección SMC no está funcionando
"""

import sys
import os
import pandas as pd
import numpy as np

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib
from estrategia.momentum_smc_strategy_lib import MomentumSMCStrategyLib

def load_test_data():
    """Cargar datos de prueba"""
    print("📂 Cargando datos de prueba...")
    
    try:
        # Cargar datos desde el archivo CSV
        file_path = "tests/test_data/EURUSD/EURUSD_5M_20250815_094446.csv"
        df = pd.read_csv(file_path)
        
        # Leer el CSV con datetime como índice
        df = pd.read_csv(file_path, index_col="datetime")
        
        # Convertir todas las columnas a float
        df = df.astype(float)
        
        # Asegurar que las columnas estén en el orden correcto
        df = df[["open", "high", "low", "close", "volume"]]
        
        # Convertir el índice a datetime
        df.index = pd.to_datetime(df.index)
        
        # MODIFICAR: Para 5M usar solo las últimas 300 velas como en smart01_optimized.py
        # Para 15M: 300 velas × 3 = 900 velas 5M
        # Para 1H: 300 velas × 12 = 3600 velas 5M  
        # Para 4H: 300 velas × 48 = 14400 velas 5M
        # Total requerido: 14400 velas 5M para cálculos de timeframes superiores
        
        total_required = 14400
        if len(df) >= total_required:
            df_full = df.tail(total_required)  # Para cálculos de timeframes superiores
            df_5m = df.tail(300)  # Solo 300 velas para análisis directo de 5M
            print(f"✅ Usando solo las últimas 300 velas para análisis directo de 5M")
            print(f"✅ Usando {total_required} velas para cálculos de timeframes superiores")
        else:
            print(f"⚠️ Datos insuficientes: {len(df)} velas disponibles")
            df_full = df
            df_5m = df.tail(min(300, len(df)))
        
        print(f"✅ Datos cargados: {len(df_5m)} registros para 5M directo")
        print(f"   Rango 5M: {df_5m.index[0]} a {df_5m.index[-1]}")
        print(f"   Columnas: {list(df_5m.columns)}")
        
        return df_5m, df_full
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None, None

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
    
    # MODIFICAR: Usar solo las últimas 300 velas como en smart01_optimized.py
    max_velas = 300
    if len(df_resampled) > max_velas:
        df_resampled = df_resampled.tail(max_velas)
        print(f"   📊 Usando solo las últimas {max_velas} velas de {timeframe}")
    
    return df_resampled

def debug_smc_detection(df, timeframe_name):
    """Diagnóstico detallado de la detección SMC"""
    print(f"\n🔍 DIAGNÓSTICO SMC DETALLADO - {timeframe_name}")
    print("=" * 60)
    
    # Inicializar librería
    market_analysis = MarketAnalysisLib()
    
    print(f"📊 Datos del timeframe:")
    print(f"   Registros: {len(df)}")
    print(f"   Rango: {df.index[0]} a {df.index[-1]}")
    print(f"   Precio actual: {df['close'].iloc[-1]:.5f}")
    
    # Mostrar últimos 10 precios para ver la tendencia visual
    print(f"\n📈 Últimos 10 precios de cierre:")
    last_10_prices = df['close'].tail(10)
    for i, (date, price) in enumerate(last_10_prices.items()):
        if i > 0:
            prev_price = last_10_prices.iloc[i-1]
            change = price - prev_price
            change_pct = (change / prev_price) * 100
            direction = "🟢 ↗️" if change > 0 else "🔴 ↘️" if change < 0 else "🟡 ➡️"
            print(f"   {date.strftime('%H:%M')}: {price:.5f} {direction} ({change:+.5f}, {change_pct:+.2f}%)")
        else:
            print(f"   {date.strftime('%H:%M')}: {price:.5f}")
    
    # Intentar detectar tendencia con método estructural
    print(f"\n🔄 Intentando detección SMC (estructural)...")
    try:
        trend_data = market_analysis.detect_trend(df, method='structural')
        print(f"✅ Tendencia SMC calculada exitosamente")
        
        # Mostrar estructura de datos retornada
        print(f"\n📋 Estructura de datos retornada:")
        print(f"   Columnas: {list(trend_data.columns)}")
        print(f"   Filas: {len(trend_data)}")
        print(f"   Tipos de datos:")
        for col in trend_data.columns:
            print(f"     {col}: {trend_data[col].dtype}")
        
        # Mostrar últimos 5 valores de cada columna
        print(f"\n📊 Últimos 5 valores de cada indicador:")
        last_5 = trend_data.tail(5)
        for col in trend_data.columns:
            print(f"\n   {col}:")
            for i, value in enumerate(last_5[col]):
                print(f"     [{i+1}]: {value}")
        
        # Verificar si hay valores NaN o infinitos
        print(f"\n🔍 Verificación de calidad de datos:")
        for col in trend_data.columns:
            nan_count = trend_data[col].isna().sum()
            inf_count = np.isinf(trend_data[col]).sum()
            print(f"   {col}: NaN={nan_count}, Inf={inf_count}")
        
        # Mostrar estadísticas básicas
        print(f"\n📈 Estadísticas básicas:")
        for col in trend_data.columns:
            if trend_data[col].dtype in ['float64', 'int64']:
                print(f"   {col}: min={trend_data[col].min():.4f}, max={trend_data[col].max():.4f}, mean={trend_data[col].mean():.4f}")
        
    except Exception as e:
        print(f"❌ Error en detección SMC: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return trend_data

def main():
    """Función principal"""
    print("🚀 DIAGNÓSTICO PROFUNDO DE DETECCIÓN SMC")
    print("=" * 60)
    
    # 1. Cargar datos
    df_5m, df_full = load_test_data()
    if df_5m is None:
        return
    
    # 2. Resamplear a diferentes timeframes
    print("\n🔄 Resampleando datos...")
    
    df_15m = resample_data(df_full, '15min')
    df_1h = resample_data(df_full, '1h')
    df_4h = resample_data(df_full, '4h')
    
    print(f"✅ 5M:  {len(df_5m)} registros (datos originales)")
    print(f"✅ 15M: {len(df_15m)} registros")
    print(f"✅ 1H:  {len(df_1h)} registros")
    print(f"✅ 4H:  {len(df_4h)} registros")
    
    # 3. Diagnóstico SMC para cada timeframe
    timeframes = [
        ("5M", df_5m),   # Agregar análisis directo de 5M
        ("15M", df_15m),
        ("1H", df_1h),
        ("4H", df_4h)
    ]
    
    for tf_name, df_tf in timeframes:
        debug_smc_detection(df_tf, tf_name)
    
    print("\n🎯 DIAGNÓSTICO COMPLETADO")
    print("=" * 60)
    print("Revisa los resultados para identificar por qué SMC no detecta tendencias")

if __name__ == "__main__":
    main()
