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
        
        print(f"🚀 Estrategia ICC SmartMoney inicializada")
        print(f"   📊 RSI: {self.rsi.params.period}")
        print(f"   📊 MACD: 12, 26, 9")
        print(f"   🧠 SmartMoney ICC: R:R mínimo 1:{self.smartmoney_icc.risk_reward_min}")
        
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
            # Lógica de salida SmartMoney ICC
            if self.position.size > 0:  # Posición larga
                # Salir si RSI está sobrecomprado o MACD cruza hacia abajo
                if self.rsi[0] > 75 or self.macd.macd[0] < self.macd.signal[0]:
                    self.log(f"🎯 Cerrando posición larga - RSI: {self.rsi[0]:.2f}, MACD: {self.macd.macd[0]:.5f}")
                    self.close()
            else:  # Posición corta
                # Salir si RSI está sobrevendido o MACD cruza hacia arriba
                if self.rsi[0] < 25 or self.macd.macd[0] > self.macd.signal[0]:
                    self.log(f"🎯 Cerrando posición corta - RSI: {self.rsi[0]:.2f}, MACD: {self.macd.macd[0]:.5f}")
                    self.close()
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
                
                # Escanear señales SmartMoney ICC
                self.log(f"🔍 Analizando SmartMoney ICC en vela {len(self.data)}")
                signals = self.smartmoney_icc.scan_for_icc_signals(df_5m, df_1h, df_4h)
                
                if signals:
                    # Procesar señales SmartMoney
                    for signal in signals:
                        direction = signal['direction']
                        entry_price = signal['entry_price']
                        
                        self.log(f"🎯 SEÑAL SMARTMONEY ICC: {direction}")
                        self.log(f"   📊 Precio entrada: {entry_price:.5f}")
                        self.log(f"   📈 RSI actual: {self.rsi[0]:.2f}")
                        self.log(f"   📊 MACD actual: {self.macd.macd[0]:.5f}")
                        
                        # Ejecutar orden según dirección
                        if direction == 'LONG':
                            self.buy()
                        elif direction == 'SHORT':
                            self.sell()
                        
                        # Solo procesar la primera señal
                        break
                else:
                    # Fallback a lógica simple si no hay señales SmartMoney
                    self.log(f"📊 No hay señales SmartMoney, usando lógica de respaldo")
                    
                    # Condiciones de compra de respaldo
                    if (self.rsi[0] < 60 and 
                        self.macd.macd[0] > self.macd.signal[0] and 
                        self.data.close[0] > self.data.close[-5]):
                        
                        self.log(f"🎯 SEÑAL COMPRA (RESPALDO) en vela {len(self.data)}")
                        self.buy()
                        
                    # Condiciones de venta de respaldo
                    elif (self.rsi[0] > 40 and 
                          self.macd.macd[0] < self.macd.signal[0] and 
                          self.data.close[0] < self.data.close[-5]):
                        
                        self.log(f"🎯 SEÑAL VENTA (RESPALDO) en vela {len(self.data)}")
                        self.sell()
                        
            except Exception as e:
                self.log(f"❌ Error en análisis SmartMoney: {e}")
                # Usar lógica de respaldo en caso de error
                if (self.rsi[0] < 60 and 
                    self.macd.macd[0] > self.macd.signal[0] and 
                    self.data.close[0] > self.data.close[-5]):
                    self.log(f"🎯 SEÑAL COMPRA (ERROR) en vela {len(self.data)}")
                    self.buy()
                elif (self.rsi[0] > 40 and 
                      self.macd.macd[0] < self.macd.signal[0] and 
                      self.data.close[0] < self.data.close[-5]):
                    self.log(f"🎯 SEÑAL VENTA (ERROR) en vela {len(self.data)}")
                    self.sell()
    
    def notify_order(self, order):
        """Notificar cambios en órdenes"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'🟢 COMPRA EJECUTADA - Precio: {order.executed.price:.5f}, '
                        f'Costo: {order.executed.value:.2f}, '
                        f'Comisión: {order.executed.comm:.2f}')
            else:
                self.log(f'🔴 VENTA EJECUTADA - Precio: {order.executed.price:.5f}, '
                        f'Costo: {order.executed.value:.2f}, '
                        f'Comisión: {order.executed.comm:.2f}')
        
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
        
        self.log(f'TRADE CERRADO - P&L: {pnl:.2f}, P&L Neto: {pnlcomm:.2f}, ROI: {roi:.2f}%')
        
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
            'direction': 'LONG' if trade.size > 0 else 'SHORT'
        }
        self.trades.append(trade_info)
    
    def stop(self):
        """Método llamado al final del backtesting"""
        # Cerrar cualquier posición abierta al final del backtesting
        if self.position:
            self.log(f'🔚 Cerrando posición abierta al final del backtesting')
            self.close()
        
        self.log(f'🏁 BACKTESTING COMPLETADO')
        self.log(f'   📊 Total de operaciones: {self.trade_count}')
        self.log(f'   ✅ Operaciones ganadoras: {self.win_count}')
        self.log(f'   ❌ Operaciones perdedoras: {self.loss_count}')
        
        if self.trade_count > 0:
            win_rate = (self.win_count / self.trade_count) * 100
            self.log(f'   📈 Tasa de éxito: {win_rate:.2f}%')

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
        df = df.tail(500)
        
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
        if hasattr(trades_analysis, 'total') and trades_analysis.total.total > 0:
            print(f"\n🎯 ANÁLISIS DE OPERACIONES:")
            print(f"   📊 Total de operaciones: {trades_analysis.total.total}")
            print(f"   ✅ Operaciones ganadoras: {trades_analysis.won.total}")
            print(f"   ❌ Operaciones perdedoras: {trades_analysis.lost.total}")
            
            win_rate = (trades_analysis.won.total / trades_analysis.total.total) * 100
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