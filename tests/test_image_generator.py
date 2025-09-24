# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que el generador de imágenes funciona
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from image_generator_c import generate_smc_chart

def create_test_data():
    """Crear datos de prueba"""
    # Crear fechas
    start_date = datetime.now() - timedelta(days=100)
    dates = [start_date + timedelta(minutes=5*i) for i in range(100)]
    
    # Crear datos OHLCV de prueba
    np.random.seed(42)
    base_price = 1.1000
    
    data = []
    current_price = base_price
    
    for i in range(100):
        # Simular movimiento de precio
        change = np.random.normal(0, 0.001)
        current_price += change
        
        # Crear OHLC
        open_price = current_price
        high_price = open_price + abs(np.random.normal(0, 0.0005))
        low_price = open_price - abs(np.random.normal(0, 0.0005))
        close_price = open_price + np.random.normal(0, 0.0003)
        
        # Asegurar que high >= max(open, close) y low <= min(open, close)
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_image_generation():
    """Probar la generación de imágenes"""
    print("🧪 Creando datos de prueba...")
    
    # Crear datos de prueba
    window_df = create_test_data()
    print(f"📊 Datos creados: {window_df.shape}")
    print(f"📊 Columnas: {list(window_df.columns)}")
    
    # Crear indicadores de prueba
    macd_line = pd.Series(np.random.normal(0, 0.001, len(window_df)), index=window_df.index)
    signal_line = pd.Series(np.random.normal(0, 0.0005, len(window_df)), index=window_df.index)
    histogram = pd.Series(np.random.normal(0, 0.0002, len(window_df)), index=window_df.index)
    rsi = pd.Series(np.random.uniform(20, 80, len(window_df)), index=window_df.index)
    
    # Crear directorio de salida
    output_dir = "test_frames"
    os.makedirs(output_dir, exist_ok=True)
    
    # Nombre del archivo de salida
    output_filename = f"{output_dir}/test_chart.png"
    
    print(f"🎨 Generando gráfico de prueba...")
    print(f"📁 Archivo de salida: {output_filename}")
    
    try:
        # Llamar a la función de generación
        generate_smc_chart(
            window_df=window_df,
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=histogram,
            rsi=rsi,
            current_trend=1,
            current_trend_15m=1,
            current_trend_1h=1,
            current_trend_4h=1,
            fvg_data=None,
            swing_highs_lows_data=None,
            bos_choch_data=None,
            ob_data=None,
            liquidity_data=None,
            previous_high_low_data=None,
            sessions=None,
            retracements=None,
            output_filename=output_filename
        )
        
        # Verificar que el archivo se creó
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            print(f"✅ ¡Éxito! Archivo creado: {output_filename} ({file_size} bytes)")
            return True
        else:
            print(f"❌ Error: El archivo no se creó")
            return False
            
    except Exception as e:
        print(f"❌ Error durante la generación: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Iniciando prueba del generador de imágenes...")
    success = test_image_generation()
    
    if success:
        print("🎉 ¡Prueba exitosa! El generador de imágenes funciona correctamente.")
    else:
        print("💥 Prueba fallida. Revisar los errores arriba.")

