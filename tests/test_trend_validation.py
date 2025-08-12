#!/usr/bin/env python3
"""
Script de prueba para validar las funciones de tendencia
Valida que se puedan calcular tendencias en 15M, 1H y 4H desde datos de 5M
"""

import pandas as pd
import numpy as np
import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib
from estrategia.momentum_smc_strategy_lib import MomentumSMCStrategyLib

def load_test_data():
    """Cargar datos de prueba desde el CSV"""
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
    print(f"   Columnas: {list(df.columns)}")
    
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

def debug_resampled_data(df_5m, df_15m, df_1h, df_4h):
    """Función de diagnóstico para verificar datos resampleados"""
    print("\n🔍 DIAGNÓSTICO DE DATOS RESAMPLEADOS")
    print("=" * 60)
    
    # Mostrar información básica de cada timeframe
    timeframes_info = [
        ("5M (Original)", df_5m),
        ("15M", df_15m),
        ("1H", df_1h),
        ("4H", df_4h)
    ]
    
    for tf_name, df_tf in timeframes_info:
        print(f"\n📊 {tf_name}:")
        print(f"   Registros: {len(df_tf)}")
        print(f"   Rango: {df_tf.index[0]} a {df_tf.index[-1]}")
        print(f"   Precio actual: {df_tf['close'].iloc[-1]:.5f}")
        print(f"   Precio anterior: {df_tf['close'].iloc[-2]:.5f}")
        
        # Calcular cambio de precio
        if len(df_tf) > 1:
            price_change = df_tf['close'].iloc[-1] - df_tf['close'].iloc[-2]
            price_change_pct = (price_change / df_tf['close'].iloc[-2]) * 100
            print(f"   Cambio: {price_change:+.5f} ({price_change_pct:+.2f}%)")
            
            # Determinar dirección visual
            if price_change > 0:
                direction = "🟢 ↗️ (ALCISTA)"
            elif price_change < 0:
                direction = "🔴 ↘️ (BAJISTA)"
            else:
                direction = "🟡 ➡️ (LATERAL)"
            print(f"   Dirección visual: {direction}")
    
    # Mostrar últimos 5 registros de cada timeframe para comparar
    print(f"\n📋 ÚLTIMOS 5 REGISTROS COMPARADOS:")
    print("=" * 80)
    
    for tf_name, df_tf in timeframes_info:
        print(f"\n{tf_name}:")
        print(f"{'Fecha':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Vol':<8}")
        print("-" * 70)
        
        last_5 = df_tf.tail(5)
        for date, row in last_5.iterrows():
            print(f"{date.strftime('%Y-%m-%d %H:%M'):<20} "
                  f"{row['open']:<10.5f} {row['high']:<10.5f} "
                  f"{row['low']:<10.5f} {row['close']:<10.5f} "
                  f"{row['volume']:<8.0f}")

