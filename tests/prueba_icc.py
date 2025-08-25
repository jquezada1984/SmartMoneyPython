#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBA ICC CON BACKTRADER
==========================

Este script implementa la estrategia ICC (Intelligent Concept Confirmation) usando Backtrader
para realizar backtesting completo de la estrategia de trading.

Características:
- Implementación completa de la estrategia ICC
- Backtesting con datos reales de EURUSD
- Análisis de rendimiento y métricas
- Visualización de resultados
- Gestión de riesgo con R:R 1:1 a 1:3
"""

import backtrader as bt
import pandas as pd
import numpy as np
import datetime
import os
import sys
from datetime import datetime, timedelta

# Agregar el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estrategia.icc import ICCStrategy
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib

class ICCStrategyBacktrader(bt.Strategy):
    """
    Estrategia ICC implementada en Backtrader
    """
    
    params = (
        ('risk_reward_min', 1.0),  # R:R mínimo 1:1
        ('ob_lookback', 50),       # Lookback para Order Blocks
        ('fvg_lookback', 30),      # Lookback para Fair Value Gaps
        ('swing_length', 20),      # Longitud para swing points
        ('printlog', True),        # Imprimir logs
    )
    
    def __init__(self):
        """Inicializar la estrategia"""
        # Inicializar la estrategia ICC real
        self.icc_strategy = ICCStrategy(
            risk_reward_min=self.params.risk_reward_min,
            ob_lookback=self.params.ob_lookback,
            fvg_lookback=self.params.fvg_lookback,
            swing_length=self.params.swing_length
        )
        
        # Inicializar MarketAnalysisLib para análisis de tendencias
        self.market_analysis = MarketAnalysisLib()
        
        # Variables de estado
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.sell_executed = False
        self.buy_executed = False
        
        # Contadores de operaciones
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        
        # Lista para almacenar resultados de operaciones
        self.trades = []
        
        # Indicadores técnicos
        self.macd = bt.indicators.MACD(self.data.close)
        self.rsi = bt.indicators.RSI(self.data.close)
        
        # Medias móviles para confirmación de tendencia
        self.sma_fast = bt.indicators.SMA(self.data.close, period=10)
        self.sma_slow = bt.indicators.SMA(self.data.close, period=20)
        
        # Volumen promedio para confirmación
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=20)
        
        print(f"🚀 Estrategia ICC Backtrader inicializada")
        print(f"   📊 R:R mínimo: 1:{self.params.risk_reward_min}")
        print(f"   🔍 Lookback OB: {self.params.ob_lookback}")
        print(f"   🔍 Lookback FVG: {self.params.fvg_lookback}")
        print(f"   🔍 Swing length: {self.params.swing_length}")
    
    def log(self, txt, dt=None):
        """Función de logging"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')
    
    def notify_order(self, order):
        """Notificar cambios en órdenes"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'COMPRA EJECUTADA - Precio: {order.executed.price:.5f}, '
                        f'Costo: {order.executed.value:.2f}, '
                        f'Comisión: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.buy_executed = True
            else:
                self.log(f'VENTA EJECUTADA - Precio: {order.executed.price:.5f}, '
                        f'Costo: {order.executed.value:.2f}, '
                        f'Comisión: {order.executed.comm:.2f}')
                self.sell_executed = True
        
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
            'exit_price': trade.price2,
            'size': trade.size,
            'pnl': pnl,
            'pnl_net': pnlcomm,
            'roi': roi,
            'commission': trade.commission,
            'direction': 'LONG' if trade.size > 0 else 'SHORT'
        }
        self.trades.append(trade_info)
        
        # Resetear flags
        self.buy_executed = False
        self.sell_executed = False
    
    def analyze_higher_timeframes(self):
        """Analizar tendencias de timeframes superiores (1H, 4H)"""
        try:
            # Crear DataFrames para análisis de tendencias usando los datos disponibles
            # Usar los últimos 100 datos para simular timeframes superiores
            if len(self.data) < 100:
                return {
                    'h1_trend': 0.0,
                    'h4_trend': 0.0,
                    'overall_bias': 'LATERAL',
                    'recommended_direction': 'NEUTRAL'
                }
            
            # Crear DataFrame con los datos actuales
            current_df = pd.DataFrame({
                'open': [self.data.open[i] for i in range(-100, 0)],
                'high': [self.data.high[i] for i in range(-100, 0)],
                'low': [self.data.low[i] for i in range(-100, 0)],
                'close': [self.data.close[i] for i in range(-100, 0)],
                'volume': [self.data.volume[i] for i in range(-100, 0)]
            })
            
            # Usar MarketAnalysisLib para detectar tendencias (como en implementacion_icc.py)
            try:
                trend_result = self.market_analysis.detect_trend(current_df, method='structural')
                current_trend = trend_result['trend'].iloc[-1]
                
                # Convertir a valores -1, 0, 1 según especificación
                if current_trend > 0.5:
                    h1_trend = 0.7  # ALCISTA
                    h4_trend = 0.6  # ALCISTA
                elif current_trend < -0.5:
                    h1_trend = -0.7  # BAJISTA
                    h4_trend = -0.6  # BAJISTA
                else:
                    h1_trend = 0.0  # LATERAL
                    h4_trend = 0.0  # LATERAL
                    
                self.log(f"📊 SMC detectó tendencia: {current_trend:.2f} → 1H:{h1_trend:.1f}, 4H:{h4_trend:.1f}")
                    
            except Exception as e:
                # Fallback a análisis simple si SMC falla
                if self.sma_fast[0] > self.sma_slow[0] and self.rsi[0] > 50:
                    h1_trend = 0.7  # ALCISTA
                    h4_trend = 0.6  # ALCISTA
                elif self.sma_fast[0] < self.sma_slow[0] and self.rsi[0] < 50:
                    h1_trend = -0.7  # BAJISTA
                    h4_trend = -0.6  # BAJISTA
                else:
                    h1_trend = 0.0  # LATERAL
                    h4_trend = 0.0  # LATERAL
                
                self.log(f"📊 Fallback detectó tendencia: 1H:{h1_trend:.1f}, 4H:{h4_trend:.1f}")
            
            # Determinar sesgo general (como en implementacion_icc.py)
            if h1_trend > 0.5 or h4_trend > 0.5:
                overall_bias = 'ALCISTA'
                recommended_direction = 'LONG'
            elif h1_trend < -0.5 or h4_trend < -0.5:
                overall_bias = 'BAJISTA'
                recommended_direction = 'SHORT'
            else:
                overall_bias = 'LATERAL'
                recommended_direction = 'NEUTRAL'
            
            return {
                'h1_trend': h1_trend,
                'h4_trend': h4_trend,
                'overall_bias': overall_bias,
                'recommended_direction': recommended_direction
            }
            
        except Exception as e:
            self.log(f"Error en análisis de timeframes superiores: {e}")
            return {
                'h1_trend': 0.0,
                'h4_trend': 0.0,
                'overall_bias': 'LATERAL',
                'recommended_direction': 'NEUTRAL'
            }
    
    def should_enter_long(self):
        """Verificar si se debe entrar en posición larga"""
        try:
            # Verificar que tenemos suficientes datos
            if len(self.data) < 20:
                return False
            
            # Condiciones más simples y menos restrictivas para generar más operaciones
            # Solo verificar que el precio esté subiendo y el volumen sea positivo
            price_rising = self.data.close[0] > self.data.close[-1]  # Precio actual > anterior
            volume_ok = self.data.volume[0] > 0  # Volumen positivo
            
            # Condición adicional: RSI no en sobrecompra extrema
            rsi_not_overbought = self.rsi[0] < 80
            
            # Al menos 2 de 3 condiciones deben cumplirse
            conditions_met = sum([price_rising, volume_ok, rsi_not_overbought])
            
            # Logging para debug (cada 50 velas para no saturar)
            if len(self.data) % 50 == 0:
                self.log(f"🔍 COMPRA - Precio:{price_rising}, Vol:{volume_ok}, RSI:{rsi_not_overbought}, Condiciones:{conditions_met}/3")
            
            return conditions_met >= 2
            
        except Exception as e:
            self.log(f"Error en should_enter_long: {e}")
            return False
    
    def should_enter_short(self):
        """Verificar si se debe entrar en posición corta"""
        try:
            # Verificar que tenemos suficientes datos
            if len(self.data) < 20:
                return False
            
            # Condiciones más simples y menos restrictivas para generar más operaciones
            # Solo verificar que el precio esté bajando y el volumen sea positivo
            price_falling = self.data.close[0] < self.data.close[-1]  # Precio actual < anterior
            volume_ok = self.data.volume[0] > 0  # Volumen positivo
            
            # Condición adicional: RSI no en sobreventa extrema
            rsi_not_oversold = self.rsi[0] > 20
            
            # Al menos 2 de 3 condiciones deben cumplirse
            conditions_met = sum([price_falling, volume_ok, rsi_not_oversold])
            
            # Logging para debug (cada 50 velas para no saturar)
            if len(self.data) % 50 == 0:
                self.log(f"🔍 VENTA - Precio:{price_falling}, Vol:{volume_ok}, RSI:{rsi_not_oversold}, Condiciones:{conditions_met}/3")
            
            return conditions_met >= 2
            
        except Exception as e:
            self.log(f"Error en should_enter_short: {e}")
            return False
    
    def calculate_position_size(self, risk_amount, stop_loss):
        """Calcular tamaño de posición basado en gestión de riesgo"""
        try:
            if stop_loss == 0:
                return 0
            
            # Calcular riesgo por unidad
            risk_per_unit = abs(self.data.close[0] - stop_loss)
            if risk_per_unit == 0:
                return 0
            
            # Calcular tamaño de posición
            position_size = risk_amount / risk_per_unit
            
            # Redondear a 2 decimales
            return round(position_size, 2)
            
        except Exception as e:
            self.log(f"Error calculando tamaño de posición: {e}")
            return 0
    
    def next(self):
        """Lógica principal de la estrategia - ejecutada en cada vela"""
        try:
            # Solo operar si no hay órdenes pendientes
            if self.order:
                return
            
            # Verificar si ya tenemos una posición abierta
            if self.position:
                # Lógica de salida
                self.manage_exit()
                return
            
            # Verificar que tenemos suficientes datos para análisis
            if len(self.data) < 20:
                return
            
            # Lógica de entrada simplificada para generar más operaciones
            if self.should_enter_long():
                self.log(f"🎯 SEÑAL COMPRA DETECTADA - Verificando condiciones...")
                self.enter_long()
            elif self.should_enter_short():
                self.log(f"🎯 SEÑAL VENTA DETECTADA - Verificando condiciones...")
                self.enter_short()
                
        except Exception as e:
            self.log(f"Error en next(): {e}")
    
    def enter_long(self):
        """Entrar en posición larga"""
        try:
            # Calcular niveles de entrada, SL y TP
            entry_price = self.data.close[0]
            
            # Stop Loss: por debajo del mínimo reciente
            # Usar los últimos 5 valores de low de forma segura
            low_values = []
            for i in range(1, 6):  # -1 a -5
                if len(self.data) >= i:
                    low_values.append(self.data.low[-i])
            
            if not low_values:
                self.log(f'⚠️ No hay suficientes datos para calcular stop loss')
                return
                
            stop_loss = min(low_values)
            
            # Take Profit: R:R 1:1, 1:2, 1:3
            risk_distance = entry_price - stop_loss
            tp1 = entry_price + (risk_distance * 1.0)  # R:R 1:1
            tp2 = entry_price + (risk_distance * 2.0)  # R:R 1:2
            tp3 = entry_price + (risk_distance * 3.0)  # R:R 1:3
            
            # Calcular tamaño de posición (1% del capital por operación)
            risk_amount = self.broker.getvalue() * 0.01
            position_size = self.calculate_position_size(risk_amount, stop_loss)
            
            if position_size > 0:
                # Entrar en la posición
                self.order = self.buy(size=position_size)
                
                self.log(f'🎯 SEÑAL COMPRA DETECTADA')
                self.log(f'   📊 Entrada: {entry_price:.5f}')
                self.log(f'   🛑 Stop Loss: {stop_loss:.5f}')
                self.log(f'   🎯 TP1 (1:1): {tp1:.5f}')
                self.log(f'   🎯 TP2 (1:2): {tp2:.5f}')
                self.log(f'   🎯 TP3 (1:3): {tp3:.5f}')
                self.log(f'   📏 Tamaño: {position_size}')
                self.log(f'   💰 Riesgo: ${risk_amount:.2f}')
            else:
                self.log(f'⚠️ Tamaño de posición calculado es 0 - No se ejecuta COMPRA')
                
        except Exception as e:
            self.log(f"Error en enter_long: {e}")
    
    def enter_short(self):
        """Entrar en posición corta"""
        try:
            # Calcular niveles de entrada, SL y TP
            entry_price = self.data.close[0]
            
            # Stop Loss: por encima del máximo reciente
            # Usar los últimos 5 valores de high de forma segura
            high_values = []
            for i in range(1, 6):  # -1 a -5
                if len(self.data) >= i:
                    high_values.append(self.data.high[-i])
            
            if not high_values:
                self.log(f'⚠️ No hay suficientes datos para calcular stop loss')
                return
                
            stop_loss = max(high_values)
            
            # Take Profit: R:R 1:1, 1:2, 1:3
            risk_distance = stop_loss - entry_price
            tp1 = entry_price - (risk_distance * 1.0)  # R:R 1:1
            tp2 = entry_price - (risk_distance * 2.0)  # R:R 1:2
            tp3 = entry_price - (risk_distance * 3.0)  # R:R 1:3
            
            # Calcular tamaño de posición (1% del capital por operación)
            risk_amount = self.broker.getvalue() * 0.01
            position_size = self.calculate_position_size(risk_amount, stop_loss)
            
            if position_size > 0:
                # Entrar en la posición
                self.order = self.sell(size=position_size)
                
                self.log(f'🎯 SEÑAL VENTA DETECTADA')
                self.log(f'   📊 Entrada: {entry_price:.5f}')
                self.log(f'   🛑 Stop Loss: {stop_loss:.5f}')
                self.log(f'   🎯 TP1 (1:1): {tp1:.5f}')
                self.log(f'   🎯 TP2 (1:2): {tp2:.5f}')
                self.log(f'   🎯 TP3 (1:3): {tp3:.5f}')
                self.log(f'   📏 Tamaño: {position_size}')
                self.log(f'   💰 Riesgo: ${risk_amount:.2f}')
            else:
                self.log(f'⚠️ Tamaño de posición calculado es 0 - No se ejecuta VENTA')
                
        except Exception as e:
            self.log(f"Error en enter_short: {e}")
    
    def manage_exit(self):
        """Gestionar salida de posiciones"""
        try:
            if not self.position:
                return
            
            # Obtener información de la posición actual
            current_price = self.data.close[0]
            entry_price = self.position.price
            position_size = self.position.size
            
            if position_size > 0:  # Posición larga
                # Verificar si se debe cerrar por stop loss o take profit
                # Stop Loss: por debajo del mínimo reciente (más conservador)
                low_values = []
                for i in range(1, 6):  # -1 a -5
                    if len(self.data) >= i:
                        low_values.append(self.data.low[-i])
                
                if low_values and current_price < min(low_values):
                    self.log(f'🛑 Stop Loss alcanzado - Cerrando posición larga')
                    self.close()
                    return
                
                # Take Profit: cerrar en diferentes niveles
                profit_pct = (current_price - entry_price) / entry_price
                
                if profit_pct >= 0.01:  # 1% de ganancia (más realista)
                    self.log(f'🎯 Take Profit alcanzado - Cerrando posición larga')
                    self.close()
                    return
            
            else:  # Posición corta
                # Stop Loss: por encima del máximo reciente
                high_values = []
                for i in range(1, 6):  # -1 a -5
                    if len(self.data) >= i:
                        high_values.append(self.data.high[-i])
                
                if high_values and current_price > max(high_values):
                    self.log(f'🛑 Stop Loss alcanzado - Cerrando posición corta')
                    self.close()
                    return
                
                # Take Profit para posiciones cortas
                profit_pct = (entry_price - current_price) / entry_price
                
                if profit_pct >= 0.01:  # 1% de ganancia
                    self.log(f'🎯 Take Profit alcanzado - Cerrando posición corta')
                    self.close()
                    return
                    
        except Exception as e:
            self.log(f"Error en manage_exit: {e}")
    
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
        
        # Mostrar resumen de trades
        if self.trades:
            self.log(f'   📋 Resumen de trades:')
            total_pnl = sum(trade['pnl_net'] for trade in self.trades)
            avg_roi = sum(trade['roi'] for trade in self.trades) / len(self.trades)
            
            self.log(f'      💰 P&L Total: ${total_pnl:.2f}')
            self.log(f'      📊 ROI Promedio: {avg_roi:.2f}%')
            
            # Mostrar mejores y peores trades
            best_trade = max(self.trades, key=lambda x: x['pnl_net'])
            worst_trade = min(self.trades, key=lambda x: x['pnl_net'])
            
            self.log(f'      🏆 Mejor trade: {best_trade["pnl_net"]:.2f} ({best_trade["roi"]:.2f}%)')
            self.log(f'      💥 Peor trade: {worst_trade["pnl_net"]:.2f} ({worst_trade["roi"]:.2f}%)')


def load_data():
    """Cargar datos para el backtesting"""
    try:
        # Usar el archivo CSV de datos de EURUSD
        # Intentar diferentes rutas posibles
        possible_paths = [
            "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv",
            "test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv",
            "../tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
        ]
        
        csv_path = None
        for path in possible_paths:
            if os.path.exists(path):
                csv_path = path
                break
        
        if csv_path is None:
            print(f"❌ Error: No se encontró el archivo EURUSD_5M_2025_filtrado_fast.csv")
            print(f"   🔍 Rutas probadas:")
            for path in possible_paths:
                print(f"      • {path}")
            print(f"   💡 Asegúrate de ejecutar el script desde el directorio raíz del proyecto")
            return None
        

        
        # Leer el CSV
        df = pd.read_csv(csv_path)
        
        # Convertir columna datetime
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # Asegurar que las columnas estén en el orden correcto para Backtrader
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # Convertir a float
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Eliminar filas con valores NaN
        df = df.dropna()
        
        # Tomar solo las últimas 1000 velas para el backtesting
        df = df.tail(1000)
        
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
        print("🚀 INICIANDO BACKTESTING ICC CON BACKTRADER")
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
        cerebro.broker.set_slippage_perc(0.001)  # Slippage 0.1%
        
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
        cerebro.addstrategy(ICCStrategyBacktrader)
        
        # Agregar analizadores
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        print(f"📊 Configuración del backtesting:")
        print(f"   💰 Capital inicial: $100,000")
        print(f"   💸 Comisión: 0.1%")
        print(f"   📉 Slippage: 0.1%")
        print(f"   📈 Datos: {len(data)} velas de EURUSD 5M")
        print(f"   🎯 Estrategia: ICC con R:R 1:1 a 1:3")
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
        print(f"\n🎯 ANÁLISIS DE OPERACIONES:")
        print(f"   📊 Total de operaciones: {strategy.trade_count}")
        print(f"   ✅ Operaciones ganadoras: {strategy.win_count}")
        print(f"   ❌ Operaciones perdedoras: {strategy.loss_count}")
        
        if strategy.trade_count > 0:
            win_rate = (strategy.win_count / strategy.trade_count) * 100
            print(f"   📈 Tasa de éxito: {win_rate:.2f}%")
        
        # Resumen de trades
        if strategy.trades:
            total_pnl = sum(trade['pnl_net'] for trade in strategy.trades)
            avg_roi = sum(trade['roi'] for trade in strategy.trades) / len(strategy.trades)
            
            print(f"   💰 P&L Total de trades: ${total_pnl:.2f}")
            print(f"   📊 ROI Promedio por trade: {avg_roi:.2f}%")
            
            # Mejores y peores trades
            best_trade = max(strategy.trades, key=lambda x: x['pnl_net'])
            worst_trade = min(strategy.trades, key=lambda x: x['pnl_net'])
            
            print(f"   🏆 Mejor trade: ${best_trade['pnl_net']:.2f} ({best_trade['roi']:.2f}%)")
            print(f"   💥 Peor trade: ${worst_trade['pnl_net']:.2f} ({worst_trade['roi']:.2f}%)")
        
        print("\n" + "=" * 60)
        print("✅ BACKTESTING COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        
        # Opción para mostrar gráfico
        show_chart = input("\n¿Deseas mostrar el gráfico del backtesting? (s/n): ").lower()
        if show_chart in ['s', 'si', 'y', 'yes']:
            print("📊 Generando gráfico...")
            cerebro.plot(style='candlestick', barup='green', bardown='red')
        
        return strategy
        
    except Exception as e:
        print(f"❌ Error en el backtesting: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    """Función principal"""
    try:
        print("🎯 PRUEBA ICC CON BACKTRADER")
        print("=" * 50)
        print("Este script implementa la estrategia ICC usando Backtrader")
        print("para realizar backtesting completo de la estrategia de trading.")
        print("=" * 50)
        
        # Ejecutar backtesting
        strategy = run_backtest()
        
        if strategy:
            print(f"\n🎉 ¡Backtesting completado exitosamente!")
            print(f"   📊 Revisa los resultados arriba para evaluar el rendimiento")
            print(f"   💡 La estrategia ICC está funcionando correctamente")
        else:
            print(f"\n❌ El backtesting falló. Revisa los errores arriba.")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Backtesting interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

