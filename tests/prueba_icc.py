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
        
        print(f"🚀 Estrategia ICC SmartMoney inicializada")
        
    def log(self, txt, dt=None):
        """Función de logging"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
        
    def next(self):
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
        
        # Analizar con SmartMoney ICC cada 20 velas
        if len(self.data) % 20 == 0 and len(self.data_buffer) >= 100:
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
                
                # Escanear señales SmartMoney ICC (sin logging)
                # Redirigir stdout temporalmente para suprimir mensajes internos
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                
                try:
                    signals = self.smartmoney_icc.scan_for_icc_signals(df_5m, df_1h, df_4h)
                finally:
                    sys.stdout = old_stdout
                
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
                        
                        # Mostrar señal SmartMoney
                        self.log(f"🎯 SEÑAL SMARTMONEY: {direction} - Precio: {entry_price:.5f}")
                        
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
                        if direction == 'LONG':
                            self.buy()
                        elif direction == 'SHORT':
                            self.sell()                        
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
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
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
        if not trade.isclosed:
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
    
    def stop(self):
        """Método llamado al final del backtesting"""
        # Cerrar cualquier posición abierta al final del backtesting
        if self.position:
            self.log(f'🔚 Cerrando posición abierta al final del backtesting')
            self.close()
            
        # Limpiar información de gestión de riesgo
        self.current_position_info = None
        
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            self.log(f'🏁 BACKTESTING COMPLETADO - {self.trade_count} operaciones - {win_rate:.1f}% éxito')
        else:
            self.log(f'🏁 BACKTESTING COMPLETADO - Sin operaciones')

def load_data():
    """Cargar datos de EURUSD como en smart01.py"""
    try:
        # Usar el archivo CSV de datos de EURUSD
        csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
        
        if not os.path.exists(csv_path):
            print(f"❌ Error: No se encontró el archivo {csv_path}")
            return None
        
        # Leer el CSV como en smart01.py
        df = pd.read_csv(csv_path, index_col="datetime")
        
        # Convertir todas las columnas a float
        df = df.astype(float)
        
        # Asegurar que las columnas estén en el orden correcto
        df = df[["open", "high", "low", "close", "volume"]]
        
        # Convertir el índice a datetime
        df.index = pd.to_datetime(df.index)
        
        # Tomar solo las últimas 500 velas para el test
        # df = df.tail(500)
        
        print(f"📊 Datos cargados desde: {csv_path}")
        print(f"   📈 Total de velas: {len(df)}")
        print(f"   📅 Rango: {df.index[0]} a {df.index[-1]}")
        print(f"   💰 Precio actual: {df['close'].iloc[-1]:.5f}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None

def run_backtest():
    """Ejecutar el backtesting completo"""
    try:
        print("🚀 INICIANDO BACKTESTING ICC SMARTMONEY")
        print("=" * 60)
        
        # Cargar datos
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
        
        print(f"📊 Configuración del backtesting:")
        print(f"   💰 Capital inicial: $100,000")
        print(f"   💸 Comisión: 0.1%")
        print(f"   📈 Datos: {len(data)} velas de EURUSD 5M")
        print(f"   🎯 Estrategia: ICC SmartMoney con Order Blocks, FVG y múltiples timeframes")
        print("=" * 60)
        
        # Ejecutar backtesting
        print("🔄 Ejecutando backtesting...")
        results = cerebro.run()
        strategy = results[0]
        
        # Mostrar resultados
        print("\n" + "=" * 60)
        print("📊 RESULTADOS DEL BACKTESTING")
        print("=" * 60)
        
        # Capital final
        final_value = cerebro.broker.getvalue()
        initial_value = 100000.0
        total_return = ((final_value - initial_value) / initial_value) * 100
        
        print(f"💰 RESULTADOS FINANCIEROS:")
        print(f"   💵 Capital inicial: ${initial_value:,.2f}")
        print(f"   💵 Capital final: ${final_value:,.2f}")
        print(f"   📈 Retorno total: {total_return:+.2f}%")
        print(f"   💰 Ganancia/Pérdida: ${final_value - initial_value:+,.2f}")
        
        # Métricas de rendimiento
        print(f"\n📊 MÉTRICAS DE RENDIMIENTO:")
        
        # Sharpe Ratio
        sharpe_ratio = strategy.analyzers.sharpe.get_analysis()
        if 'sharperatio' in sharpe_ratio and sharpe_ratio['sharperatio'] is not None:
            print(f"   📈 Sharpe Ratio: {sharpe_ratio['sharperatio']:.3f}")
        else:
            print(f"   📈 Sharpe Ratio: N/A")
        
        # Drawdown
        drawdown = strategy.analyzers.drawdown.get_analysis()
        if 'max' in drawdown:
            print(f"   📉 Máximo Drawdown: {drawdown['max']['drawdown']:.2f}%")
        else:
            print(f"   📉 Máximo Drawdown: N/A")
        
        # Retornos
        returns = strategy.analyzers.returns.get_analysis()
        if 'rtot' in returns:
            print(f"   📊 Retorno total: {returns['rtot']:.2f}%")
        if 'rnorm100' in returns:
            print(f"   📊 Retorno normalizado: {returns['rnorm100']:.2f}%")
        
        # Análisis de trades
        trades_analysis = strategy.analyzers.trades.get_analysis()
        try:
            if 'total' in trades_analysis and trades_analysis['total']['total'] > 0:
                print(f"\n🎯 ANÁLISIS DE OPERACIONES:")
                print(f"   📊 Total de operaciones: {trades_analysis['total']['total']}")
                print(f"   ✅ Operaciones ganadoras: {trades_analysis['won']['total']}")
                print(f"   ❌ Operaciones perdedoras: {trades_analysis['lost']['total']}")
                
                win_rate = (trades_analysis['won']['total'] / trades_analysis['total']['total']) * 100
                print(f"   📈 Tasa de éxito: {win_rate:.2f}%")
        except (KeyError, TypeError) as e:
            print(f"\n🎯 ANÁLISIS DE OPERACIONES:")
            print(f"   📊 Total de operaciones: {strategy.trade_count}")
            print(f"   ✅ Operaciones ganadoras: {strategy.win_count}")
            print(f"   ❌ Operaciones perdedoras: {strategy.loss_count}")
            
            if strategy.trade_count > 0:
                win_rate = (strategy.win_count / strategy.trade_count) * 100
                print(f"   📈 Tasa de éxito: {win_rate:.2f}%")
        
        print("\n" + "=" * 60)
        print("✅ BACKTESTING COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        
        # Opción para mostrar gráfico
        show_chart = input("\n¿Deseas mostrar el gráfico del backtesting? (s/n): ").lower()
        if show_chart in ['s', 'si', 'y', 'yes']:
            print("📊 Generando gráfico...")
            # Usar la misma configuración que pruebas.py
            cerebro.plot()
        
        return strategy
        
    except Exception as e:
        print(f"❌ Error en el backtesting: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    """Función principal"""
    try:
        print("🎯 PRUEBA ICC SMARTMONEY CON BACKTRADER")
        print("=" * 50)
        print("Este script implementa la estrategia ICC SmartMoney usando Backtrader")
        print("con datos de EURUSD, integrando Order Blocks, Fair Value Gaps y análisis de múltiples timeframes")
        print("=" * 50)
        
        # Ejecutar backtesting
        strategy = run_backtest()
        
        if strategy:
            print(f"\n🎉 ¡Backtesting completado exitosamente!")
            print(f"   📊 Revisa los resultados arriba para evaluar el rendimiento")
            print(f"   💡 Las señales de compra y venta se mostrarán en el gráfico")
        else:
            print(f"\n❌ El backtesting falló. Revisa los errores arriba.")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Backtesting interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()