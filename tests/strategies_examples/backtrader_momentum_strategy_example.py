import backtrader as bt
import pandas as pd
import numpy as np
import sys
import os
import collections

# Agregar el directorio de la librería al path
strategy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "estrategia")
sys.path.insert(0, strategy_path)


class MomentumSMCStrategyExample(bt.Strategy):
    """
    EJEMPLO DE ESTRATEGIA: Ruptura de Estructura (BOS) + Order Block + Fair Value Gap
    
    Esta es una versión de ejemplo que utiliza la librería MomentumSMCStrategyLib
    para calcular señales de trading. La estrategia combina tres enfoques:
    
    ESTRATEGIA 1: BOS + VELA DE IMPULSO
    ESTRATEGIA 2: ORDER BLOCK + FIBONACCI (Tendencia 1H alcista)
    ESTRATEGIA 3: FAIR VALUE GAP (FVG) (Tendencia 15M/1H alcista)
    
    GESTIÓN DE RIESGO:
    - POSICIÓN ÚNICA: Solo se permite una posición activa a la vez
    - Stop Loss: Justo por debajo/encima del Order Block o swing previo + buffer de 1.5× ATR(14)
    - Take Profit 1: Nivel del swing high/low en timeframe superior (15M) donde confluyan estructuras
    - Take Profit 2: Zonas clave en mitigación o Breaker Block identificado en 15M/1H
    - Trailing Stop: Tras alcanzar 50% de TP, mover SL a break-even. Al alcanzar TP1, mover SL a punto medio
    """
    params = dict(
        swing_length=5,  # Para identificar swings más claros
        lookback=20,
        buffer_size=500,  # Reducido para simplificar
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        # Parámetros para Order Block
        ob_lookback=50,  # Buscar Order Blocks en las últimas 50 velas
        fib_min=0.618,   # 61.8% Fibonacci
        fib_max=0.786,   # 78.6% Fibonacci
        # Parámetros para Fair Value Gap
        fvg_lookback=30,  # Buscar FVG en las últimas 30 velas
        fvg_min_size=0.0001,  # Tamaño mínimo del gap
    )

    def __init__(self):
        self.data_close = self.datas[0].close
        self.data_open = self.datas[0].open
        self.data_high = self.datas[0].high
        self.data_low = self.datas[0].low
        self.data_volume = self.datas[0].volume
        

        
        # Contadores de señales
        self.buy_signal_count = 0
        self.sell_signal_count = 0
        
        # Buffer de datos
        self.df_buffer = collections.deque(maxlen=self.p.buffer_size)
        
        # Gestión de órdenes
        self.sl_order = None
        self.tp1_order = None
        self.tp2_order = None
        self.position_size = 0
        
        # Indicadores técnicos para visualización
        self.macd = bt.indicators.MACD(
            self.data_close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        self.rsi = bt.indicators.RSI(self.data_close, period=self.p.rsi_period)
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # Indicador de Fibonacci para visualización
        self.fibonacci = FibonacciIndicator()
        
        # Indicador de Order Blocks para visualización
        self.order_block_indicator = OrderBlockIndicator()

    def next(self):
        # Mensaje inicial de la estrategia
        if len(self.data) == 1:
            print("🚀 INICIANDO EJEMPLO DE ESTRATEGIA: Ruptura de Estructura (BOS) + Order Block + Fair Value Gap")
            print("=" * 70)
            print("📋 ESTRATEGIA 1: BOS + VELA DE IMPULSO")
            print("   ✅ BOS: Vela que rompe el último swing high/low")
            print("   ✅ Vela de impulso: Cuerpo amplio (≥60%) y colas pequeñas (≤20%)")
            print("   ✅ MACD: Crossover alcista/bajista")
            print("   ✅ RSI: >50 para compras, <50 para ventas")
            print("   ✅ Volumen alto (opcional): Confirmación adicional")
            print("")
            print("📋 ESTRATEGIA 2: ORDER BLOCK + FIBONACCI (Tendencia 1H alcista)")
            print("   ✅ Order Block: Vela previa al impulso institucional")
            print("   ✅ Retroceso Fibonacci: 61.8% - 78.6%")
            print("   ✅ MACD: Histograma reduciendo debilidad")
            print("   ✅ RSI: >30 con divergencia alcista")
            print("")
            print("📋 ESTRATEGIA 3: FAIR VALUE GAP (FVG) (Tendencia 15M/1H alcista)")
            print("   ✅ FVG: Gap entre velas consecutivas")
            print("   ✅ Relleno: Precio toca zona media del FVG")
            print("   ✅ MACD: Crossover cerca del FVG")
            print("   ✅ RSI: Reacción alcista en 50-60")
            print("   ✅ Verificación: No FVG sin mitigar en niveles superiores")
            print("=" * 70)
        
        # Agregar la nueva barra al buffer
        self.df_buffer.append({
            'open': self.data_open[0],
            'high': self.data_high[0],
            'low': self.data_low[0],
            'close': self.data_close[0],
            'volume': self.data_volume[0],
            'datetime': self.datas[0].datetime.datetime(0)
        })
        
        # Salir si no hay suficientes velas para análisis
        if len(self.df_buffer) < 100:
            return
            
        if len(self.data) % 100 == 0:
            print(f"Procesando barra {len(self.data)} - Fecha: {self.datas[0].datetime.datetime(0)} - Precio: {self.data_close[0]}")
        
        # Obtener DataFrame
        df = self._get_df()
        if len(df) < self.p.lookback:
            return
            

        
        # Procesar señales de la librería
        for signal in signals:
            if signal['index'] == len(df) - 1:  # Señal en la barra actual
                if signal['type'] == 'BUY' and not self.position:
                    self._execute_buy_signal_from_lib(signal)
                elif signal['type'] == 'SELL' and not self.position:
                    self._execute_sell_signal_from_lib(signal)

        # --- ACTUALIZAR TRAILING STOP ---
        self._update_trailing_stop()

    def _get_df(self):
        # Construye un DataFrame OHLCV solo a partir del buffer
        if not self.df_buffer:
            return pd.DataFrame()
        data = {
            'open': [x['open'] for x in self.df_buffer],
            'high': [x['high'] for x in self.df_buffer],
            'low': [x['low'] for x in self.df_buffer],
            'close': [x['close'] for x in self.df_buffer],
            'volume': [x['volume'] for x in self.df_buffer],
        }
        index = pd.Index([x['datetime'] for x in self.df_buffer])
        df = pd.DataFrame(data, index=index)
        return df

    def _execute_buy_signal_from_lib(self, signal):
        """Ejecutar señal de compra desde la librería - SOLO UNA POSICIÓN A LA VEZ"""
        # Verificar que no haya posición activa
        if self.position:
            print(f"⚠️ Ya hay una posición activa. Ignorando señal de compra ({signal['strategy']})")
            return
        
        entry_price = float(self.data_close[0])
        
        # Usar los métodos de SL y TP
        sl = self._get_sl_buy(entry_price)
        tp1 = self._get_tp1_buy(entry_price)
        tp2 = self._get_tp2_buy(entry_price)
        
        # Tamaño de posición fijo
        size = 0.01
        
        # Ejecutar orden
        self.buy(size=size)
        self.sl_order = self.sell(exectype=bt.Order.Stop, price=sl, size=size)
        self.tp1_order = self.sell(exectype=bt.Order.Limit, price=tp1, size=size*0.5)
        self.tp2_order = self.sell(exectype=bt.Order.Limit, price=tp2, size=size*0.5)
        
        self.buy_signal_count += 1
        confidence = signal.get('confidence', 0)
        print(f"🚀 SEÑAL DE COMPRA #{self.buy_signal_count} ({signal['strategy']}) | Confianza: {confidence}% | Entrada: {entry_price:.5f} | SL: {sl:.5f} | TP1: {tp1:.5f} | TP2: {tp2:.5f} | Tamaño: {size}")

    def _execute_sell_signal_from_lib(self, signal):
        """Ejecutar señal de venta desde la librería - SOLO UNA POSICIÓN A LA VEZ"""
        # Verificar que no haya posición activa
        if self.position:
            print(f"⚠️ Ya hay una posición activa. Ignorando señal de venta ({signal['strategy']})")
            return
        
        entry_price = float(self.data_close[0])
        
        # Usar los métodos de SL y TP
        sl = self._get_sl_sell(entry_price)
        tp1 = self._get_tp1_sell(entry_price)
        tp2 = self._get_tp2_sell(entry_price)
        
        # Tamaño de posición fijo
        size = 0.01
        
        # Ejecutar orden
        self.sell(size=size)
        self.sl_order = self.buy(exectype=bt.Order.Stop, price=sl, size=size)
        self.tp1_order = self.buy(exectype=bt.Order.Limit, price=tp1, size=size*0.5)
        self.tp2_order = self.buy(exectype=bt.Order.Limit, price=tp2, size=size*0.5)
        
        self.sell_signal_count += 1
        confidence = signal.get('confidence', 0)
        print(f"📉 SEÑAL DE VENTA #{self.sell_signal_count} ({signal['strategy']}) | Confianza: {confidence}% | Entrada: {entry_price:.5f} | SL: {sl:.5f} | TP1: {tp1:.5f} | TP2: {tp2:.5f} | Tamaño: {size}")

    def notify_order(self, order):
        # Cancelar el SL y TPs si se cierra la posición
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if self.sl_order is not None:
                self.cancel(self.sl_order)
                self.sl_order = None
            if self.tp1_order is not None:
                self.cancel(self.tp1_order)
                self.tp1_order = None
            if self.tp2_order is not None:
                self.cancel(self.tp2_order)
                self.tp2_order = None

    # ===== MÉTODOS DE GESTIÓN DE RIESGO (simplificados para el ejemplo) =====

    def _calculate_atr(self, period=14):
        """Calcular Average True Range (ATR) para el buffer de volatilidad"""
        if len(self.df_buffer) < period:
            return 0.001  # Valor por defecto
        
        df = self._get_df()
        if len(df) < period:
            return 0.001
        
        # Calcular True Range
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calcular ATR como media móvil del True Range
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) else 0.001

    def _get_sl_buy(self, entry_price):
        """Stop Loss para compras (simplificado para el ejemplo)"""
        atr = self._calculate_atr(14)
        atr_buffer = atr * 1.5
        
        # Fallback: 2% del precio de entrada
        sl_price = entry_price * 0.98
        final_sl = sl_price - atr_buffer
        
        print(f"SL Compra: {sl_price:.5f}, ATR Buffer={atr_buffer:.5f}, Final={final_sl:.5f}")
        return final_sl

    def _get_sl_sell(self, entry_price):
        """Stop Loss para ventas (simplificado para el ejemplo)"""
        atr = self._calculate_atr(14)
        atr_buffer = atr * 1.5
        
        # Fallback: 2% del precio de entrada
        sl_price = entry_price * 1.02
        final_sl = sl_price + atr_buffer
        
        print(f"SL Venta: {sl_price:.5f}, ATR Buffer={atr_buffer:.5f}, Final={final_sl:.5f}")
        return final_sl

    def _get_tp1_buy(self, entry_price):
        """Take Profit 1 para compras (simplificado para el ejemplo)"""
        # Fallback: 1:2 RR
        risk = entry_price - self._get_sl_buy(entry_price)
        tp1 = entry_price + (risk * 2)
        
        print(f"TP1 Compra: {tp1:.5f}")
        return tp1

    def _get_tp2_buy(self, entry_price):
        """Take Profit 2 para compras (simplificado para el ejemplo)"""
        # Fallback: 5% del precio de entrada
        tp2 = entry_price * 1.05
        
        print(f"TP2 Compra: {tp2:.5f}")
        return tp2

    def _get_tp1_sell(self, entry_price):
        """Take Profit 1 para ventas (simplificado para el ejemplo)"""
        # Fallback: 1:2 RR
        risk = self._get_sl_sell(entry_price) - entry_price
        tp1 = entry_price - (risk * 2)
        
        print(f"TP1 Venta: {tp1:.5f}")
        return tp1

    def _get_tp2_sell(self, entry_price):
        """Take Profit 2 para ventas (simplificado para el ejemplo)"""
        # Fallback: 5% del precio de entrada
        tp2 = entry_price * 0.95
        
        print(f"TP2 Venta: {tp2:.5f}")
        return tp2

    def _update_trailing_stop(self):
        """Actualizar trailing stop según las reglas especificadas (simplificado)"""
        if not self.position:
            return
        
        current_price = float(self.data_close[0])
        entry_price = self.position.price
        
        # Calcular porcentaje de ganancia
        if self.position.size > 0:  # Posición larga
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Regla 1: Tras alcanzar 50% de TP, mover SL a break-even
            if profit_pct >= 1.0 and self.sl_order and self.sl_order.price < entry_price:
                new_sl = entry_price * 1.001  # Justo por encima del break-even
                self.broker.cancel(self.sl_order)
                self.sl_order = self.sell(exectype=bt.Order.Stop, price=new_sl, size=self.position.size)
                print(f"🔄 Trailing Stop: Movido a break-even ({new_sl:.5f})")
        
        elif self.position.size < 0:  # Posición corta
            profit_pct = (entry_price - current_price) / entry_price * 100
            
            # Regla 1: Tras alcanzar 50% de TP, mover SL a break-even
            if profit_pct >= 1.0 and self.sl_order and self.sl_order.price > entry_price:
                new_sl = entry_price * 0.999  # Justo por debajo del break-even
                self.broker.cancel(self.sl_order)
                self.sl_order = self.buy(exectype=bt.Order.Stop, price=new_sl, size=abs(self.position.size))
                print(f"🔄 Trailing Stop: Movido a break-even ({new_sl:.5f})")

