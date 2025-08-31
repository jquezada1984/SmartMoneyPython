#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG ICC SIGNALS
================

Script para debuggear por qué no se están mostrando compras y ventas
en prueba_icc.py
"""

import pandas as pd
import os
import sys
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la estrategia ICC real
from estrategia.icc import ICCStrategy as SmartMoneyICCStrategy

def test_icc_signals():
    """Probar si se generan señales ICC"""
    
    print("🔍 DEBUG: Probando generación de señales ICC")
    print("=" * 50)
    
    try:
        # Cargar datos de prueba
        csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
        
        if not os.path.exists(csv_path):
            print(f"❌ Error: No se encontró el archivo {csv_path}")
            return False
        
        print(f"📂 Leyendo archivo: {csv_path}")
        
        # Leer datos
        df = pd.read_csv(csv_path, index_col="datetime")
        df = df.astype(float)
        df = df[["open", "high", "low", "close", "volume"]]
        df.index = pd.to_datetime(df.index)
        
        # Tomar solo las primeras 1000 velas para prueba rápida
        df_test = df.head(1000)
        
        print(f"✅ Datos cargados: {len(df_test)} velas")
        print(f"📅 Rango: {df_test.index[0]} a {df_test.index[-1]}")
        
        # Crear timeframes superiores
        df_1h = df_test.resample('1H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        df_4h = df_test.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        print(f"📊 Timeframes creados:")
        print(f"   5M: {len(df_test)} velas")
        print(f"   1H: {len(df_1h)} velas")
        print(f"   4H: {len(df_4h)} velas")
        
        # Inicializar estrategia ICC
        print(f"\n🚀 Inicializando estrategia ICC...")
        smartmoney_icc = SmartMoneyICCStrategy(
            risk_reward_min=1.0,
            ob_lookback=50,
            fvg_lookback=30,
            swing_length=20
        )
        
        print(f"✅ Estrategia ICC inicializada")
        
        # Probar generación de señales
        print(f"\n🔍 Probando generación de señales...")
        
        # Habilitar logging completo para ver qué pasa
        import logging
        logging.basicConfig(level=logging.INFO)
        
        signals = smartmoney_icc.scan_for_icc_signals(df_test, df_1h, df_4h)
        
        if signals:
            print(f"✅ SEÑALES DETECTADAS: {len(signals)}")
            for i, signal in enumerate(signals):
                print(f"\n🎯 Señal {i+1}:")
                print(f"   Dirección: {signal.get('direction', 'N/A')}")
                print(f"   Precio entrada: {signal.get('entry_price', 'N/A')}")
                print(f"   Risk Management: {signal.get('risk_management', {})}")
        else:
            print(f"❌ NO SE DETECTARON SEÑALES")
            print(f"   💡 Esto explica por qué no hay compras/ventas")
            print(f"   🔍 Revisando posibles causas...")
            
            # Verificar si hay suficientes datos
            print(f"\n📊 Verificación de datos:")
            print(f"   Datos 5M: {len(df_test)} (mínimo recomendado: 100)")
            print(f"   Datos 1H: {len(df_1h)} (mínimo recomendado: 20)")
            print(f"   Datos 4H: {len(df_4h)} (mínimo recomendado: 10)")
            
            # Verificar si hay Order Blocks o FVG
            print(f"\n🔍 Verificando componentes SmartMoney...")
            
            # Probar con más datos
            print(f"\n🔄 Probando con más datos...")
            df_more = df.head(2000)
            df_1h_more = df_more.resample('1H').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
            df_4h_more = df_more.resample('4H').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
            
            signals_more = smartmoney_icc.scan_for_icc_signals(df_more, df_1h_more, df_4h_more)
            
            if signals_more:
                print(f"✅ CON MÁS DATOS: {len(signals_more)} señales detectadas")
            else:
                print(f"❌ CON MÁS DATOS: Aún no hay señales")
                print(f"   💡 Posibles causas:")
                print(f"      - No hay Order Blocks válidos en el período")
                print(f"      - No hay Fair Value Gaps válidos")
                print(f"      - No se cumplen los criterios de R:R mínimo")
                print(f"      - El mercado está en rango lateral")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backtrader_integration():
    """Probar integración con Backtrader"""
    
    print(f"\n🔍 DEBUG: Probando integración con Backtrader")
    print("=" * 50)
    
    try:
        import backtrader as bt
        
        # Crear datos de prueba simples
        data = pd.DataFrame({
            'open': [1.0800, 1.0810, 1.0820, 1.0815, 1.0830],
            'high': [1.0815, 1.0825, 1.0835, 1.0825, 1.0840],
            'low': [1.0795, 1.0805, 1.0815, 1.0810, 1.0825],
            'close': [1.0810, 1.0820, 1.0815, 1.0830, 1.0835],
            'volume': [1000, 1200, 1100, 1300, 1400]
        })
        data.index = pd.date_range('2025-01-01', periods=5, freq='5min')
        
        # Crear cerebro de Backtrader
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000.0)
        
        # Agregar datos
        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None,
            open=0, high=1, low=2, close=3, volume=4, openinterest=-1
        )
        cerebro.adddata(data_feed)
        
        # Crear estrategia simple de prueba
        class TestStrategy(bt.Strategy):
            def __init__(self):
                self.order = None
                print("🚀 TestStrategy inicializada")
            
            def next(self):
                if not self.position and not self.order:
                    print("🟢 Ejecutando orden de compra de prueba...")
                    self.buy()
            
            def notify_order(self, order):
                if order.status in [order.Completed]:
                    if order.isbuy():
                        print(f"✅ COMPRA EJECUTADA - Precio: {order.executed.price:.5f}")
                    else:
                        print(f"🔴 VENTA EJECUTADA - Precio: {order.executed.price:.5f}")
                self.order = None
        
        # Agregar estrategia de prueba
        cerebro.addstrategy(TestStrategy)
        
        print("🔄 Ejecutando backtesting de prueba...")
        results = cerebro.run()
        
        print("✅ Backtesting de prueba completado")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba Backtrader: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    
    print("🔍 DEBUG ICC SIGNALS - ¿Por qué no hay compras/ventas?")
    print("=" * 60)
    
    # Prueba 1: Verificar generación de señales
    test1_success = test_icc_signals()
    
    # Prueba 2: Verificar integración Backtrader
    test2_success = test_backtrader_integration()
    
    print(f"\n📊 RESUMEN DE PRUEBAS:")
    print(f"   🔍 Generación de señales: {'✅' if test1_success else '❌'}")
    print(f"   📈 Integración Backtrader: {'✅' if test2_success else '❌'}")
    
    if not test1_success:
        print(f"\n💡 RECOMENDACIONES:")
        print(f"   1. Verificar que el archivo de datos existe")
        print(f"   2. Verificar que la estrategia ICC está funcionando")
        print(f"   3. Probar con diferentes períodos de datos")
        print(f"   4. Revisar los parámetros de la estrategia")
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print(f"   1. Si no hay señales: Ajustar parámetros de la estrategia")
    print(f"   2. Si hay señales pero no órdenes: Revisar integración Backtrader")
    print(f"   3. Si todo funciona: El problema está en otro lugar")

if __name__ == '__main__':
    main()
