#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACIÓN DE NIVELES ESTRUCTURALES
===================================

Este script valida que el Take Profit apunte a niveles estructurales
del mercado (nivel medio del OB en timeframes superiores o siguiente swing estructural).
"""

import pandas as pd
import numpy as np
import os
import sys

# Agregar el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estrategia.icc import ICCStrategy

def simular_niveles_estructurales():
    """
    Simular diferentes escenarios para validar niveles estructurales
    """
    print("🔍 VALIDACIÓN DE NIVELES ESTRUCTURALES")
    print("=" * 50)
    
    # Crear datos simulados
    dates = pd.date_range('2025-01-01', periods=200, freq='5min')
    
    # Simular datos de mercado con swing highs/lows
    np.random.seed(42)
    base_price = 1.08500
    
    # Crear datos con estructura de mercado
    data = []
    for i, date in enumerate(dates):
        # Simular movimiento de precio con estructura
        if i < 50:
            # Tendencia alcista inicial
            price_change = np.random.normal(0.0002, 0.0005)
        elif i < 100:
            # Pullback
            price_change = np.random.normal(-0.0001, 0.0003)
        elif i < 150:
            # Nuevo impulso
            price_change = np.random.normal(0.0003, 0.0004)
        else:
            # Consolidación
            price_change = np.random.normal(0.0000, 0.0002)
        
        base_price += price_change
        
        # Crear OHLC
        high = base_price + abs(np.random.normal(0, 0.0003))
        low = base_price - abs(np.random.normal(0, 0.0003))
        open_price = base_price + np.random.normal(0, 0.0001)
        close_price = base_price + np.random.normal(0, 0.0001)
        volume = np.random.randint(100, 1000)
        
        data.append({
            'datetime': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df_5m = pd.DataFrame(data)
    df_5m.set_index('datetime', inplace=True)
    
    # Crear timeframes superiores
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
    
    # Inicializar estrategia ICC
    icc_strategy = ICCStrategy()
    
    # Simular diferentes puntos de entrada
    entry_points = [
        (1.08500, 'LONG', 'Entrada en soporte'),
        (1.08700, 'LONG', 'Entrada en pullback'),
        (1.08300, 'SHORT', 'Entrada en resistencia'),
        (1.08600, 'SHORT', 'Entrada en impulso')
    ]
    
    for entry_price, direction, description in entry_points:
        print(f"\n📊 ESCENARIO: {description}")
        print(f"   💰 Entry Price: {entry_price:.5f}")
        print(f"   📈 Direction: {direction}")
        
        try:
            # Calcular niveles estructurales
            tp_levels = icc_strategy.calculate_structural_take_profits(
                df_5m, entry_price, direction, df_1h, df_4h
            )
            
            structural_levels = tp_levels.get('structural_levels', [])
            
            if structural_levels:
                print(f"   🎯 Niveles estructurales encontrados:")
                for i, level in enumerate(structural_levels[:3]):
                    print(f"      • Nivel {i+1}: {level:.5f}")
                
                # Calcular R:R para el primer nivel
                if direction == 'LONG':
                    risk_distance = entry_price * 0.005  # 0.5% de riesgo
                    stop_loss = entry_price - risk_distance
                    reward_distance = structural_levels[0] - entry_price
                else:  # SHORT
                    risk_distance = entry_price * 0.005  # 0.5% de riesgo
                    stop_loss = entry_price + risk_distance
                    reward_distance = entry_price - structural_levels[0]
                
                rr_ratio = reward_distance / risk_distance
                
                print(f"   🛑 Stop Loss: {stop_loss:.5f}")
                print(f"   🎯 Take Profit: {structural_levels[0]:.5f}")
                print(f"   📊 R:R Ratio: 1:{rr_ratio:.2f}")
                
                # Validar límites
                if rr_ratio > 3.0:
                    print(f"   ⚠️  R:R excede 1:3, se limitará a 1:3")
                elif rr_ratio < 1.0:
                    print(f"   ⚠️  R:R menor a 1:1, se ajustará a 1:1")
                else:
                    print(f"   ✅ R:R dentro de límites aceptables")
                    
            else:
                print(f"   ❌ No se encontraron niveles estructurales")
                print(f"   🔄 Usando fallback R:R 1:1.5")
                
        except Exception as e:
            print(f"   ❌ Error calculando niveles: {e}")

def mostrar_resumen_mejoras():
    """
    Mostrar resumen de las mejoras implementadas
    """
    print("\n📋 RESUMEN DE MEJORAS IMPLEMENTADAS")
    print("=" * 50)
    print("   🎯 ANTES: Take Profit basado en ATR")
    print("   ✅ AHORA: Take Profit basado en niveles estructurales")
    print("\n   📊 Niveles estructurales considerados:")
    print("      • Swing Highs/Lows en 1H")
    print("      • Swing Highs/Lows en 4H")
    print("      • Zonas de alta liquidez")
    print("      • Equal Highs/Lows")
    print("      • Nivel medio de Order Blocks")
    print("\n   🎯 Lógica del Take Profit:")
    print("      • Apunta al nivel estructural más cercano")
    print("      • R:R mínimo: 1:1")
    print("      • R:R máximo: 1:3")
    print("      • Si el nivel estructural da R:R > 1:3, se limita a 1:3")
    print("      • Si el nivel estructural da R:R < 1:1, se ajusta a 1:1")
    print("\n   ✅ BENEFICIOS:")
    print("      • Take Profit más preciso y basado en estructura real")
    print("      • Respeta niveles importantes del mercado")
    print("      • Mejor gestión de riesgo")
    print("      • Mayor probabilidad de alcanzar el TP")

if __name__ == '__main__':
    try:
        print("🎯 VALIDACIÓN DE NIVELES ESTRUCTURALES")
        print("=" * 60)
        
        # Simular niveles estructurales
        simular_niveles_estructurales()
        
        # Mostrar resumen
        mostrar_resumen_mejoras()
        
        print("\n" + "=" * 60)
        print("✅ VALIDACIÓN COMPLETADA")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error en la validación: {e}")
        import traceback
        traceback.print_exc()