class FibonacciIndicator(bt.Indicator):
    """Indicador de niveles de Fibonacci para visualización"""
    lines = ('fib_618', 'fib_786',)
    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(
        fib_618=dict(_name='Fib 61.8%', color='orange', linestyle='--'),
        fib_786=dict(_name='Fib 78.6%', color='red', linestyle='--')
    )
    
    def next(self):
        # Los niveles se actualizan desde la estrategia principal
        pass

class OrderBlockIndicator(bt.Indicator):
    """Indicador para mostrar Order Blocks en el gráfico"""
    lines = ('ob_high', 'ob_low',)
    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(
        ob_high=dict(_name='OB High', color='blue', linestyle='-', linewidth=2),
        ob_low=dict(_name='OB Low', color='blue', linestyle='-', linewidth=2)
    )
    
    def next(self):
        # Los niveles se actualizan desde la estrategia principal
        pass

class BrokerObserver(bt.Observer):
    """Observador para mostrar información del broker en los gráficos"""
    lines = ('cash', 'value',)
    plotinfo = dict(plot=True, subplot=True)
    plotlines = dict(
        cash=dict(_name='Cash', color='red'),
        value=dict(_name='Value', color='blue')
    )
    
    def next(self):
        self.lines.cash[0] = self._owner.broker.getcash()
        self.lines.value[0] = self._owner.broker.getvalue()

class TradeObserver(bt.Observer):
    """Observador para mostrar trades en los gráficos"""
    lines = ('pnl',)
    plotinfo = dict(plot=True, subplot=True)
    plotlines = dict(
        pnl=dict(_name='PnL', color='green', _method='bar')
    )
    
    def next(self):
        if self._owner.position:
            self.lines.pnl[0] = self._owner.position.pnl
        else:
            self.lines.pnl[0] = 0 