def analyze_trends(df_5m, df_15m, df_1h, df_4h):
    """Analizar tendencias SMC en todos los timeframes"""
    print("\n🔍 ANALIZANDO TENDENCIAS SMC EN DIFERENTES TIMEFRAMES")
    print("=" * 60)
    
    # Inicializar librerías
    print("⚙️ Inicializando librerías de análisis SMC...")
    market_analysis = MarketAnalysisLib()
    strategy_lib = MomentumSMCStrategyLib()
    print("✅ Librerías SMC inicializadas")
    
    # Calcular tendencias solo para timeframes superiores (15M, 1H, 4H)
    timeframes = [
        ("15M", df_15m),
        ("1H", df_1h),
        ("4H", df_4h)
    ]
    
    trend_results = {}
    
    print(f"\n🚀 Comenzando análisis SMC de {len(timeframes)} timeframes...")
    
    for i, (tf_name, df_tf) in enumerate(timeframes, 1):
        print(f"\n📊 [{i}/{len(timeframes)}] Analizando SMC en {tf_name} - {len(df_tf)} registros")
        print("-" * 50)
        
        try:
            print(f"   🔄 Calculando tendencia usando método SMC (estructural)...")
            # Calcular tendencia usando SOLO método SMC (estructural)
            trend_data = market_analysis.detect_trend(df_tf, method='structural')
            print(f"   ✅ Tendencia SMC calculada exitosamente")
            
            # Obtener valores actuales
            current_trend = trend_data['trend'].iloc[-1]
            current_strength = trend_data['strength'].iloc[-1]
            current_confidence = trend_data['confidence'].iloc[-1]
            
            # Interpretar tendencia
            if current_trend == 1:
                trend_text = "🟢 ALCISTA (SMC)"
            elif current_trend == -1:
                trend_text = "🔴 BAJISTA (SMC)"
            else:
                trend_text = "🟡 LATERAL (SMC)"
            
            print(f"   📈 Resultados SMC obtenidos:")
            print(f"      Tendencia: {trend_text}")
            print(f"      Fuerza: {current_strength:.1f}/100")
            print(f"      Confianza: {current_confidence:.1f}/100")
            
            # Mostrar últimos 5 valores de tendencia
            print(f"   🔍 Analizando últimos 5 valores SMC...")
            last_trends = trend_data['trend'].tail(5)
            trend_changes = []
            for i, trend in enumerate(last_trends):
                if trend == 1:
                    trend_changes.append("↗️")
                elif trend == -1:
                    trend_changes.append("↘️")
                else:
                    trend_changes.append("➡️")
            
            print(f"      Últimos 5 valores: {' '.join(trend_changes)}")
            
            # Guardar resultados
            trend_results[tf_name] = {
                'trend': current_trend,
                'strength': current_strength,
                'confidence': current_confidence,
                'data': trend_data,
                'method': 'SMC (estructural)'
            }
            
            print(f"   💾 Resultados SMC guardados para {tf_name}")
            
        except Exception as e:
            print(f"   ❌ Error calculando tendencia SMC para {tf_name}: {e}")
            trend_results[tf_name] = None
    
    print(f"\n✅ Análisis de tendencias SMC completado para todos los timeframes")
    return trend_results

def validate_trend_consistency(trend_results):
    """Validar consistencia entre timeframes"""
    print("\n🔍 VALIDACIÓN DE CONSISTENCIA ENTRE TIMEFRAMES")
    print("=" * 60)
    
    if not trend_results:
        print("❌ No hay resultados de tendencia para validar")
        return
    
    # Verificar si hay tendencias claras
    clear_trends = {}
    for tf_name, result in trend_results.items():
        if result and result['confidence'] > 50:
            clear_trends[tf_name] = result['trend']
    
    if not clear_trends:
        print("⚠️ No se detectaron tendencias claras (confianza > 50%)")
        return
    
    print(f"✅ Tendencias claras detectadas:")
    for tf_name, trend in clear_trends.items():
        trend_text = "ALCISTA" if trend == 1 else "BAJISTA"
        print(f"   {tf_name}: {trend_text}")
    
    # Verificar consistencia
    trends = list(clear_trends.values())
    if len(set(trends)) == 1:
        trend_value = trends[0]
        if trend_value == 1:
            print(f"\n🎯 CONSISTENCIA SMC PERFECTA: Todos los timeframes muestran tendencia ALCISTA")
        elif trend_value == -1:
            print(f"\n🎯 CONSISTENCIA SMC PERFECTA: Todos los timeframes muestran tendencia BAJISTA")
        else:
            print(f"\n🎯 CONSISTENCIA SMC PERFECTA: Todos los timeframes muestran tendencia LATERAL")
    else:
        print(f"\n⚠️ INCONSISTENCIA SMC: Diferentes timeframes muestran tendencias opuestas")
        for tf_name, trend in clear_trends.items():
            trend_text = "ALCISTA" if trend == 1 else "BAJISTA"
            print(f"   {tf_name}: {trend_text}")

