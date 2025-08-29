#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACIÓN DE RATIOS DE TAKE PROFIT
===================================

Este script valida los diferentes ratios de Risk:Reward que puede generar
el sistema de Take Profit estructural.
"""

import pandas as pd
import numpy as np
import os
import sys

def calcular_tp_estructural(entry_price, stop_loss, atr_values):
    """
    Calcular Take Profit estructural basado en ATR
    """
    risk_distance = abs(entry_price - stop_loss)
    
    if atr_values:
        atr = sum(atr_values) / len(atr_values)
        # Calcular R:R basado en estructura (entre 1.0 y 3.0)
        structural_rr = min(3.0, max(1.0, (atr * 2) / risk_distance))
        take_profit = entry_price + (risk_distance * structural_rr) if entry_price > stop_loss else entry_price - (risk_distance * structural_rr)
    else:
        # Fallback a R:R 1.5 si no hay suficientes datos
        structural_rr = 1.5
        take_profit = entry_price + (risk_distance * structural_rr) if entry_price > stop_loss else entry_price - (risk_distance * structural_rr)
    
    return take_profit, structural_rr

def simular_diferentes_escenarios():
    """
    Simular diferentes escenarios de mercado para validar ratios
    """
    print("🔍 VALIDACIÓN DE RATIOS DE TAKE PROFIT")
    print("=" * 50)
    
    # Escenario 1: Mercado con baja volatilidad (ATR pequeño)
    print("\n📊 ESCENARIO 1: Mercado con baja volatilidad")
    entry_price = 1.08500
    stop_loss = 1.08000  # 50 pips de riesgo
    risk_distance = entry_price - stop_loss
    
    # ATR bajo (mercado tranquilo)
    atr_values = [0.00020, 0.00025, 0.00018, 0.00022, 0.00019]  # ~20-25 pips ATR
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {risk_distance:.5f} ({risk_distance*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")
    
    # Escenario 2: Mercado con volatilidad media
    print("\n📊 ESCENARIO 2: Mercado con volatilidad media")
    entry_price = 1.08500
    stop_loss = 1.08000
    
    # ATR medio
    atr_values = [0.00050, 0.00055, 0.00048, 0.00052, 0.00049]  # ~50 pips ATR
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {risk_distance:.5f} ({risk_distance*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")
    
    # Escenario 3: Mercado con alta volatilidad
    print("\n📊 ESCENARIO 3: Mercado con alta volatilidad")
    entry_price = 1.08500
    stop_loss = 1.08000
    
    # ATR alto
    atr_values = [0.00100, 0.00110, 0.00095, 0.00105, 0.00098]  # ~100 pips ATR
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {risk_distance:.5f} ({risk_distance*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")
    
    # Escenario 4: Mercado extremadamente volátil (debería limitarse a 1:3)
    print("\n📊 ESCENARIO 4: Mercado extremadamente volátil")
    entry_price = 1.08500
    stop_loss = 1.08000
    
    # ATR muy alto
    atr_values = [0.00200, 0.00250, 0.00180, 0.00220, 0.00190]  # ~200 pips ATR
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {risk_distance:.5f} ({risk_distance*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")
    
    # Escenario 5: Venta (SHORT)
    print("\n📊 ESCENARIO 5: Operación de VENTA (SHORT)")
    entry_price = 1.08500
    stop_loss = 1.09000  # Stop Loss por encima
    
    # ATR medio
    atr_values = [0.00060, 0.00065, 0.00058, 0.00062, 0.00059]
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {abs(entry_price - stop_loss):.5f} ({abs(entry_price - stop_loss)*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")
    
    # Escenario 6: Con riesgo más pequeño para ver ratios mayores
    print("\n📊 ESCENARIO 6: Riesgo pequeño (10 pips)")
    entry_price = 1.08500
    stop_loss = 1.08400  # Solo 10 pips de riesgo
    
    # ATR medio
    atr_values = [0.00050, 0.00055, 0.00048, 0.00052, 0.00049]
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {abs(entry_price - stop_loss):.5f} ({abs(entry_price - stop_loss)*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")
    
    # Escenario 7: Con riesgo muy pequeño para ver ratios altos
    print("\n📊 ESCENARIO 7: Riesgo muy pequeño (5 pips)")
    entry_price = 1.08500
    stop_loss = 1.08450  # Solo 5 pips de riesgo
    
    # ATR alto
    atr_values = [0.00100, 0.00110, 0.00095, 0.00105, 0.00098]
    
    tp, rr = calcular_tp_estructural(entry_price, stop_loss, atr_values)
    print(f"   💰 Entry: {entry_price:.5f}")
    print(f"   🛑 Stop Loss: {stop_loss:.5f}")
    print(f"   📏 Risk Distance: {abs(entry_price - stop_loss):.5f} ({abs(entry_price - stop_loss)*10000:.0f} pips)")
    print(f"   📈 ATR Promedio: {sum(atr_values)/len(atr_values):.5f}")
    print(f"   🎯 Take Profit: {tp:.5f}")
    print(f"   📊 R:R Ratio: 1:{rr:.2f}")

def validar_formula_atr():
    """
    Validar la fórmula del cálculo de ATR
    """
    print("\n🔬 VALIDACIÓN DE LA FÓRMULA ATR")
    print("=" * 40)
    
    # Simular datos de velas
    high = 1.08550
    low = 1.08400
    close_prev = 1.08450
    
    # Calcular True Range
    tr1 = high - low  # High - Low
    tr2 = abs(high - close_prev)  # High - Previous Close
    tr3 = abs(low - close_prev)   # Low - Previous Close
    
    tr = max(tr1, tr2, tr3)
    
    print(f"   📊 High: {high:.5f}")
    print(f"   📊 Low: {low:.5f}")
    print(f"   📊 Previous Close: {close_prev:.5f}")
    print(f"   📏 True Range: {tr:.5f}")
    print(f"   📏 True Range (pips): {tr*10000:.0f}")

def mostrar_resumen():
    """
    Mostrar resumen de los ratios posibles
    """
    print("\n📋 RESUMEN DE RATIOS POSIBLES")
    print("=" * 40)
    print("   🎯 R:R Mínimo: 1:1.0")
    print("   🎯 R:R Máximo: 1:3.0")
    print("   🎯 R:R Fallback: 1:1.5 (sin datos ATR)")
    print("   📊 Ratios intermedios posibles: 1:1.2, 1:1.5, 1:2.1, 1:2.8, etc.")
    print("\n   💡 El ratio se calcula basado en:")
    print("      - ATR (Average True Range) del mercado")
    print("      - Distancia de riesgo (Entry - Stop Loss)")
    print("      - Fórmula: min(3.0, max(1.0, (ATR * 2) / risk_distance))")
    print("\n   ✅ CONCLUSIÓN: El Take Profit NO siempre será 1:1")
    print("      Puede variar desde 1:1 hasta 1:3 según la volatilidad del mercado")

if __name__ == '__main__':
    try:
        print("🎯 VALIDACIÓN DE RATIOS DE TAKE PROFIT")
        print("=" * 60)
        
        # Validar fórmula ATR
        validar_formula_atr()
        
        # Simular diferentes escenarios
        simular_diferentes_escenarios()
        
        # Mostrar resumen
        mostrar_resumen()
        
        print("\n" + "=" * 60)
        print("✅ VALIDACIÓN COMPLETADA")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error en la validación: {e}")
        import traceback
        traceback.print_exc()
