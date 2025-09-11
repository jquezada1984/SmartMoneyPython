#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBA ICC SMARTMONEY CON BACKTRADER
====================================

Este script implementa la estrategia ICC SmartMoney usando Backtrader
con datos de EURUSD, integrando Order Blocks, Fair Value Gaps y análisis
de múltiples timeframes.
"""

import backtrader as bt
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from tqdm import tqdm
import time

# Agregar el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

cantidad_velas = 2500

# Importar la estrategia ICC real
try:
    from estrategia.icc import ICCStrategy as SmartMoneyICCStrategy
    print("✅ Estrategia ICC importada exitosamente")
except ImportError as e:
    print(f"❌ Error importando estrategia ICC: {e}")
    SmartMoneyICCStrategy = None

# Importar la librería de análisis de mercado
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib

# Generación de imágenes deshabilitada
print("📊 Modo de visualización: Solo texto (sin generación de imágenes)")

class ICCStrategy(bt.Strategy):
    """Estrategia ICC SmartMoney con Backtrader"""
    

    def __init__(self, df_5m=None, df_1h=None, df_4h=None, cantidad_velas=2500):
        # Guardar referencias a los DataFrames
        self.df_5m = df_5m
        self.df_1h = df_1h
        self.df_4h = df_4h
        self.cantidad_velas = cantidad_velas
        
        # Indicadores técnicos básicos para Backtrader
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        
        # Instancia de análisis de mercado para detectar tendencias
        self.market_analysis = MarketAnalysisLib()
        
        # Variable para órdenes pendientes
        self.order = None
        
        # Contadores de operaciones
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Lista para almacenar resultados de operaciones
        self.trades = []
        
        # Variables para trailing stop
        self.trailing_stop_breakeven = False  # Si ya se movió al breakeven
        self.trailing_stop_profit = False     # Si ya se movió para asegurar ganancia
        
        # Variables para CSV de trades
        self.trades_csv_data = []
        self.csv_filename = f"trades_icc_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Inicializar la estrategia SmartMoney ICC
        try:
            if SmartMoneyICCStrategy is None:
                raise ImportError("SmartMoneyICCStrategy no está disponible")
            
            self.smartmoney_icc = SmartMoneyICCStrategy(
                risk_reward_min=1.0,  # R:R mínimo 1:1
                ob_lookback=50,
                fvg_lookback=30,
                swing_length=20
            )
            print(f"   ✅ Estrategia SmartMoney ICC inicializada correctamente")
        except Exception as e:
            print(f"   ❌ Error inicializando estrategia SmartMoney ICC: {e}")
            self.smartmoney_icc = None
        
        # Almacenar datos para análisis SmartMoney
        self.data_buffer = []
        self.last_analysis_time = None
        
        # Almacenar DataFrames de múltiples timeframes para acceso en otros métodos
        self.df_5m = None
        self.df_1h = df_1h  # Usar los datos pasados desde run_backtest
        self.df_4h = df_4h  # Usar los datos pasados desde run_backtest
        
        # Variables para gestión de riesgo ICC
        self.current_position_info = None  # Almacenar info de la posición actual
        self.stop_loss_level = None
        self.take_profit_levels = None
        
        # Variables para seguimiento de progreso
        self.total_bars = 0  # Se inicializará en start()
        self.current_bar = 0
        self.last_progress_update = 0
        
        print(f"🚀 Estrategia ICC SmartMoney inicializada")
        print(f"   🎯 Mínimo R:R requerido: 1:1")
        print(f"   📊 Modo de visualización: Solo texto")
        print(f"      • Mostrar puntos de entrada, profit y loss")
        print(f"      • Sin generación de imágenes")
        
    def log(self, txt, dt=None):
        """Función de logging"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
        
    def calculate_macd(df, fast=12, slow=26, signal=9):
        """Calcular MACD: MACD Line, Signal Line, Histogram"""
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_rsi(df, period=14):
        """Calcular RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def update_progress(self):
        """Actualizar progreso del backtesting"""
        self.current_bar += 1
        
        # Verificar que tenemos datos válidos
        if self.total_bars <= 0:
            return
        
        # Mostrar progreso cada 100 velas o en eventos importantes
        if (self.current_bar % 100 == 0 or 
            self.current_bar == self.total_bars or 
            self.current_bar - self.last_progress_update >= 500):
            
            progress_pct = (self.current_bar / self.total_bars) * 100
            current_time = self.data.datetime.datetime(0)
            
            self.last_progress_update = self.current_bar
        
    def next(self):
        # Actualizar progreso
        self.update_progress()
        
        # Mostrar progreso cada 200 velas
        if self.current_bar % 200 == 0:
            current_time = self.data.datetime.datetime(0)
            print(f"   📊 Procesando vela {self.current_bar}/{self.total_bars} - {current_time}")
        
        # Solo operar si no hay órdenes pendientes
        if self.order:
            return
        
        # Acumular datos para análisis SmartMoney
        current_candle = {
            'open': self.data.open[0],
            'high': self.data.high[0],
            'low': self.data.low[0],
            'close': self.data.close[0],
            'volume': self.data.volume[0],
            'datetime': self.data.datetime.datetime(0)
        }
        self.data_buffer.append(current_candle)
        
        # Verificar si ya tenemos una posición abierta
        if self.position:
            # GESTIÓN DE RIESGO ICC - Verificar Stop Loss y Take Profit
            self.check_icc_risk_management()
            return
        
        # Verificar que tenemos suficientes datos para análisis SmartMoney
        if len(self.data_buffer) < 100:  # Necesitamos al menos 100 velas
            return
        
       
        if len(self.data_buffer) >= 100:
            try:
                # Convertir buffer a DataFrame
                df_5m = pd.DataFrame(self.data_buffer)
                df_5m.set_index('datetime', inplace=True)
                # Convertir el índice a string con formato específico para la estrategia ICC
                if not isinstance(df_5m.index, pd.DatetimeIndex):
                    df_5m.index = pd.to_datetime(df_5m.index)
                df_5m.index = df_5m.index.strftime("%Y-%m-%d %H:%M:%S")
                
                # Usar los datos de múltiples timeframes ya cargados
                # Filtrar solo los datos que corresponden al período actual
                current_time_str = df_5m.index[-1]  # String format
                current_time_dt = pd.to_datetime(current_time_str)  # Convertir a datetime para comparar
                
                # Filtrar datos H1 y H4 hasta el tiempo actual (usando datetime para comparar)
                df_1h_filtered = self.df_1h[self.df_1h.index <= current_time_dt] if self.df_1h is not None else pd.DataFrame()
                df_4h_filtered = self.df_4h[self.df_4h.index <= current_time_dt] if self.df_4h is not None else pd.DataFrame()
                
                # Convertir los índices filtrados a string para la estrategia ICC
                if not df_1h_filtered.empty:
                    df_1h_filtered = df_1h_filtered.copy()
                    df_1h_filtered.index = df_1h_filtered.index.strftime("%Y-%m-%d %H:%M:%S")
                if not df_4h_filtered.empty:
                    df_4h_filtered = df_4h_filtered.copy()
                    df_4h_filtered.index = df_4h_filtered.index.strftime("%Y-%m-%d %H:%M:%S")
                
                # Almacenar DataFrames para acceso en otros métodos
                self.df_5m = df_5m
                # No sobrescribir df_1h y df_4h, ya están establecidos en __init__

                try:
                    signals = self.smartmoney_icc.scan_for_icc_signals(df_5m, df_1h_filtered, df_4h_filtered)

                except Exception as e:
                    signals = None
                
                if signals:
                    # Procesar señales SmartMoney
                    for signal in signals:
                        direction = signal['direction']
                        entry_price = signal['entry_price']
                        
                        # Obtener gestión de riesgo ICC
                        risk_management = signal.get('risk_management', {})
                        stop_loss = risk_management.get('stop_loss')
                        take_profit = risk_management.get('take_profit')  # TP ESTRUCTURAL ÚNICO
                        risk_reward_ratio = risk_management.get('risk_reward_ratio', 0)
                        
                        # Obtener niveles estructurales (para referencia)
                        structural_levels = risk_management.get('structural_levels', [])
                        
                        # VALIDAR TAKE PROFIT ESTRUCTURAL
                        if not self.validate_structural_take_profit(entry_price, take_profit, direction, self.df_1h, self.df_4h):
                            print(f"   ❌ SEÑAL RECHAZADA: Take Profit no está en nivel estructural válido")
                            continue
                        
                        # Almacenar información de la posición para gestión de riesgo
                        self.current_position_info = {
                            'direction': direction,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,  # UN SOLO TP ESTRUCTURAL
                            'risk_reward_ratio': risk_reward_ratio,
                            'structural_levels': structural_levels
                        }
                        
                        # Reiniciar variables de trailing stop para nueva posición
                        self.trailing_stop_breakeven = False
                        self.trailing_stop_profit = False
                        
                        # MOSTRAR INFORMACIÓN DETALLADA DE LA SEÑAL ICC
                        print(f"   📊 INFORMACIÓN DETALLADA DE LA SEÑAL ICC:")
                        print(f"   " + "="*60)
                        print(f"   🎯 DIRECCIÓN: {direction}")
                        print(f"   💰 PUNTO DE ENTRADA: {entry_price:.5f}")
                        print(f"   🛑 STOP LOSS: {stop_loss:.5f}")
                        print(f"   🎯 TAKE PROFIT: {take_profit:.5f}")
                        print(f"   📊 RIESGO/BENEFICIO: 1:{risk_reward_ratio:.2f}")
                        print(f"   🔍 FUENTE: {signal.get('source', 'ICC')}")
                        print(f"   📅 FECHA/HORA: {self.data.datetime.datetime(0)}")
                        print(f"   " + "="*60)
                        
                        # Mostrar niveles estructurales si están disponibles
                        if structural_levels:
                            print(f"   📊 NIVELES ESTRUCTURALES:")
                            for i, level in enumerate(structural_levels, 1):
                                print(f"      {i}. {level}")
                        print(f"   " + "="*60)
                                                
                        # Ejecutar orden según dirección
                        print(f"   🚀 EJECUTANDO ORDEN: {direction}")
                        if direction == 'LONG':
                            print(f"   📈 ENVIANDO ORDEN DE COMPRA...")
                            self.order = self.buy()
                        elif direction == 'SHORT':
                            print(f"   📉 ENVIANDO ORDEN DE VENTA...")
                            self.order = self.sell()
                        
                        print(f"   ✅ ORDEN ENVIADA")
                        # Solo procesar la primera señal
                        break
                else:
                    # No hay señales SmartMoney - NO OPERAR
                    # Solo SmartMoney ICC puede generar señales de entrada
                    pass
                        
            except Exception as e:
                # Solo SmartMoney ICC puede generar señales - NO OPERAR en caso de error
                self.log(f"⚠️ Error en análisis SmartMoney: {e}")
                pass
    
    def check_icc_risk_management(self):
        """Verificar Stop Loss y Take Profit basado en gestión de riesgo ICC con Trailing Stop"""
        if not self.current_position_info:
            return
            
        current_price = self.data.close[0]
        direction = self.current_position_info['direction']
        entry_price = self.current_position_info['entry_price']
        stop_loss = self.current_position_info['stop_loss']
        
        # Obtener Take Profit estructural ÚNICO
        take_profit = self.current_position_info.get('take_profit')
        rr_ratio = self.current_position_info.get('risk_reward_ratio', 0)
        
        # Calcular distancia desde entrada
        if direction == 'LONG':
            distance_to_profit = take_profit - entry_price if take_profit else 0
            distance_to_sl = entry_price - stop_loss
            current_profit_distance = current_price - entry_price
            
            # Debug: Verificar que las distancias sean correctas
            if distance_to_profit <= distance_to_sl:
                self.log(f"⚠️ ADVERTENCIA: Distancia al TP ({distance_to_profit:.5f}) <= Distancia al SL ({distance_to_sl:.5f})")
                self.log(f"   Entrada: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                self.log(f"   R:R reportado: {rr_ratio:.2f}, R:R real: {distance_to_profit/distance_to_sl:.2f}")
            
            # TRAILING STOP LOGIC
            # 1. Mover SL al breakeven cuando el precio avance la misma distancia que el riesgo inicial
            if not self.trailing_stop_breakeven and current_profit_distance >= distance_to_sl:
                # Mover SL al punto de entrada (breakeven) con un pequeño margen
                new_sl = entry_price + (distance_to_sl * 0.1)  # 10% del riesgo original como margen
                self.current_position_info['stop_loss'] = new_sl
                self.trailing_stop_breakeven = True
                self.log(f"🔄 TRAILING STOP: SL movido al breakeven - Nuevo SL: {new_sl:.5f}")
            
            # 2. Para R:R >= 1:2, mover SL para asegurar ganancia mínima cuando esté cerca de 1:2
            elif (not self.trailing_stop_profit and rr_ratio >= 2.0 and 
                  current_profit_distance >= distance_to_sl * 1.8):  # 90% del camino a 1:2
                # Mover SL para asegurar ganancia de al menos 1:1
                new_sl = entry_price + distance_to_sl  # Asegurar ganancia 1:1
                self.current_position_info['stop_loss'] = new_sl
                self.trailing_stop_profit = True
                self.log(f"🔄 TRAILING STOP: SL movido para asegurar ganancia 1:1 - Nuevo SL: {new_sl:.5f}")
            
            # Verificar Stop Loss (precio por debajo del SL)
            if current_price <= self.current_position_info['stop_loss']:
                self.log(f"🛑 STOP LOSS alcanzado - Precio: {current_price:.5f}, SL: {self.current_position_info['stop_loss']:.5f}")
                self.close()
                self.current_position_info = None
                self.trailing_stop_breakeven = False
                self.trailing_stop_profit = False
                return
                
            # Verificar Take Profit estructural ÚNICO
            if take_profit and current_price >= take_profit:
                self.log(f"🎯 TAKE PROFIT ESTRUCTURAL alcanzado - Precio: {current_price:.5f}, TP: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})")
                self.close()
                self.current_position_info = None
                self.trailing_stop_breakeven = False
                self.trailing_stop_profit = False
                return
                
        elif direction == 'SHORT':
            distance_to_profit = entry_price - take_profit if take_profit else 0
            distance_to_sl = stop_loss - entry_price
            current_profit_distance = entry_price - current_price
            
            # Debug: Verificar que las distancias sean correctas
            if distance_to_profit <= distance_to_sl:
                self.log(f"⚠️ ADVERTENCIA: Distancia al TP ({distance_to_profit:.5f}) <= Distancia al SL ({distance_to_sl:.5f})")
                self.log(f"   Entrada: {entry_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                self.log(f"   R:R reportado: {rr_ratio:.2f}, R:R real: {distance_to_profit/distance_to_sl:.2f}")
            
            # TRAILING STOP LOGIC
            # 1. Mover SL al breakeven cuando el precio avance la misma distancia que el riesgo inicial
            if not self.trailing_stop_breakeven and current_profit_distance >= distance_to_sl:
                # Mover SL al punto de entrada (breakeven) con un pequeño margen
                new_sl = entry_price - (distance_to_sl * 0.1)  # 10% del riesgo original como margen
                self.current_position_info['stop_loss'] = new_sl
                self.trailing_stop_breakeven = True
                self.log(f"🔄 TRAILING STOP: SL movido al breakeven - Nuevo SL: {new_sl:.5f}")
            
            # 2. Para R:R >= 1:2, mover SL para asegurar ganancia mínima cuando esté cerca de 1:2
            elif (not self.trailing_stop_profit and rr_ratio >= 2.0 and 
                  current_profit_distance >= distance_to_sl * 1.8):  # 90% del camino a 1:2
                # Mover SL para asegurar ganancia de al menos 1:1
                new_sl = entry_price - distance_to_sl  # Asegurar ganancia 1:1
                self.current_position_info['stop_loss'] = new_sl
                self.trailing_stop_profit = True
                self.log(f"🔄 TRAILING STOP: SL movido para asegurar ganancia 1:1 - Nuevo SL: {new_sl:.5f}")
            
            # Verificar Stop Loss (precio por encima del SL)
            if current_price >= self.current_position_info['stop_loss']:
                self.log(f"🛑 STOP LOSS alcanzado - Precio: {current_price:.5f}, SL: {self.current_position_info['stop_loss']:.5f}")
                self.close()
                self.current_position_info = None
                self.trailing_stop_breakeven = False
                self.trailing_stop_profit = False
                return
                
            # Verificar Take Profit estructural ÚNICO
            if take_profit and current_price <= take_profit:
                self.log(f"🎯 TAKE PROFIT ESTRUCTURAL alcanzado - Precio: {current_price:.5f}, TP: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})")
                self.close()
                self.current_position_info = None
                self.trailing_stop_breakeven = False
                self.trailing_stop_profit = False
                return
    
    def validate_structural_take_profit(self, entry_price, take_profit, direction, df_1h, df_4h):
        """
        Validar que el Take Profit esté en un nivel estructural válido de marcos superiores
        y que no esté dentro de un bloque de consolidación
        """
        if not take_profit:
            return False
        
        # Tolerancia para considerar que un precio está "cerca" de un nivel estructural
        tolerance = 0.0005  # 5 pips
        
        # Obtener niveles estructurales de H1 y H4
        h1_levels = self.get_structural_levels(df_1h)
        h4_levels = self.get_structural_levels(df_4h)
        
        # Combinar niveles de ambos timeframes
        all_levels = h1_levels + h4_levels
        
        # Verificar si el Take Profit está cerca de algún nivel estructural
        tp_near_level = False
        for level in all_levels:
            if abs(take_profit - level) <= tolerance:
                tp_near_level = True
                break
        
        if not tp_near_level:
            print(f"   ⚠️ Take Profit {take_profit:.5f} no está cerca de nivel estructural")
            return False
        
        # Verificar que la entrada no esté dentro de un bloque de consolidación
        if self.is_inside_consolidation_block(entry_price, df_1h, df_4h):
            print(f"   ⚠️ Entrada {entry_price:.5f} está dentro de bloque de consolidación")
            return False
        
        # Verificar que el Take Profit esté en la dirección correcta
        if direction == 'LONG' and take_profit <= entry_price:
            print(f"   ⚠️ Take Profit {take_profit:.5f} no está por encima de entrada {entry_price:.5f}")
            return False
        elif direction == 'SHORT' and take_profit >= entry_price:
            print(f"   ⚠️ Take Profit {take_profit:.5f} no está por debajo de entrada {entry_price:.5f}")
            return False
        
        return True
    
    def get_structural_levels(self, df):
        """
        Obtener niveles estructurales (soportes y resistencias) de un DataFrame
        """
        if df is None or len(df) < 20:
            return []
        
        levels = []
        
        # Buscar máximos y mínimos locales
        highs = df['high'].values
        lows = df['low'].values
        
        # Encontrar máximos locales (resistencias)
        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                levels.append(highs[i])
        
        # Encontrar mínimos locales (soportes)
        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                levels.append(lows[i])
        
        # Filtrar niveles muy cercanos entre sí
        filtered_levels = []
        for level in sorted(levels):
            if not filtered_levels or abs(level - filtered_levels[-1]) > 0.001:  # 10 pips mínimo
                filtered_levels.append(level)
        
        return filtered_levels
    
    def is_inside_consolidation_block(self, price, df_1h, df_4h):
        """
        Verificar si un precio está dentro de un bloque de consolidación
        """
        if df_1h is None or len(df_1h) < 10:
            return False
        
        # Obtener el rango de precios reciente en H1 (últimas 10 velas)
        recent_1h = df_1h.tail(10)
        recent_high = recent_1h['high'].max()
        recent_low = recent_1h['low'].min()
        
        # Si el precio está dentro del rango reciente, podría estar en consolidación
        if recent_low <= price <= recent_high:
            # Verificar si hay mucha volatilidad (no consolidación)
            price_range = recent_high - recent_low
            if price_range < 0.002:  # Menos de 20 pips de rango
                return True
        
        return False
    
    def add_trade_to_csv(self, trade_data):
        """
        Agregar información de trade al CSV
        """
        self.trades_csv_data.append(trade_data)
    
    def save_trades_csv(self):
        """
        Guardar el CSV con todos los trades
        """
        if not self.trades_csv_data:
            return
        
        import csv
        import os
        
        # Crear directorio si no existe
        csv_dir = "trades_logs"
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
        
        csv_path = os.path.join(csv_dir, self.csv_filename)
        
        # Definir headers del CSV
        headers = [
            'Fecha', 'Hora', 'Minuto', 'Dia_Semana',
            'Tipo_Operacion', 'Punto_Entrada', 'Stop_Loss', 'Take_Profit',
            'R_R_Ratio', 'Precio_Cierre', 'Fecha_Cierre', 'Hora_Cierre',
            'Resultado', 'P_L_Bruto', 'P_L_Neto', 'ROI_Porcentaje',
            'Tipo_Cierre', 'Duracion_Minutos', 'Trailing_Stop_Breakeven', 'Trailing_Stop_Profit'
        ]
        
        # Escribir CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(self.trades_csv_data)
        
        print(f"   📊 CSV de trades guardado: {csv_path}")
        print(f"   📈 Total de trades registrados: {len(self.trades_csv_data)}")
    
    def notify_order(self, order):
        """Notificar cambios en órdenes"""
        print(f"   📋 Notificación de orden: {order.status}")
        
        if order.status in [order.Submitted, order.Accepted]:
            print(f"   ⏳ Orden {order.status}: Esperando ejecución...")
            return
        
        if order.status in [order.Completed]:
            print(f"   ✅ ORDEN COMPLETADA: {order.ref}")
            print(f"   💰 Precio de ejecución: {order.executed.price:.5f}")
            print(f"   📊 Cantidad: {order.executed.size}")
            print(f"   💸 Comisión: {order.executed.comm:.2f}")
            
            # MOSTRAR CONFIRMACIÓN DE ORDEN EJECUTADA
            if self.current_position_info:
                print(f"   ✅ CONFIRMACIÓN DE ORDEN EJECUTADA:")
                print(f"   " + "="*50)
                print(f"   🎯 DIRECCIÓN: {self.current_position_info['direction']}")
                print(f"   💰 PRECIO DE ENTRADA REAL: {order.executed.price:.5f}")
                print(f"   🛑 STOP LOSS: {self.current_position_info['stop_loss']:.5f}")
                print(f"   🎯 TAKE PROFIT: {self.current_position_info['take_profit']:.5f}")
                print(f"   📊 RIESGO/BENEFICIO: 1:{self.current_position_info['risk_reward_ratio']:.2f}")
                print(f"   📅 FECHA/HORA EJECUCIÓN: {self.data.datetime.datetime(0)}")
                print(f"   " + "="*50)
            
            if order.isbuy():
                # Mostrar información de gestión de riesgo para compras
                if self.current_position_info and self.current_position_info['direction'] == 'LONG':
                    stop_loss = self.current_position_info['stop_loss']
                    take_profit = self.current_position_info['take_profit']
                    rr_ratio = self.current_position_info.get('risk_reward_ratio', 0)
                    
                    current_time = self.data.datetime.datetime(0)
                    self.log(f'🟢 COMPRA EJECUTADA - Precio: {order.executed.price:.5f}')
                    self.log(f'   📅 Hora de ejecución: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
                    self.log(f'   📊 Cantidad: +{order.executed.size} (COMPRA)')
                    self.log(f'   💰 Valor total: {order.executed.value:.2f}, Comisión: {order.executed.comm:.2f}')
                    self.log(f'   🛑 Stop Loss: {stop_loss:.5f}')
                    self.log(f'   🎯 Take Profit Estructural: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})')
                    
                    # Agregar trade al CSV
                    self.add_trade_to_csv([
                        current_time.strftime("%Y-%m-%d"),  # Fecha
                        current_time.strftime("%H:%M:%S"),  # Hora
                        current_time.minute,                # Minuto
                        current_time.strftime("%A"),        # Día de la semana
                        'LONG',                             # Tipo operación
                        order.executed.price,               # Punto entrada
                        stop_loss,                          # Stop Loss
                        take_profit,                        # Take Profit
                        rr_ratio,                           # R:R Ratio
                        '',                                 # Precio cierre (se llenará después)
                        '',                                 # Fecha cierre (se llenará después)
                        '',                                 # Hora cierre (se llenará después)
                        '',                                 # Resultado (se llenará después)
                        '',                                 # P&L Bruto (se llenará después)
                        '',                                 # P&L Neto (se llenará después)
                        '',                                 # ROI % (se llenará después)
                        '',                                 # Tipo cierre (se llenará después)
                        '',                                 # Duración minutos (se llenará después)
                        False,                              # Trailing Stop Breakeven
                        False                               # Trailing Stop Profit
                    ])
                else:
                    self.log(f'🟢 COMPRA EJECUTADA - Precio: {order.executed.price:.5f}')
            else:
                # Mostrar información de gestión de riesgo para ventas
                if self.current_position_info and self.current_position_info['direction'] == 'SHORT':
                    stop_loss = self.current_position_info['stop_loss']
                    take_profit = self.current_position_info['take_profit']
                    rr_ratio = self.current_position_info.get('risk_reward_ratio', 0)
                    
                    current_time = self.data.datetime.datetime(0)
                    self.log(f'🔴 VENTA EJECUTADA - Precio: {order.executed.price:.5f}')
                    self.log(f'   📅 Hora de ejecución: {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
                    self.log(f'   📊 Cantidad: {order.executed.size} (VENTA)')
                    self.log(f'   💰 Valor total: {order.executed.value:.2f}, Comisión: {order.executed.comm:.2f}')
                    self.log(f'   🛑 Stop Loss: {stop_loss:.5f}')
                    self.log(f'   🎯 Take Profit Estructural: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})')
                    
                    # Agregar trade al CSV
                    self.add_trade_to_csv([
                        current_time.strftime("%Y-%m-%d"),  # Fecha
                        current_time.strftime("%H:%M:%S"),  # Hora
                        current_time.minute,                # Minuto
                        current_time.strftime("%A"),        # Día de la semana
                        'SHORT',                            # Tipo operación
                        order.executed.price,               # Punto entrada
                        stop_loss,                          # Stop Loss
                        take_profit,                        # Take Profit
                        rr_ratio,                           # R:R Ratio
                        '',                                 # Precio cierre (se llenará después)
                        '',                                 # Fecha cierre (se llenará después)
                        '',                                 # Hora cierre (se llenará después)
                        '',                                 # Resultado (se llenará después)
                        '',                                 # P&L Bruto (se llenará después)
                        '',                                 # P&L Neto (se llenará después)
                        '',                                 # ROI % (se llenará después)
                        '',                                 # Tipo cierre (se llenará después)
                        '',                                 # Duración minutos (se llenará después)
                        False,                              # Trailing Stop Breakeven
                        False                               # Trailing Stop Profit
                    ])
                else:
                    self.log(f'🔴 VENTA EJECUTADA - Precio: {order.executed.price:.5f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Orden Cancelada/Margin/Rechazada')
        
        self.order = None
    
    def notify_trade(self, trade):
        """Notificar cambios en trades"""
        current_time = self.data.datetime.datetime(0)
        
        if not trade.isclosed:
            print(f"   📊 Notificación de trade: Cerrado={trade.isclosed}, P&L={trade.pnlcomm:.2f}")
            print(f"   📊 Trade info: Size={trade.size}, Price={trade.price:.5f}")
            print(f"   ⏳ Trade aún abierto, esperando cierre...")
            return
        
        # Calcular métricas del trade
        pnl = trade.pnl
        pnlcomm = trade.pnlcomm
        roi = (pnlcomm / trade.price) * 100 if trade.price > 0 else 0
        
        # Determinar el tipo de cierre
        current_price = self.data.close[0]
        direction = 'LONG' if trade.size > 0 else 'SHORT'
        
        # Verificar si fue Stop Loss o Take Profit
        close_type = "MANUAL"
        if self.current_position_info:
            stop_loss = self.current_position_info['stop_loss']
            take_profit = self.current_position_info.get('take_profit')  # TP ESTRUCTURAL ÚNICO
            
            if direction == 'LONG':
                if current_price <= stop_loss:
                    close_type = "STOP LOSS"
                elif take_profit and current_price >= take_profit:
                    close_type = "TAKE PROFIT ESTRUCTURAL"
            else:  # SHORT
                if current_price >= stop_loss:
                    close_type = "STOP LOSS"
                elif take_profit and current_price <= take_profit:
                    close_type = "TAKE PROFIT ESTRUCTURAL"
        
        # Mostrar información simplificada del trade
        result = "GANADORA" if pnlcomm > 0 else "PERDEDORA"
        self.log(f'📊 TRADE CERRADO - {close_type} - {result} - P&L: {pnlcomm:.2f}')
        
        # Actualizar el último trade en el CSV con información de cierre
        if self.trades_csv_data:
            last_trade = self.trades_csv_data[-1]
            # Calcular duración en minutos
            entry_time = pd.to_datetime(f"{last_trade[0]} {last_trade[1]}")
            close_time = current_time
            duration_minutes = int((close_time - entry_time).total_seconds() / 60)
            
            # Actualizar campos de cierre
            last_trade[9] = current_price      # Precio cierre
            last_trade[10] = close_time.strftime("%Y-%m-%d")  # Fecha cierre
            last_trade[11] = close_time.strftime("%H:%M:%S")  # Hora cierre
            last_trade[12] = result            # Resultado
            last_trade[13] = pnl               # P&L Bruto
            last_trade[14] = pnlcomm           # P&L Neto
            last_trade[15] = roi               # ROI %
            last_trade[16] = close_type        # Tipo cierre
            last_trade[17] = duration_minutes  # Duración minutos
            last_trade[18] = self.trailing_stop_breakeven  # Trailing Stop Breakeven
            last_trade[19] = self.trailing_stop_profit     # Trailing Stop Profit
        
        # MOSTRAR INFORMACIÓN DETALLADA DEL CIERRE DE TRADE
        print(f"   📊 INFORMACIÓN DETALLADA DEL CIERRE:")
        print(f"   " + "="*50)
        print(f"   🎯 DIRECCIÓN: {direction}")
        print(f"   💰 PRECIO DE ENTRADA: {trade.price:.5f}")
        print(f"   💰 PRECIO DE CIERRE: {current_price:.5f}")
        print(f"   📊 TIPO DE CIERRE: {close_type}")
        print(f"   💰 P&L BRUTO: {pnl:.2f}")
        print(f"   💰 P&L NETO (con comisiones): {pnlcomm:.2f}")
        print(f"   📈 ROI: {roi:.2f}%")
        print(f"   📅 FECHA/HORA CIERRE: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if pnlcomm > 0:
            print(f"   🎉 GANANCIA: +{pnlcomm:.2f}")
        else:
            print(f"   📉 PÉRDIDA: {pnlcomm:.2f}")
        print(f"   " + "="*50)
        
        # Actualizar contadores
        self.trade_count += 1
        if pnlcomm > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        # Almacenar información del trade
        trade_info = {
            'entry_date': self.data.datetime.date(0).isoformat(),
            'exit_date': self.data.datetime.date(0).isoformat(),
            'entry_price': trade.price,
            'exit_price': trade.price,
            'size': trade.size,
            'pnl': pnl,
            'pnl_net': pnlcomm,
            'roi': roi,
            'commission': trade.commission,
            'direction': direction,
            'close_type': close_type
        }
        self.trades.append(trade_info)
    
    def start(self):
        """Método llamado al inicio del backtesting"""
        # Usar la cantidad de velas especificada
        self.total_bars = self.cantidad_velas
        
        print(f"🚀 Estrategia ICC SmartMoney iniciada")
        print(f"   📊 Total de velas a procesar: {self.total_bars}")
        print(f"   🎯 Buscando señales ICC en los datos...")
    
    def stop(self):
        """Método llamado al final del backtesting"""
        # Cerrar cualquier posición abierta al final del backtesting
        if self.position:
            self.log(f'🔚 Cerrando posición abierta al final del backtesting')
            self.log(f'   📊 Posición actual: Size={self.position.size}, Price={self.position.price:.5f}')
            
            # Calcular P&L de la posición abierta
            current_price = self.data.close[0]
            if self.position.size > 0:  # LONG
                pnl = (current_price - self.position.price) * self.position.size
            else:  # SHORT
                pnl = (self.position.price - current_price) * abs(self.position.size)
            
            # Contar como trade cerrado manualmente
            self.trade_count += 1
            if pnl > 0:
                self.win_count += 1
                result = "GANADORA"
            else:
                self.loss_count += 1
                result = "PERDEDORA"
            
            self.log(f'📊 TRADE CERRADO - CIERRE MANUAL - {result} - P&L: {pnl:.2f}')
            
            # MOSTRAR INFORMACIÓN DEL CIERRE MANUAL AL FINAL DEL BACKTESTING
            print(f"   📊 INFORMACIÓN DEL CIERRE MANUAL:")
            print(f"   " + "="*50)
            print(f"   🎯 DIRECCIÓN: {'LONG' if self.position.size > 0 else 'SHORT'}")
            print(f"   💰 PRECIO DE ENTRADA: {self.position.price:.5f}")
            print(f"   💰 PRECIO DE CIERRE: {current_price:.5f}")
            print(f"   📊 TIPO DE CIERRE: CIERRE MANUAL (Final del backtesting)")
            print(f"   💰 P&L: {pnl:.2f}")
            print(f"   📅 FECHA/HORA CIERRE: {self.data.datetime.datetime(0)}")
            print(f"   " + "="*50)
            
            self.close()
            
        # Limpiar información de gestión de riesgo
        self.current_position_info = None
        
        # Resumen de operaciones ejecutadas
        print(f"   📊 RESUMEN DE OPERACIONES EJECUTADAS:")
        print(f"      • Total de operaciones: {self.trade_count}")
        print(f"      • Operaciones ganadoras: {self.win_count}")
        print(f"      • Operaciones perdedoras: {self.loss_count}")
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            print(f"      • Tasa de éxito: {win_rate:.1f}%")
        
        print(f"   📊 Contador de trades al final: {self.trade_count}")
        
        # Guardar CSV de trades
        self.save_trades_csv()
        
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            self.log(f'🏁 BACKTESTING COMPLETADO - {self.trade_count} operaciones - {win_rate:.1f}% éxito')
            print(f"   📊 RESUMEN DE OPERACIONES:")
            print(f"      • Total de operaciones: {self.trade_count}")
            print(f"      • Operaciones ganadoras: {self.win_count}")
            print(f"      • Operaciones perdedoras: {self.loss_count}")
            print(f"      • Tasa de éxito: {win_rate:.1f}%")
            
            # Mostrar resumen de señales ICC
            if hasattr(self, 'smartmoney_icc') and hasattr(self.smartmoney_icc, 'signals'):
                total_signals = len(self.smartmoney_icc.signals) if self.smartmoney_icc.signals else 0
                print(f"   📊 RESUMEN DE SEÑALES ICC:")
                print(f"      • Total de señales detectadas: {total_signals}")
                if total_signals > 0:
                    long_signals = len([s for s in self.smartmoney_icc.signals if s['direction'] == 'LONG'])
                    short_signals = len([s for s in self.smartmoney_icc.signals if s['direction'] == 'SHORT'])
                    print(f"      • Señales LONG: {long_signals}")
                    print(f"      • Señales SHORT: {short_signals}")
        else:
            self.log(f'🏁 BACKTESTING COMPLETADO - Sin operaciones')
            print(f"   📊 RESUMEN: No se ejecutaron operaciones")
            print(f"      • Posibles causas:")
            print(f"         - Las señales no cumplieron el R:R mínimo")
            print(f"         - No se detectaron señales ICC válidas")
            print(f"         - Las órdenes no se ejecutaron correctamente")

def load_data():
    """Cargar datos de EURUSD de múltiples timeframes como en smart01.py"""
    try:
        # Cargar datos de 5M (timeframe principal)
        csv_path_5m = "test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
        
        if not os.path.exists(csv_path_5m):
            print(f"❌ Error: No se encontró el archivo {csv_path_5m}")
            return None, None, None
        
        print(f"📂 Leyendo archivo 5M: {csv_path_5m}")
        
        # Leer el CSV de 5M
        df_5m = pd.read_csv(csv_path_5m, index_col="datetime")
        
        print(f"✅ Archivo 5M leído exitosamente")
        print(f"   📊 Filas originales: {len(df_5m)}")
        
        # Convertir todas las columnas a float
        print(f"🔄 Convirtiendo tipos de datos...")
        df_5m = df_5m.astype(float)
        
        # Asegurar que las columnas estén en el orden correcto
        df_5m = df_5m[["open", "high", "low", "close", "volume"]]
        
        # Convertir el índice a datetime primero
        print(f"🔄 Procesando fechas...")
        print(f"   📊 Tipo de índice antes: {type(df_5m.index)}")
        print(f"   📊 Primeros valores del índice: {df_5m.index[:3].tolist()}")
        
        # Convertir a datetime primero
        df_5m.index = pd.to_datetime(df_5m.index)
        print(f"   📊 Tipo de índice después de to_datetime: {type(df_5m.index)}")
        
        # Tomar solo las últimas 1500 velas para el test
        df_5m = df_5m.tail(cantidad_velas)
        
        # Crear timeframes superiores desde los datos 5M reales (necesita DatetimeIndex)
        print(f"🔄 Creando timeframes superiores...")
        
        # H1 (1 hora) - agregar cada 12 velas de 5M
        df_1h = df_5m.resample('1H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # H4 (4 horas) - agregar cada 48 velas de 5M
        df_4h = df_5m.resample('4H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # IMPORTANTE: Mantener el índice como datetime para Backtrader
        # Solo convertiremos a string cuando sea necesario para la estrategia ICC
        print(f"🔄 Manteniendo índices como datetime para Backtrader...")
        
        print(f"   📊 Tipo de índice final: {type(df_5m.index)}")
        print(f"   📊 Primeros valores del índice: {df_5m.index[:3].tolist()}")
        
        print(f"   📊 Filas después de filtrado:")
        print(f"      • 5M: {len(df_5m)} velas")
        print(f"      • 1H: {len(df_1h)} velas")
        print(f"      • 4H: {len(df_4h)} velas")
        print(f"   📅 Rango de fechas: {df_5m.index.min()} a {df_5m.index.max()}")
        print(f"   📈 Precio más alto: {df_5m['high'].max():.5f}")
        print(f"   📉 Precio más bajo: {df_5m['low'].min():.5f}")
        
        # Verificar que tenemos datos válidos
        if len(df_5m) == 0:
            print(f"❌ Error: No hay datos después del filtrado")
            return None, None, None
        
        if df_5m.isnull().any().any():
            print(f"⚠️ Advertencia: Se encontraron valores nulos en los datos")
            df_5m = df_5m.dropna()
            print(f"   📊 Filas después de limpiar nulos: {len(df_5m)}")
        
        print(f"✅ Datos cargados exitosamente para backtesting")
        return df_5m, df_1h, df_4h
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None, None, None

def run_backtest():
    """Ejecutar el backtesting completo"""
    try:

        # Cargar datos de múltiples timeframes
        df_5m, df_1h, df_4h = load_data()
        if df_5m is None:
            print(f"❌ Error: No se pudieron cargar los datos")
            return
        
        print(f"📊 Datos cargados para backtesting:")
        print(f"   📈 Forma del DataFrame 5M: {df_5m.shape}")
        print(f"   📈 Forma del DataFrame 1H: {df_1h.shape}")
        print(f"   📈 Forma del DataFrame 4H: {df_4h.shape}")
        print(f"   📅 Columnas: {list(df_5m.columns)}")
        print(f"   📊 Tipos de datos: {df_5m.dtypes.to_dict()}")
        print(f"   🔍 Primeras 3 filas 5M:")
        print(df_5m.head(3))
        print(f"   🔍 Últimas 3 filas 5M:")
        print(df_5m.tail(3))
        
        # Crear el cerebro de Backtrader
        cerebro = bt.Cerebro()
        
        # Configurar parámetros
        cerebro.broker.setcash(100000.0)  # Capital inicial $100,000
        cerebro.broker.setcommission(commission=0.001)  # Comisión 0.1%
        
        # Agregar datos 5M (timeframe principal)
        data_feed = bt.feeds.PandasData(
            dataname=df_5m,
            datetime=None,  # Usar el índice como datetime
            open=0,
            high=1,
            low=2,
            close=3,
            volume=4,
            openinterest=-1
        )
        cerebro.adddata(data_feed)
        
        # Agregar estrategia con datos de múltiples timeframes
        cerebro.addstrategy(ICCStrategy, df_5m=df_5m, df_1h=df_1h, df_4h=df_4h, cantidad_velas=cantidad_velas)
        
        # Configurar plotting para mostrar señales automáticamente
        cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.0025)
        
        # Agregar analizadores
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        print(f"🚀 Iniciando simulación de backtesting...")
        print(f"   📊 Total de velas a procesar: {len(df_5m)}")
        print(f"   💰 Capital inicial: $100,000")
        print(f"   📈 Comisión: 0.1%")
        
        start_time = time.time()
        print(f"   ⏳ Ejecutando cerebro.run()...")
        try:
            results = cerebro.run()
            end_time = time.time()
            print(f"   ✅ Simulación completada en {end_time - start_time:.2f} segundos")
        except Exception as e:
            end_time = time.time()
            print(f"   ❌ Error durante la simulación: {e}")
            print(f"   ⏱️ Tiempo transcurrido: {end_time - start_time:.2f} segundos")
            import traceback
            traceback.print_exc()
            return None
        
        strategy = results[0]
        

        
        # Capital final
        final_value = cerebro.broker.getvalue()
        initial_value = 100000.0
        total_return = ((final_value - initial_value) / initial_value) * 100
        
        # Mostrar resultados
        print(f"\n📊 RESULTADOS DEL BACKTESTING:")
        print(f"   💰 Capital inicial: ${initial_value:,.2f}")
        print(f"   💰 Capital final: ${final_value:,.2f}")
        print(f"   📈 Retorno total: {total_return:.2f}%")
        print(f"   ⏱️ Tiempo de ejecución: {end_time - start_time:.2f} segundos")
        
        # Mostrar analizadores si están disponibles
        try:
            if hasattr(strategy, 'analyzers'):
                # Ratio de Sharpe
                if hasattr(strategy.analyzers.sharpe, 'get_analysis'):
                    sharpe_ratio = strategy.analyzers.sharpe.get_analysis()
                    if sharpe_ratio and 'sharperatio' in sharpe_ratio and sharpe_ratio['sharperatio'] is not None:
                        print(f"   📊 Ratio de Sharpe: {sharpe_ratio['sharperatio']:.3f}")
                    else:
                        print(f"   📊 Ratio de Sharpe: No disponible")
                
                # Máximo Drawdown
                if hasattr(strategy.analyzers.drawdown, 'get_analysis'):
                    drawdown = strategy.analyzers.drawdown.get_analysis()
                    if drawdown and 'max' in drawdown and 'drawdown' in drawdown['max'] and drawdown['max']['drawdown'] is not None:
                        print(f"   📉 Máximo Drawdown: {drawdown['max']['drawdown']:.2f}%")
                    else:
                        print(f"   📉 Máximo Drawdown: No disponible")
                
                # Retorno total
                if hasattr(strategy.analyzers.returns, 'get_analysis'):
                    returns = strategy.analyzers.returns.get_analysis()
                    if returns and 'rtot' in returns and returns['rtot'] is not None:
                        print(f"   📈 Retorno total: {returns['rtot']:.2f}%")
                    else:
                        print(f"   📈 Retorno total: No disponible")
                
                # Análisis de trades
                if hasattr(strategy.analyzers.trades, 'get_analysis'):
                    trades_analysis = strategy.analyzers.trades.get_analysis()
                    if trades_analysis:
                        total_trades = trades_analysis.get('total', {}).get('total', 0)
                        won_trades = trades_analysis.get('won', {}).get('total', 0)
                        lost_trades = trades_analysis.get('lost', {}).get('total', 0)
                        print(f"   📊 Análisis de trades:")
                        print(f"      • Total de trades: {total_trades}")
                        print(f"      • Trades ganadores: {won_trades}")
                        print(f"      • Trades perdedores: {lost_trades}")
                        if total_trades > 0:
                            win_rate = (won_trades / total_trades) * 100
                            print(f"      • Tasa de éxito: {win_rate:.1f}%")
        except Exception as e:
            print(f"   ⚠️ Error mostrando analizadores: {e}")
            print(f"   📊 Los analizadores pueden no estar disponibles para este período de datos")
        
        # Generar gráfico
        try:
            print(f"\n📈 Generando gráfico del backtesting...")
            cerebro.plot(style='candlestick', barup='green', bardown='red', volume=False, figsize=(15, 10))
            print(f"   ✅ Gráfico generado exitosamente")
        except Exception as e:
            print(f"   ❌ Error generando gráfico: {e}")
            print(f"   🔧 Intentando generar gráfico básico...")
            try:
                cerebro.plot()
                print(f"   ✅ Gráfico básico generado exitosamente")
            except Exception as e2:
                print(f"   ❌ Error generando gráfico básico: {e2}")
        
        return strategy
        
    except Exception as e:
        return None

if __name__ == '__main__':
    """Función principal"""
    try:
        print("🚀 Iniciando backtesting ICC SmartMoney...")
        strategy = run_backtest()
        print("✅ Backtesting completado exitosamente")
        
    except KeyboardInterrupt:
        print("⏹️ Backtesting interrumpido por el usuario")
    except Exception as e:
        print(f"❌ Error ejecutando backtesting: {e}")
        import traceback
        traceback.print_exc()