def show_detailed_analysis(trend_results):
    """Mostrar análisis detallado de las tendencias en timeframes superiores"""
    print("\n📈 ANÁLISIS DETALLADO DE TENDENCIAS EN TIMEFRAMES SUPERIORES")
    print("=" * 60)
    
    # Mostrar evolución de la tendencia en cada timeframe
    for tf_name in ['15M', '1H', '4H']:
        if tf_name not in trend_results or not trend_results[tf_name]:
            continue
            
        print(f"\n📊 {tf_name} - Últimas 10 tendencias:")
        print("-" * 40)
        
        trend_data = trend_results[tf_name]['data']
        last_10_trends = trend_data.tail(10)
        
        for i, trend_row in enumerate(last_10_trends.itertuples()):
            trend_value = trend_row.trend
            strength = trend_row.strength
            confidence = trend_row.confidence
            
            if trend_value == 1:
                trend_symbol = "🟢 ↗️"
            elif trend_value == -1:
                trend_symbol = "🔴 ↘️"
            else:
                trend_symbol = "🟡 ➡️"
            
            print(f"   {i+1:2d}: {trend_symbol} F:{strength:.0f} C:{confidence:.0f}")

def main():
    """Función principal"""
    print("🚀 VALIDACIÓN DE FUNCIONES DE TENDENCIA SMC")
    print("=" * 60)
    
    # 1. Cargar datos
    print("\n📂 PASO 1/6: Cargando datos de prueba...")
    df_5m = load_test_data()
    if df_5m is None:
        return
    print("✅ Datos cargados exitosamente")
    
    # 2. Resamplear a diferentes timeframes
    print("\n🔄 PASO 2/6: Resampleando datos a diferentes timeframes...")
    
    try:
        print("   🔄 Resampleando a 15 minutos...")
        df_15m = resample_data(df_5m, '15min')
        print(f"   ✅ 15M: {len(df_15m)} registros")
        
        print("   🔄 Resampleando a 1 hora...")
        df_1h = resample_data(df_5m, '1h')
        print(f"   ✅ 1H: {len(df_1h)} registros")
        
        print("   🔄 Resampleando a 4 horas...")
        df_4h = resample_data(df_5m, '4h')
        print(f"   ✅ 4H: {len(df_4h)} registros")
        
        print("✅ Resampleo completado para todos los timeframes")
        
    except Exception as e:
        print(f"❌ Error resampleando datos: {e}")
        return
    
    # 2.5. Diagnóstico de datos resampleados
    print("\n🔍 PASO 2.5/5: Diagnóstico de datos resampleados...")
    debug_resampled_data(df_5m, df_15m, df_1h, df_4h)
    
    # 3. Analizar tendencias
    print("\n🔍 PASO 3/6: Analizando tendencias...")
    trend_results = analyze_trends(df_5m, df_15m, df_1h, df_4h)
    
    # 4. Validar consistencia
    print("\n🔍 PASO 4/6: Validando consistencia entre timeframes...")
    validate_trend_consistency(trend_results)
    
    # 5. Mostrar análisis detallado
    print("\n📊 PASO 5/6: Generando análisis detallado...")
    show_detailed_analysis(trend_results)
    
    print("\n🎉 ¡VALIDACIÓN SMC COMPLETADA EXITOSAMENTE!")
    print("=" * 60)
    print(f"📁 Los datos están listos para usar en smart01.py")
    print(f"🔍 Se analizaron tendencias SMC en: 15M, 1H y 4H")
    print(f"📊 Total de registros procesados: {len(df_5m)} (5M) → {len(df_15m)} (15M) → {len(df_1h)} (1H) → {len(df_4h)} (4H)")
    print(f"🎯 Método de análisis: SMC (estructural) - Solo Smart Money Concepts")

if __name__ == "__main__":
    main()
