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

# Importar la estrategia ICC real
from estrategia.icc import ICCStrategy as SmartMoneyICCStrategy

class ICCStrategy(bt.Strategy):
    """Estrategia ICC SmartMoney con Backtrader"""
    
    def __init__(self):
        # Indicadores técnicos básicos para Backtrader
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        
        # Variable para órdenes pendientes
        self.order = None
        
        # Contadores de operaciones
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Lista para almacenar resultados de operaciones
        self.trades = []
        
        # Inicializar la estrategia SmartMoney ICC
        self.smartmoney_icc = SmartMoneyICCStrategy(
            risk_reward_min=1.0,  # R:R mínimo 1:1
            ob_lookback=50,
            fvg_lookback=30,
            swing_length=20
        )
        
        # Almacenar datos para análisis SmartMoney
        self.data_buffer = []
        self.last_analysis_time = None
        
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
        
    def log(self, txt, dt=None):
        """Función de logging"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
        
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
                
                # Crear timeframes superiores (simplificado para demo)
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
                

                try:
                    signals = self.smartmoney_icc.scan_for_icc_signals(df_5m, df_1h, df_4h)

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
                        take_profit = risk_management.get('take_profit')
                        risk_reward_ratio = risk_management.get('risk_reward_ratio', 0)
                        
                        # Obtener niveles de TP estructurales
                        tp_levels = risk_management.get('tp_levels', {})
                        tp1 = tp_levels.get('tp1')  # R:R 1:1
                        tp2 = tp_levels.get('tp2')  # R:R 1:2  
                        tp3 = tp_levels.get('tp3')  # R:R 1:3
                        structural_levels = tp_levels.get('structural_levels', [])
                        
                        # Almacenar información de la posición para gestión de riesgo
                        self.current_position_info = {
                            'direction': direction,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': tp1,  # Usar TP1 (1:1) como TP principal
                            'risk_reward_ratio': risk_reward_ratio,
                            'tp_levels': {
                                'tp1': tp1,
                                'tp2': tp2,
                                'tp3': tp3,
                                'structural_levels': structural_levels
                            }
                        }
                        
                        # Ejecutar orden según dirección
                        print(f"   🚀 EJECUTANDO ORDEN: {direction}")
                        if direction == 'LONG':
                            print(f"   📈 ENVIANDO ORDEN DE COMPRA...")
                            self.order = self.buy()
                        elif direction == 'SHORT':
                            print(f"   📉 ENVIANDO ORDEN DE VENTA...")
                            self.order = self.sell()
                        
                        print(f"   ✅ ORDEN ENVIADA: {self.order}")
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
        """Verificar Stop Loss y Take Profit basado en gestión de riesgo ICC"""
        if not self.current_position_info:
            return
            
        current_price = self.data.close[0]
        direction = self.current_position_info['direction']
        entry_price = self.current_position_info['entry_price']
        stop_loss = self.current_position_info['stop_loss']
        tp_levels = self.current_position_info.get('tp_levels', {})
        
        # Obtener Take Profit estructural
        take_profit = self.current_position_info.get('take_profit')
        rr_ratio = self.current_position_info.get('risk_reward_ratio', 0)
        
        if direction == 'LONG':
            # Verificar Stop Loss (precio por debajo del SL)
            if current_price <= stop_loss:
                self.log(f"🛑 STOP LOSS alcanzado - Precio: {current_price:.5f}, SL: {stop_loss:.5f}")
                self.close()
                self.current_position_info = None
                return
                
            # Verificar Take Profit estructural
            if take_profit and current_price >= take_profit:
                self.log(f"🎯 TAKE PROFIT ESTRUCTURAL alcanzado - Precio: {current_price:.5f}, TP: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})")
                self.close()
                self.current_position_info = None
                return
                
        elif direction == 'SHORT':
            # Verificar Stop Loss (precio por encima del SL)
            if current_price >= stop_loss:
                self.log(f"🛑 STOP LOSS alcanzado - Precio: {current_price:.5f}, SL: {stop_loss:.5f}")
                self.close()
                self.current_position_info = None
                return
                
            # Verificar Take Profit estructural
            if take_profit and current_price <= take_profit:
                self.log(f"🎯 TAKE PROFIT ESTRUCTURAL alcanzado - Precio: {current_price:.5f}, TP: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})")
                self.close()
                self.current_position_info = None
                return
    
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
            if order.isbuy():
                # Mostrar información de gestión de riesgo para compras
                if self.current_position_info and self.current_position_info['direction'] == 'LONG':
                    stop_loss = self.current_position_info['stop_loss']
                    take_profit = self.current_position_info['take_profit']
                    rr_ratio = self.current_position_info.get('risk_reward_ratio', 0)
                    
                    self.log(f'🟢 COMPRA EJECUTADA - Precio: {order.executed.price:.5f}')
                    self.log(f'   💰 Costo: {order.executed.value:.2f}, Comisión: {order.executed.comm:.2f}')
                    self.log(f'   🛑 Stop Loss: {stop_loss:.5f}')
                    self.log(f'   🎯 Take Profit Estructural: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})')
                else:
                    self.log(f'🟢 COMPRA EJECUTADA - Precio: {order.executed.price:.5f}')
            else:
                # Mostrar información de gestión de riesgo para ventas
                if self.current_position_info and self.current_position_info['direction'] == 'SHORT':
                    stop_loss = self.current_position_info['stop_loss']
                    take_profit = self.current_position_info['take_profit']
                    rr_ratio = self.current_position_info.get('risk_reward_ratio', 0)
                    
                    self.log(f'🔴 VENTA EJECUTADA - Precio: {order.executed.price:.5f}')
                    self.log(f'   💰 Costo: {order.executed.value:.2f}, Comisión: {order.executed.comm:.2f}')
                    self.log(f'   🛑 Stop Loss: {stop_loss:.5f}')
                    self.log(f'   🎯 Take Profit Estructural: {take_profit:.5f} (R:R 1:{rr_ratio:.2f})')
                else:
                    self.log(f'🔴 VENTA EJECUTADA - Precio: {order.executed.price:.5f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Orden Cancelada/Margin/Rechazada')
        
        self.order = None
    
    def notify_trade(self, trade):
        """Notificar cambios en trades"""
        print(f"   📊 Notificación de trade: Cerrado={trade.isclosed}, P&L={trade.pnlcomm:.2f}")
        print(f"   📊 Trade info: Size={trade.size}, Price={trade.price:.5f}")
        
        if not trade.isclosed:
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
            tp_levels = self.current_position_info.get('tp_levels', {})
            tp1 = tp_levels.get('tp1')
            tp2 = tp_levels.get('tp2')
            tp3 = tp_levels.get('tp3')
            
            if direction == 'LONG':
                if current_price <= stop_loss:
                    close_type = "STOP LOSS"
                elif tp3 and current_price >= tp3:
                    close_type = "TAKE PROFIT 1:3"
                elif tp2 and current_price >= tp2:
                    close_type = "TAKE PROFIT 1:2"
                elif tp1 and current_price >= tp1:
                    close_type = "TAKE PROFIT 1:1"
            else:  # SHORT
                if current_price >= stop_loss:
                    close_type = "STOP LOSS"
                elif tp3 and current_price <= tp3:
                    close_type = "TAKE PROFIT 1:3"
                elif tp2 and current_price <= tp2:
                    close_type = "TAKE PROFIT 1:2"
                elif tp1 and current_price <= tp1:
                    close_type = "TAKE PROFIT 1:1"
        
        # Mostrar información simplificada del trade
        result = "GANADORA" if pnlcomm > 0 else "PERDEDORA"
        self.log(f'📊 TRADE CERRADO - {close_type} - {result} - P&L: {pnlcomm:.2f}')
        
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
        # Inicializar el total de barras cuando los datos estén disponibles
        self.total_bars = len(self.data)
        print(f"   📊 Total de velas a procesar: {self.total_bars}")
    
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
            
            self.close()
            
        # Limpiar información de gestión de riesgo
        self.current_position_info = None
        
        print(f"   📊 Contador de trades al final: {self.trade_count}")
        
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
    """Cargar datos de EURUSD como en smart01.py"""
    try:
        # Usar el archivo CSV de datos de EURUSD
        csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
        
        if not os.path.exists(csv_path):
            print(f"❌ Error: No se encontró el archivo {csv_path}")
            return None
        
        print(f"📂 Leyendo archivo: {csv_path}")
        
        # Leer el CSV como en smart01.py
        df = pd.read_csv(csv_path, index_col="datetime")
        
        print(f"✅ Archivo leído exitosamente")
        print(f"   📊 Filas originales: {len(df)}")
        
        # Convertir todas las columnas a float
        print(f"🔄 Convirtiendo tipos de datos...")
        df = df.astype(float)
        
        # Asegurar que las columnas estén en el orden correcto
        df = df[["open", "high", "low", "close", "volume"]]
        
        # Convertir el índice a datetime
        print(f"🔄 Procesando fechas...")
        df.index = pd.to_datetime(df.index)
        
        # Tomar solo las últimas 500 velas para el test
        df = df.tail(1500)
        


        
        return df
        
    except Exception as e:
        return None

def run_backtest():
    """Ejecutar el backtesting completo"""
    try:

        data = load_data()
        if data is None:
            return
        
        # Crear el cerebro de Backtrader
        cerebro = bt.Cerebro()
        
        # Configurar parámetros
        cerebro.broker.setcash(100000.0)  # Capital inicial $100,000
        cerebro.broker.setcommission(commission=0.001)  # Comisión 0.1%
        
        # Agregar datos
        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Usar el índice como datetime
            open=0,
            high=1,
            low=2,
            close=3,
            volume=4,
            openinterest=-1
        )
        cerebro.adddata(data_feed)
        
        # Agregar estrategia
        cerebro.addstrategy(ICCStrategy)
        
        # Configurar plotting para mostrar señales automáticamente
        cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.0025)
        
        # Agregar analizadores
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        

        
        start_time = time.time()
        results = cerebro.run()
        end_time = time.time()
        
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
            cerebro.plot(style='candlestick', barup='green', bardown='red', 
                        volume=False, figsize=(15, 10))
            print(f"   ✅ Gráfico generado exitosamente")
        except Exception as e:
            print(f"   ❌ Error generando gráfico: {e}")
        
        return strategy
        
    except Exception as e:
        return None

if __name__ == '__main__':
    """Función principal"""
    try:
        strategy = run_backtest()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass