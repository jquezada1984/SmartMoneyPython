#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMART01 TEST IMAGE GENERATOR C - Versión de prueba usando image_generator_c.py
=============================================================================

Esta versión de smart01.py usa la nueva librería image_generator_c.py para generar
imágenes con indicadores SMC, manteniendo la misma lógica de análisis pero usando
la nueva implementación modular.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import sys
import os
from datetime import datetime
import numpy as np
import time
from io import BytesIO
from PIL import Image
import plotly.io as pio
from tqdm import tqdm
import datetime

# Importar paquetes asumiendo ejecución como módulo (python -m tests.smart01)
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib

# Importar la nueva librería image_generator_c
from image_generator_c import generate_smc_chart, add_FVG, add_swing_highs_lows, add_bos_choch, add_OB, add_liquidity, add_trend_analysis

def calculate_hybrid_trend(df, timeframe_name, market_analysis_lib):
    """
    Calcular tendencia usando Smart Money Concepts (SMC) desde market_analysis_lib
    Simplificado para devolver solo -1 (bajista), 0 (lateral), 1 (alcista)
    
    Parámetros:
    df: DataFrame del timeframe actual
    timeframe_name: Nombre del timeframe (ej: '15M', '1H', '4H')
    market_analysis_lib: Instancia de MarketAnalysisLib
    """
    try:
        # Usar la función detect_trend de market_analysis_lib con método 'structural'
        trend_result = market_analysis_lib.detect_trend(df, method='structural')
        
        # Obtener el valor de tendencia actual (última vela)
        current_trend = trend_result['trend'].iloc[-1]
        
        # Convertir a valores claros -1, 0, 1 según especificación del usuario
        if current_trend > 0.5:
            final_trend = 1  # ALCISTA
        elif current_trend < -0.5:
            final_trend = -1  # BAJISTA
        else:
            final_trend = 0  # LATERAL
        
        print(f"DEBUG {timeframe_name}: SMC detectó tendencia: {final_trend}")
        print(f"   📊 Analizando {len(df)} velas con método 'structural' (HH+HL, LL+LH, BOS, CHoCH)")
        
        # Crear DataFrame de tendencia simplificado
        trend_data = pd.DataFrame({
            'trend': [final_trend] * len(df)
        }, index=df.index)
        
        return trend_data
        
    except Exception as e:
        print(f"Error calculando tendencia SMC para {timeframe_name}: {e}")
        # Retornar tendencia neutral en caso de error
        neutral_trend = pd.DataFrame({
            'trend': [0] * len(df)
        }, index=df.index)
        return neutral_trend

def analyze_simple_price_trend(window_df):
    """
    Análisis simple de tendencia basado en precio cuando no hay estructura SMC clara
    """
    if len(window_df) < 10:
        return 0
    
    # Calcular cambio de precio en las últimas 10 velas
    recent_prices = window_df['close'].tail(10)
    price_change = recent_prices.iloc[-1] - recent_prices.iloc[0]
    price_change_pct = (price_change / recent_prices.iloc[0]) * 100
    
    # Calcular medias móviles simples
    ma_short = window_df['close'].rolling(window=5).mean()
    ma_long = window_df['close'].rolling(window=10).mean()
    
    # Determinar tendencia basada en precio y medias móviles
    if price_change_pct > 0.5 and ma_short.iloc[-1] > ma_long.iloc[-1]:
        return 1  # Alcista
    elif price_change_pct < -0.5 and ma_short.iloc[-1] < ma_long.iloc[-1]:
        return -1  # Bajista
    else:
        return 0  # Lateral

