#!/usr/bin/env python3
"""
Ejemplo completo de uso de la librería MT5Connector con Smart Money Concepts
Este script demuestra cómo conectar con MT5, obtener datos, analizar con SMC y generar señales
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartmoneyconcepts.mt5_connector import MT5Connector
import pandas as pd
from datetime import datetime, timedelta

def main():
    print("🚀 Iniciando ejemplo de trading con Smart Money Concepts")
    print("=" * 60)
    
    # Configuración de conexión (opcional - si no se proporciona, usa MT5 local)
    # login = 12345678
    # password = "tu_password"
    # server = "tu_broker"
    
    # Inicializar conector
    print("📡 Conectando a MetaTrader 5...")
    mt5 = MT5Connector()
    # mt5 = MT5Connector(login=login, password=password, server=server)
    
    if not mt5.connected:
        print("❌ No se pudo conectar a MT5. Verifica que MT5 esté abierto.")
        return
    
    # Configuración de trading
    symbol = "EURUSD"
    timeframe = "1h"
    bars = 500
    
    print(f"\n📊 Obteniendo datos de {symbol}...")
    
    # Obtener datos
    df = mt5.get_data(symbol, timeframe, bars)
    
    if df.empty:
        print("❌ No se pudieron obtener datos")
        return
    
    print(f"✅ Datos obtenidos: {len(df)} barras")
    print(f"   Rango: {df.index[0]} a {df.index[-1]}")
    print(f"   Precio actual: {df['close'].iloc[-1]:.5f}")
    
    # Análisis de Smart Money Concepts
    print(f"\n🔍 Realizando análisis de Smart Money Concepts...")
    smc_analysis = mt5.analyze_smc(df, swing_length=20)
    
    if not smc_analysis:
        print("❌ Error en análisis SMC")
        return
    
    # Análisis de patrones de velas
    print(f"\n🕯️ Analizando patrones de velas...")
    patterns = mt5.analyze_patterns(df)
    
    # Generar señales
    print(f"\n📊 Generando señales de trading...")
    signals = mt5.generate_signals(df, smc_analysis, patterns)
    
    # Mostrar resultados
    print(f"\n📈 RESULTADOS DEL ANÁLISIS")
    print("=" * 40)
    
    # Información de tendencia
    if 'trend_indicator' in smc_analysis:
        trend_data = smc_analysis['trend_indicator']
        if not trend_data.empty:
            latest_trend = trend_data.iloc[-1]
            trend_text = "ALCISTA" if latest_trend['Trend'] == 1 else "BAJISTA" if latest_trend['Trend'] == -1 else "LATERAL"
            print(f"🎯 Tendencia: {trend_text}")
            print(f"💪 Fuerza: {latest_trend['Strength']:.1f}%")
            print(f"🎯 Confianza: {latest_trend['Confidence']:.1f}%")
    
    # Señales de trading
    print(f"\n🔔 SEÑALES DE TRADING")
    print("=" * 30)
    
    if signals['buy_signals']:
        print("🟢 SEÑALES DE COMPRA:")
        for signal in signals['buy_signals']:
            print(f"   • {signal['type']} - Score: {signal['score']}")
            print(f"     Precio: {signal['price']:.5f}")
            print(f"     Razón: {signal['reason']}")
    
    if signals['sell_signals']:
        print("🔴 SEÑALES DE VENTA:")
        for signal in signals['sell_signals']:
            print(f"   • {signal['type']} - Score: {signal['score']}")
            print(f"     Precio: {signal['price']:.5f}")
            print(f"     Razón: {signal['reason']}")
    
    if not signals['buy_signals'] and not signals['sell_signals']:
        print("⚪ No hay señales claras en este momento")
    
    # Análisis detallado de indicadores
    print(f"\n📊 ANÁLISIS DETALLADO")
    print("=" * 30)
    
    # FVG
    fvg_data = smc_analysis.get('fvg', pd.DataFrame())
    if not fvg_data.empty:
        recent_fvg = fvg_data.iloc[-10:]
        bullish_fvg = recent_fvg[recent_fvg['FVG'] == 1]
        bearish_fvg = recent_fvg[recent_fvg['FVG'] == -1]
        print(f"📈 Fair Value Gaps: {len(bullish_fvg)} alcistas, {len(bearish_fvg)} bajistas")
    
    # Order Blocks
    ob_data = smc_analysis.get('ob', pd.DataFrame())
    if not ob_data.empty:
        recent_ob = ob_data.iloc[-10:]
        bullish_ob = recent_ob[recent_ob['OB'] == 1]
        bearish_ob = recent_ob[recent_ob['OB'] == -1]
        print(f"📦 Order Blocks: {len(bullish_ob)} alcistas, {len(bearish_ob)} bajistas")
    
    # Patrones de velas
    if patterns:
        print(f"🕯️ Patrones detectados:")
        for pattern_name, pattern_data in patterns.items():
            if not pattern_data.empty and pattern_data.iloc[-1]:
                print(f"   • {pattern_name.replace('_', ' ').title()}")
    
    # Premium/Discount Zones
    pd_data = smc_analysis.get('premium_discount_zones', pd.DataFrame())
    if not pd_data.empty:
        current_zone = pd_data.iloc[-1]['Zone']
        if not pd.isna(current_zone):
            zone_text = "PREMIUM" if current_zone == 1 else "DISCOUNT" if current_zone == -1 else "NEUTRAL"
            print(f"💰 Zona actual: {zone_text}")
    
    # Posiciones abiertas
    print(f"\n💼 POSICIONES ABIERTAS")
    print("=" * 25)
    positions = mt5.get_positions(symbol)
    
    if not positions.empty:
        print(f"Posiciones abiertas en {symbol}:")
        for _, pos in positions.iterrows():
            pos_type = "COMPRA" if pos['type'] == 0 else "VENTA"
            print(f"   • {pos_type} - Volumen: {pos['volume']} - P&L: ${pos['profit']:.2f}")
    else:
        print(f"No hay posiciones abiertas en {symbol}")
    
    # Ejemplo de colocación de orden (comentado por seguridad)
    print(f"\n⚠️  EJEMPLO DE ORDEN (NO EJECUTADA)")
    print("=" * 40)
    print("Para ejecutar una orden real, descomenta las líneas siguientes:")
    print("""
    # Ejemplo de orden de compra
    # if signals['buy_signals']:
    #     signal = signals['buy_signals'][0]
    #     volume = 0.1  # 0.1 lotes
    #     sl = signal['price'] * 0.998  # Stop Loss 0.2% abajo
    #     tp = signal['price'] * 1.002  # Take Profit 0.2% arriba
    #     
    #     success = mt5.place_order(
    #         symbol=symbol,
    #         order_type="BUY",
    #         volume=volume,
    #         sl=sl,
    #         tp=tp,
    #         comment="SMC Signal"
    #     )
    """)
    
    # Cerrar conexión
    mt5.disconnect()
    print(f"\n✅ Análisis completado")

if __name__ == "__main__":
    main() 