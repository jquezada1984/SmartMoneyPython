#!/usr/bin/env python3
"""
Script de prueba para verificar la detección de Order Blocks en la estrategia ICC usando datos reales
"""

import sys
import os
import pandas as pd
import numpy as np

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estrategia.icc import ICCStrategy

def test_with_real_data():
    """Prueba con datos reales del CSV"""
    print("🧪 PRUEBA CON DATOS REALES")
    print("=" * 50)
    
    # Cargar datos reales
    csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ Archivo no encontrado: {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path, index_col="datetime")
        df = df.astype(float)    
        df = df[["open", "high", "low", "close", "volume"]]    
        df.index = pd.to_datetime(df.index)
        
        # Tomar solo las últimas 500 velas para la prueba
        df = df.tail(500)
        
        print(f"📊 Datos reales cargados: {len(df)} velas")
        print(f"   📈 Rango de precios: {df['low'].min():.5f} - {df['high'].max():.5f}")
        print(f"   📊 Rango de fechas: {df.index[0]} a {df.index[-1]}")
        print(f"   📊 Columnas: {df.columns.tolist()}")
        
        # Verificar que no hay NaN en los datos
        nan_counts = df.isna().sum()
        print(f"   🔍 NaN counts: {nan_counts.to_dict()}")
        
        # Inicializar estrategia ICC
        icc_strategy = ICCStrategy(
            risk_reward_min=3.0,
            ob_lookback=50,
            fvg_lookback=30,
            swing_length=20
        )
        
        print(f"\n🔍 PROBANDO DETECCIÓN DE ORDER BLOCKS CON DATOS REALES...")
        
        # Probar detección de Order Blocks
        ob_data = icc_strategy.identify_order_blocks(df)
        
        print(f"\n📊 RESULTADO DE LA PRUEBA OB:")
        if not ob_data.empty:
            print(f"   ✅ Order Blocks detectados: {len(ob_data)}")
            print(f"   📈 OB Alcistas: {len(ob_data[ob_data['OB'] == 1])}")
            print(f"   📉 OB Bajistas: {len(ob_data[ob_data['OB'] == -1])}")
            print(f"   ⚪ OB Neutrales: {len(ob_data[ob_data['OB'] == 0])}")
            
            # Mostrar algunos ejemplos
            if len(ob_data[ob_data['OB'] == 1]) > 0:
                bullish_example = ob_data[ob_data['OB'] == 1].iloc[0]
                print(f"   📈 Ejemplo OB Alcista: {bullish_example.name}")
            
            if len(ob_data[ob_data['OB'] == -1]) > 0:
                bearish_example = ob_data[ob_data['OB'] == -1].iloc[0]
                print(f"   📉 Ejemplo OB Bajista: {bearish_example.name}")
        else:
            print(f"   ⚠️ No se detectaron Order Blocks")
        
        print(f"\n🔍 PROBANDO DETECCIÓN DE FVG CON DATOS REALES...")
        
        # Probar detección de FVG
        fvg_data = icc_strategy.identify_fair_value_gaps(df)
        
        print(f"\n📊 RESULTADO DE LA PRUEBA FVG:")
        if not fvg_data.empty:
            print(f"   ✅ Fair Value Gaps detectados: {len(fvg_data)}")
            print(f"   📈 FVG Alcistas: {len(fvg_data[fvg_data['FVG'] == 1])}")
            print(f"   📉 FVG Bajistas: {len(fvg_data[fvg_data['FVG'] == -1])}")
            print(f"   ⚪ Sin FVG: {len(fvg_data[fvg_data['FVG'].isna()])}")
        else:
            print(f"   ⚠️ No se detectaron Fair Value Gaps")
        
        print(f"\n✅ PRUEBA COMPLETADA")
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_real_data()