def generate_frame_with_image_generator_c(df_5m, df_15m, df_1h, df_4h, pos, window=100, frames_dir="frames_png"):
    """
    Generar frame usando image_generator_c.py en lugar de las funciones internas
    """
    print(f"🎬 Generando frame {pos} usando image_generator_c.py...")
    
    # Calcular la ventana de análisis
    analysis_start = max(0, pos - window)
    analysis_df = df_5m.iloc[analysis_start : pos]
    
    # Ventana de visualización (últimas 100 velas)
    window_df = df_5m.iloc[pos - window : pos]
    
    # Calcular tendencias usando SMC
    market_analysis = MarketAnalysisLib()
    
    # Tendencia 5M (visualización)
    trend_data = calculate_hybrid_trend(analysis_df, '5M', market_analysis)
    
    # Tendencia 15M
    df_15m_analysis = df_15m.iloc[:len(df_15m)//2]  # Usar primera mitad para análisis
    trend_data_15m = calculate_hybrid_trend(df_15m_analysis, '15M', market_analysis)
    
    # Tendencia 1H
    df_1h_analysis = df_1h.iloc[:len(df_1h)//2]  # Usar primera mitad para análisis
    trend_data_1h = calculate_hybrid_trend(df_1h_analysis, '1H', market_analysis)
    
    # Tendencia 4H
    df_4h_analysis = df_4h.iloc[:len(df_4h)//2]  # Usar primera mitad para análisis
    trend_data_4h = calculate_hybrid_trend(df_4h_analysis, '4H', market_analysis)
    
    # Determinar tipos de tendencia
    current_trend_5m = trend_data['trend'].iloc[-1] if len(trend_data) > 0 else 0
    current_trend_15m = trend_data_15m['trend'].iloc[-1] if len(trend_data_15m) > 0 else 0
    current_trend_1h = trend_data_1h['trend'].iloc[-1] if len(trend_data_1h) > 0 else 0
    current_trend_4h = trend_data_4h['trend'].iloc[-1] if len(trend_data_4h) > 0 else 0
    
    # Convertir a tipos de tendencia
    trend_type_5m = "ALCISTA" if current_trend_5m > 0.3 else "BAJISTA" if current_trend_5m < -0.3 else "LATERAL"
    trend_type_15m = "ALCISTA" if current_trend_15m > 0.3 else "BAJISTA" if current_trend_15m < -0.3 else "LATERAL"
    trend_type_1h = "ALCISTA" if current_trend_1h > 0.3 else "BAJISTA" if current_trend_1h < -0.3 else "LATERAL"
    trend_type_4h = "ALCISTA" if current_trend_4h > 0.3 else "BAJISTA" if current_trend_4h < -0.3 else "LATERAL"
    
    # Crear datos SMC simulados para la prueba
    smc_data = {
        'order_blocks': pd.DataFrame({
            'OB': [1] * 5,
            'Type': ['Bullish', 'Bearish', 'Bullish', 'Bearish', 'Bullish'],
            'Level': [1.0850, 1.0800, 1.0900, 1.0750, 1.0950]
        }),
        'fvg_data': pd.DataFrame({
            'FVG': [1] * 3,
            'Top': [1.0880, 1.0820, 1.0920],
            'Bottom': [1.0860, 1.0800, 1.0900],
            'MitigatedIndex': [10, 15, 20]
        }),
        'swing_data': pd.DataFrame({
            'HighLow': [1, -1, 1, -1, 1],
            'Level': [1.0900, 1.0780, 1.0920, 1.0760, 1.0940]
        }),
        'bos_choch_data': pd.DataFrame({
            'BOS': [1, 0, 1, 0, 1],
            'CHOCH': [0, 1, 0, 1, 0],
            'Level': [1.0880, 1.0800, 1.0900, 1.0780, 1.0920],
            'BrokenIndex': [12, 0, 18, 0, 25],
            'ChoCHIndex': [0, 16, 0, 22, 0]
        }),
        'trends': {
            'h1_trend': trend_type_1h,
            'h4_trend': trend_type_4h,
            'overall_bias': 'ALCISTA' if current_trend_1h > 0 and current_trend_4h > 0 else 'BAJISTA' if current_trend_1h < 0 and current_trend_4h < 0 else 'LATERAL'
        }
    }
    
    # Crear nombre de archivo único
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart01_test_{timestamp}_frame_{pos:04d}.png"
    save_path = os.path.join(frames_dir, filename)
    
    # Generar título del gráfico
    title = f"EURUSD - Frame {pos} - SMC Test con image_generator_c.py"
    
    try:
        # Usar generate_smc_chart de image_generator_c.py
        fig = generate_smc_chart(
            df=window_df,
            smc_data=smc_data,
            icc_signals=None,  # No hay señales ICC en este test
            signal_type="SMC_TEST",
            title=title,
            width=1200,
            height=800,
            save_path=save_path
        )
        
        print(f"✅ Frame {pos} generado exitosamente usando image_generator_c.py: {filename}")
        print(f"   📊 Tendencias detectadas:")
        print(f"      • 5M: {trend_type_5m} ({current_trend_5m:.2f})")
        print(f"      • 15M: {trend_type_15m} ({current_trend_15m:.2f})")
        print(f"      • 1H: {trend_type_1h} ({current_trend_1h:.2f})")
        print(f"      • 4H: {trend_type_4h} ({current_trend_4h:.2f})")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error generando frame {pos} con image_generator_c.py: {e}")
        return None

def main():
    """Función principal para probar image_generator_c.py"""
    print("🚀 SMART01 TEST IMAGE GENERATOR C - Probando la nueva librería")
    print("=" * 70)
    
    # Verificar que image_generator_c.py esté disponible
    try:
        from image_generator_c import generate_smc_chart
        print("✅ image_generator_c.py importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando image_generator_c.py: {e}")
        return
    
    # Crear directorio de frames si no existe
    frames_dir = "frames_png"
    os.makedirs(frames_dir, exist_ok=True)
    
    # Cargar datos de ejemplo (usar datos reales si están disponibles)
    print("📊 Cargando datos de ejemplo...")
    
    # Crear datos simulados para la prueba
    dates = pd.date_range('2025-01-01', periods=1000, freq='5T')
    np.random.seed(42)
    
    # Generar datos OHLCV simulados
    base_price = 1.0850
    prices = []
    for i in range(1000):
        if i == 0:
            price = base_price
        else:
            change = np.random.normal(0, 0.0005)
            price = prices[-1] + change
        prices.append(price)
    
    df_5m = pd.DataFrame({
        'open': prices,
        'high': [p + abs(np.random.normal(0, 0.0002)) for p in prices],
        'low': [p - abs(np.random.normal(0, 0.0002)) for p in prices],
        'close': prices,
        'volume': np.random.randint(100, 1000, 1000)
    }, index=dates)
    
    # Ajustar high y low para que sean consistentes
    df_5m['high'] = df_5m[['open', 'high', 'close']].max(axis=1)
    df_5m['low'] = df_5m[['open', 'low', 'close']].min(axis=1)
    
    # Crear timeframes superiores
    df_15m = df_5m.resample('15T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_1h = df_5m.resample('1H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_4h = df_5m.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    print(f"✅ Datos simulados generados:")
    print(f"   📊 5M: {len(df_5m)} velas")
    print(f"   📊 15M: {len(df_15m)} velas")
    print(f"   📊 1H: {len(df_1h)} velas")
    print(f"   📊 4H: {len(df_4h)} velas")
    
    # Generar algunos frames de prueba
    print(f"\n🎬 Generando frames de prueba...")
    test_positions = [200, 400, 600, 800]
    
    for pos in test_positions:
        if pos < len(df_5m):
            generate_frame_with_image_generator_c(df_5m, df_15m, df_1h, df_4h, pos, window=100, frames_dir=frames_dir)
        else:
            print(f"⚠️ Posición {pos} fuera de rango, saltando...")
    
    print(f"\n🏁 Prueba completada!")
    print(f"   📁 Frames guardados en: {frames_dir}/")
    print(f"   🔍 Verifica las imágenes generadas para confirmar que image_generator_c.py funciona correctamente")

if __name__ == "__main__":
    main()
