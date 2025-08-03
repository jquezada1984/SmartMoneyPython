import backtrader as bt
import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc
import collections

class MomentumSMCStrategy(bt.Strategy):
    """
    ESTRATEGIA: Ruptura de Estructura (BOS) + Order Block + Fair Value Gap
    
    Esta estrategia combina tres enfoques de trading:
    
    ESTRATEGIA 1: BOS + VELA DE IMPULSO
    - BOS: Vela que rompe el último swing high/low
    - Vela de impulso: Cuerpo amplio (≥60%) y colas pequeñas (≤20%)
    - MACD: Crossover alcista/bajista
    - RSI: >50 para compras, <50 para ventas
    - Volumen alto (opcional): Confirmación adicional
    
    ESTRATEGIA 2: ORDER BLOCK + FIBONACCI (Tendencia 1H alcista)
    - Order Block: Vela previa al impulso institucional
    - Retroceso Fibonacci: 61.8% - 78.6%
    - MACD: Histograma reduciendo debilidad
    - RSI: >30 con divergencia alcista
    
    ESTRATEGIA 3: FAIR VALUE GAP (FVG) (Tendencia 15M/1H alcista)
    - FVG: Gap entre velas consecutivas
    - Relleno: Precio toca zona media del FVG
    - MACD: Crossover cerca del FVG
    - RSI: Reacción alcista en 50-60
    - Verificación: No FVG sin mitigar en niveles superiores
    
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
        
        # Swing highs/lows
        self.swing_highs_lows = None
        
        # Gestión de órdenes
        self.sl_order = None
        self.tp1_order = None
        self.tp2_order = None
        self.position_size = 0
        
        # Indicadores técnicos
        self.macd = bt.indicators.MACD(
            self.data_close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        self.rsi = bt.indicators.RSI(self.data_close, period=self.p.rsi_period)
        
        # Agregar indicadores adicionales para visualización
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        # Indicador de Fibonacci para visualización
        self.fibonacci = FibonacciIndicator()
        
        # Indicador de Order Blocks para visualización
        self.order_block_indicator = OrderBlockIndicator()
        
        # Variables para calcular niveles de Fibonacci dinámicamente
        self.last_swing_high = None
        self.last_swing_low = None
        
        # Variables para Order Block
        self.order_blocks = []
        self.trend_1h = 0  # Tendencia 1H
        
        # Variables para Fair Value Gap
        self.fair_value_gaps = []
        self.trend_15m = 0  # Tendencia 15M

    def next(self):
        # Mensaje inicial de la estrategia
        if len(self.data) == 1:
            print("🚀 INICIANDO ESTRATEGIA: Ruptura de Estructura (BOS) + Order Block + Fair Value Gap")
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
            
        # Calcular swing highs/lows
        self.swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.p.swing_length)
        
        # Actualizar niveles de Fibonacci para visualización
        self._update_fibonacci_levels()
        
        # Verificar si los indicadores están listos
        if len(self.macd.macd) < 2 or len(self.rsi) < 1:
            return
            
        # --- ESTRATEGIA 1: BOS + VELA DE IMPULSO + MACD + RSI ---
        
        # 1. VERIFICAR BOS ALCISTA (Break of Structure)
        if self._is_bos_bullish():
            print("✅ BOS alcista detectado")
            
            # 2. VERIFICAR VELA DE IMPULSO ALCISTA
            if self._is_impulse_candle_bullish():
                print("✅ Vela de impulso alcista detectada")
                
                # 3. VERIFICAR MACD CROSSOVER ALCISTA
                if self._is_macd_bullish_crossover():
                    print("✅ MACD crossover alcista detectado")
                    
                    # 4. VERIFICAR RSI > 50 (confirmando momentum)
                    if self.rsi[0] > 50:
                        print("✅ RSI > 50 confirmando momentum")
                        
                        # 5. VERIFICAR VOLUMEN ALTO (opcional)
                        if self._is_high_volume():
                            print("✅ Volumen alto confirmado")
                        
                        # SEÑAL DE COMPRA - ESTRATEGIA 1
                        if not self.position:
                            self._execute_buy_signal("BOS + Impulso")
        
        # 1. VERIFICAR BOS BAJISTA (Break of Structure)
        elif self._is_bos_bearish():
            print("✅ BOS bajista detectado")
            
            # 2. VERIFICAR VELA DE IMPULSO BAJISTA
            if self._is_impulse_candle_bearish():
                print("✅ Vela de impulso bajista detectada")
                
                # 3. VERIFICAR MACD CROSSOVER BAJISTA
                if self._is_macd_bearish_crossover():
                    print("✅ MACD crossover bajista detectado")
                    
                    # 4. VERIFICAR RSI < 50 (confirmando momentum bajista)
                    if self.rsi[0] < 50:
                        print("✅ RSI < 50 confirmando momentum bajista")
                        
                        # 5. VERIFICAR VOLUMEN ALTO (opcional)
                        if self._is_high_volume():
                            print("✅ Volumen alto confirmado")
                        
                        # SEÑAL DE VENTA - ESTRATEGIA 1
                        if not self.position:
                            self._execute_sell_signal("BOS + Impulso")
        
        # --- ESTRATEGIA 2: ORDER BLOCK + FIBONACCI + TENDENCIA 1H ---
        
        # Actualizar tendencia 1H
        self._update_1h_trend()
        
        # Verificar Order Block alcista con retroceso Fibonacci
        if self.trend_1h > 0:  # Tendencia alcista en 1H
            if self._is_order_block_bullish_setup():
                print("✅ Order Block alcista detectado")
                
                if self._is_fibonacci_retracement_bullish():
                    print("✅ Retroceso Fibonacci alcista detectado")
                    
                    if self._is_macd_histogram_bullish():
                        print("✅ MACD histograma reduciendo debilidad")
                        
                        if self._is_rsi_bullish_divergence():
                            print("✅ RSI divergencia alcista detectada")
                            
                                        # SEÑAL DE COMPRA - ESTRATEGIA 2
            if not self.position:
                self._execute_buy_signal("Order Block + Fibonacci")
        
        # --- ESTRATEGIA 3: FAIR VALUE GAP (FVG) + TENDENCIA 15M/1H ---
        
        # Actualizar tendencias
        self._update_15m_trend()
        
        # Verificar FVG alcista con relleno
        if self.trend_15m > 0 or self.trend_1h > 0:  # Tendencia alcista en 15M o 1H
            if self._is_fvg_bullish_setup():
                print("✅ FVG alcista detectado")
                
                if self._is_fvg_filled():
                    print("✅ FVG rellenado en zona media")
                    
                    if self._is_macd_crossover_near_fvg():
                        print("✅ MACD crossover cerca del FVG")
                        
                        if self._is_rsi_bullish_reaction():
                            print("✅ RSI reacción alcista en 50-60")
                            
                            # Verificar que no haya FVG sin mitigar en niveles superiores (15M)
                            if self._check_no_unmitigated_fvg_15m():
                                print("✅ No hay FVG sin mitigar en niveles superiores")
                                
                                # SEÑAL DE COMPRA - ESTRATEGIA 3
                                if not self.position:
                                    self._execute_buy_signal("Fair Value Gap")

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

    def _get_last(self, serie):
        # Devuelve el último valor de una Serie, DataFrame o ndarray
        if hasattr(serie, 'iloc'):
            return serie.iloc[-1]
        elif hasattr(serie, '__getitem__'):
            return serie[-1]
        else:
            return serie

    def _is_bos_bullish(self):
        """BOS alcista: vela que cierre por encima del último swing high"""
        if self.swing_highs_lows is not None and not self.swing_highs_lows.empty:
            try:
                # Verificar la estructura del DataFrame
                if 'type' in self.swing_highs_lows.columns:
                    # Buscar el último swing high
                    swing_highs = self.swing_highs_lows[self.swing_highs_lows['type'] == 'high']
                    if not swing_highs.empty:
                        last_swing_high = swing_highs['high'].iloc[-1]
                        current_close = float(self.data_close[0])
                        
                        # Verificar si la vela actual cierra por encima del swing high
                        if current_close > last_swing_high:
                            print(f"BOS alcista: Cierre actual ({current_close:.5f}) > Swing high ({last_swing_high:.5f})")
                            return True
                else:
                    # Si no hay columna 'type', buscar el máximo en las columnas de high
                    if 'high' in self.swing_highs_lows.columns:
                        last_swing_high = self.swing_highs_lows['high'].max()
                        current_close = float(self.data_close[0])
                        
                        if current_close > last_swing_high:
                            print(f"BOS alcista: Cierre actual ({current_close:.5f}) > Swing high ({last_swing_high:.5f})")
                            return True
            except Exception as e:
                print(f"Error en _is_bos_bullish: {e}")
        return False

    def _is_bos_bearish(self):
        """BOS bajista: vela que cierre por debajo del último swing low"""
        if self.swing_highs_lows is not None and not self.swing_highs_lows.empty:
            try:
                # Verificar la estructura del DataFrame
                if 'type' in self.swing_highs_lows.columns:
                    # Buscar el último swing low
                    swing_lows = self.swing_highs_lows[self.swing_highs_lows['type'] == 'low']
                    if not swing_lows.empty:
                        last_swing_low = swing_lows['low'].iloc[-1]
                        current_close = float(self.data_close[0])
                        
                        # Verificar si la vela actual cierra por debajo del swing low
                        if current_close < last_swing_low:
                            print(f"BOS bajista: Cierre actual ({current_close:.5f}) < Swing low ({last_swing_low:.5f})")
                            return True
                else:
                    # Si no hay columna 'type', buscar el mínimo en las columnas de low
                    if 'low' in self.swing_highs_lows.columns:
                        last_swing_low = self.swing_highs_lows['low'].min()
                        current_close = float(self.data_close[0])
                        
                        if current_close < last_swing_low:
                            print(f"BOS bajista: Cierre actual ({current_close:.5f}) < Swing low ({last_swing_low:.5f})")
                            return True
            except Exception as e:
                print(f"Error en _is_bos_bearish: {e}")
        return False

    def _is_impulse_candle_bullish(self):
        """Vela de impulso alcista: cuerpo amplio y cola pequeña"""
        o, h, l, c = self.data_open[0], self.data_high[0], self.data_low[0], self.data_close[0]
        body = abs(c - o)
        total_range = h - l
        
        if total_range == 0:
            return False
            
        # Cuerpo debe ser al menos 60% del rango total
        body_ratio = body / total_range
        
        # Cola superior pequeña (máximo 20% del rango)
        upper_wick = h - max(o, c)
        upper_wick_ratio = upper_wick / total_range
        
        # Cola inferior pequeña (máximo 20% del rango)
        lower_wick = min(o, c) - l
        lower_wick_ratio = lower_wick / total_range
        
        # Vela debe ser verde (alcista)
        is_green = c > o
        
        # Verificar condiciones
        if (body_ratio >= 0.6 and 
            upper_wick_ratio <= 0.2 and 
            lower_wick_ratio <= 0.2 and 
            is_green):
            print(f"Vela de impulso alcista: Body={body_ratio:.2f}, Upper={upper_wick_ratio:.2f}, Lower={lower_wick_ratio:.2f}")
            return True
            
        return False

    def _is_impulse_candle_bearish(self):
        """Vela de impulso bajista: cuerpo amplio y cola pequeña"""
        o, h, l, c = self.data_open[0], self.data_high[0], self.data_low[0], self.data_close[0]
        body = abs(c - o)
        total_range = h - l
        
        if total_range == 0:
            return False
            
        # Cuerpo debe ser al menos 60% del rango total
        body_ratio = body / total_range
        
        # Cola superior pequeña (máximo 20% del rango)
        upper_wick = h - max(o, c)
        upper_wick_ratio = upper_wick / total_range
        
        # Cola inferior pequeña (máximo 20% del rango)
        lower_wick = min(o, c) - l
        lower_wick_ratio = lower_wick / total_range
        
        # Vela debe ser roja (bajista)
        is_red = c < o
        
        # Verificar condiciones
        if (body_ratio >= 0.6 and 
            upper_wick_ratio <= 0.2 and 
            lower_wick_ratio <= 0.2 and 
            is_red):
            print(f"Vela de impulso bajista: Body={body_ratio:.2f}, Upper={upper_wick_ratio:.2f}, Lower={lower_wick_ratio:.2f}")
            return True
            
        return False

    def _is_macd_bullish_crossover(self):
        """MACD crossover alcista: línea MACD cruza por encima de la línea señal"""
        if len(self.macd.macd) < 2 or len(self.macd.signal) < 2:
            return False
            
        # Verificar crossover alcista
        macd_current = self.macd.macd[0]
        macd_previous = self.macd.macd[-1]
        signal_current = self.macd.signal[0]
        signal_previous = self.macd.signal[-1]
        
        # Crossover: MACD estaba por debajo de Signal y ahora está por encima
        if (macd_previous < signal_previous and 
            macd_current > signal_current):
            print(f"MACD crossover alcista: MACD({macd_current:.5f}) > Signal({signal_current:.5f})")
            return True
            
        return False

    def _is_macd_bearish_crossover(self):
        """MACD crossover bajista: línea MACD cruza por debajo de la línea señal"""
        if len(self.macd.macd) < 2 or len(self.macd.signal) < 2:
            return False
            
        # Verificar crossover bajista
        macd_current = self.macd.macd[0]
        macd_previous = self.macd.macd[-1]
        signal_current = self.macd.signal[0]
        signal_previous = self.macd.signal[-1]
        
        # Crossover: MACD estaba por encima de Signal y ahora está por debajo
        if (macd_previous > signal_previous and 
            macd_current < signal_current):
            print(f"MACD crossover bajista: MACD({macd_current:.5f}) < Signal({signal_current:.5f})")
            return True
            
        return False

    def _execute_buy_signal(self, strategy_type="BOS + Impulso"):
        """Ejecutar señal de compra - SOLO UNA POSICIÓN A LA VEZ"""
        # Verificar que no haya posición activa
        if self.position:
            print(f"⚠️ Ya hay una posición activa. Ignorando señal de compra ({strategy_type})")
            return
        
        entry_price = float(self.data_close[0])
        
        # Usar los nuevos métodos de SL y TP
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
        print(f"🚀 SEÑAL DE COMPRA #{self.buy_signal_count} ({strategy_type}) | Entrada: {entry_price:.5f} | SL: {sl:.5f} | TP1: {tp1:.5f} | TP2: {tp2:.5f} | Tamaño: {size}")

    def _execute_sell_signal(self, strategy_type="BOS + Impulso"):
        """Ejecutar señal de venta - SOLO UNA POSICIÓN A LA VEZ"""
        # Verificar que no haya posición activa
        if self.position:
            print(f"⚠️ Ya hay una posición activa. Ignorando señal de venta ({strategy_type})")
            return
        
        entry_price = float(self.data_close[0])
        
        # Usar los nuevos métodos de SL y TP
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
        print(f"📉 SEÑAL DE VENTA #{self.sell_signal_count} ({strategy_type}) | Entrada: {entry_price:.5f} | SL: {sl:.5f} | TP1: {tp1:.5f} | TP2: {tp2:.5f} | Tamaño: {size}")

    def _update_1h_trend(self):
        """Actualizar tendencia de 1 hora usando resampleo"""
        if len(self.df_buffer) < 12:  # Necesitamos al menos 1 hora de datos
            return
            
        # Crear DataFrame de 1H
        df_5m = self._get_df()
        df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
        
        # Resamplear a 1H
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_1h = df_5m.resample('1h').agg(ohlc_dict).dropna()
        
        if len(df_1h) < 10:
            return
            
        # Calcular tendencia usando swing highs/lows
        swing_1h = smc.swing_highs_lows(df_1h, swing_length=self.p.swing_length)
        if swing_1h is not None and not swing_1h.empty:
            trend_1h = smc.trend_indicator(df_1h, swing_1h)
            if 'Trend' in trend_1h.columns:
                self.trend_1h = trend_1h['Trend'].iloc[-1] if not trend_1h.empty else 0

    def _is_order_block_bullish_setup(self):
        """Detectar Order Block alcista: vela previa al impulso institucional"""
        if len(self.df_buffer) < 20:
            return False
            
        # Buscar velas de impulso alcista en las últimas N velas
        for i in range(min(20, len(self.df_buffer))):
            if i == 0:
                continue
                
            # Obtener datos de la vela actual y anterior
            current = list(self.df_buffer)[-(i+1)]
            previous = list(self.df_buffer)[-(i+2)]
            
            # Verificar si la vela actual es de impulso alcista
            current_body = abs(current['close'] - current['open'])
            current_range = current['high'] - current['low']
            
            if current_range == 0:
                continue
                
            body_ratio = current_body / current_range
            is_green = current['close'] > current['open']
            
            # Vela de impulso: cuerpo amplio y verde
            if body_ratio >= 0.6 and is_green:
                # La vela anterior es el Order Block
                prev_body = abs(previous['close'] - previous['open'])
                prev_range = previous['high'] - previous['low']
                
                if prev_range > 0:
                    prev_body_ratio = prev_body / prev_range
                    
                    # Order Block: vela con cuerpo significativo
                    if prev_body_ratio >= 0.4:
                        self.last_swing_high = current['high']
                        self.last_swing_low = previous['low']
                        print(f"Order Block detectado: Vela {len(self.df_buffer)-i-2} -> Impulso vela {len(self.df_buffer)-i-1}")
                        print(f"Fibonacci: Swing High={self.last_swing_high:.5f}, Swing Low={self.last_swing_low:.5f}")
                        return True
                        
        return False

    def _is_fibonacci_retracement_bullish(self):
        """Verificar retroceso Fibonacci entre 61.8% y 78.6%"""
        if self.last_swing_high is None or self.last_swing_low is None:
            return False
            
        current_price = float(self.data_close[0])
        swing_range = self.last_swing_high - self.last_swing_low
        
        if swing_range == 0:
            return False
            
        # Calcular niveles de Fibonacci
        fib_618 = self.last_swing_high - (swing_range * self.p.fib_min)
        fib_786 = self.last_swing_high - (swing_range * self.p.fib_max)
        
        # Verificar si el precio está en la zona de retroceso
        if fib_786 <= current_price <= fib_618:
            print(f"Retroceso Fibonacci: Precio {current_price:.5f} en zona {fib_786:.5f} - {fib_618:.5f}")
            return True
            
        return False

    def _is_macd_histogram_bullish(self):
        """Verificar que el histograma MACD reduzca su debilidad"""
        if len(self.macd.macd) < 3:
            return False
            
        # Calcular histograma
        hist_current = self.macd.macd[0] - self.macd.signal[0]
        hist_previous = self.macd.macd[-1] - self.macd.signal[-1]
        hist_prev2 = self.macd.macd[-2] - self.macd.signal[-2]
        
        # Verificar que el histograma esté mejorando (menos negativo o más positivo)
        if hist_previous < hist_prev2 and hist_current > hist_previous:
            print(f"MACD histograma mejorando: {hist_prev2:.5f} -> {hist_previous:.5f} -> {hist_current:.5f}")
            return True
            
        return False

    def _is_rsi_bullish_divergence(self):
        """Detectar divergencia alcista en RSI: mínimos más altos en RSI pese a precio más bajo"""
        if len(self.rsi) < 10:
            return False
            
        # Verificar que RSI esté por encima de 30
        if self.rsi[0] < 30:
            return False
            
        # Buscar divergencia en las últimas 10 velas
        rsi_values = [self.rsi[i] for i in range(min(10, len(self.rsi)))]
        price_values = [self.data_close[i] for i in range(min(10, len(self.data_close)))]
        
        # Buscar dos mínimos en RSI y precio
        rsi_minima = []
        price_minima = []
        
        for i in range(1, len(rsi_values)-1):
            if rsi_values[i] < rsi_values[i-1] and rsi_values[i] < rsi_values[i+1]:
                rsi_minima.append((i, rsi_values[i]))
                price_minima.append((i, price_values[i]))
        
        # Verificar divergencia: RSI mínimos más altos, precio mínimos más bajos
        if len(rsi_minima) >= 2 and len(price_minima) >= 2:
            rsi1, rsi2 = rsi_minima[-2], rsi_minima[-1]
            price1, price2 = price_minima[-2], price_minima[-1]
            
            if rsi2[1] > rsi1[1] and price2[1] < price1[1]:
                print(f"Divergencia alcista RSI: RSI {rsi1[1]:.2f} -> {rsi2[1]:.2f}, Precio {price1[1]:.5f} -> {price2[1]:.5f}")
                return True
                
        return False

    def _update_15m_trend(self):
        """Actualizar tendencia de 15 minutos usando resampleo"""
        if len(self.df_buffer) < 3:  # Necesitamos al menos 15 minutos de datos
            return
            
        # Crear DataFrame de 15M
        df_5m = self._get_df()
        df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
        
        # Resamplear a 15M
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_15m = df_5m.resample('15min').agg(ohlc_dict).dropna()
        
        if len(df_15m) < 10:
            return
            
        # Calcular tendencia usando swing highs/lows
        swing_15m = smc.swing_highs_lows(df_15m, swing_length=self.p.swing_length)
        if swing_15m is not None and not swing_15m.empty:
            trend_15m = smc.trend_indicator(df_15m, swing_15m)
            if 'Trend' in trend_15m.columns:
                self.trend_15m = trend_15m['Trend'].iloc[-1] if not trend_15m.empty else 0

    def _is_fvg_bullish_setup(self):
        """Detectar Fair Value Gap alcista: gap entre high de vela N y low de vela N+1"""
        if len(self.df_buffer) < 3:
            return False
            
        # Buscar FVG en las últimas N velas
        for i in range(min(self.p.fvg_lookback, len(self.df_buffer)-1)):
            if i == 0:
                continue
                
            # Obtener datos de velas consecutivas
            vela_n = list(self.df_buffer)[-(i+2)]
            vela_n1 = list(self.df_buffer)[-(i+1)]
            
            # Verificar si hay gap alcista
            gap_high = vela_n['high']
            gap_low = vela_n1['low']
            
            if gap_low > gap_high:  # Gap alcista
                gap_size = gap_low - gap_high
                
                if gap_size >= self.p.fvg_min_size:
                    # Calcular zona media del FVG
                    fvg_mid = (gap_high + gap_low) / 2
                    
                    # Guardar información del FVG
                    fvg_info = {
                        'gap_high': gap_high,
                        'gap_low': gap_low,
                        'fvg_mid': fvg_mid,
                        'gap_size': gap_size,
                        'vela_index': len(self.df_buffer) - i - 2
                    }
                    
                    self.fair_value_gaps.append(fvg_info)
                    print(f"FVG alcista detectado: Gap {gap_high:.5f} - {gap_low:.5f}, Medio: {fvg_mid:.5f}")
                    return True
                    
        return False

    def _is_fvg_filled(self):
        """Verificar si el precio ha tocado la zona media del FVG"""
        if not self.fair_value_gaps:
            return False
            
        current_price = float(self.data_close[0])
        
        # Verificar el FVG más reciente
        latest_fvg = self.fair_value_gaps[-1]
        fvg_mid = latest_fvg['fvg_mid']
        
        # Verificar si el precio ha tocado la zona media (con tolerancia)
        tolerance = latest_fvg['gap_size'] * 0.1  # 10% del tamaño del gap
        zone_low = fvg_mid - tolerance
        zone_high = fvg_mid + tolerance
        
        if zone_low <= current_price <= zone_high:
            print(f"FVG rellenado: Precio {current_price:.5f} en zona {zone_low:.5f} - {zone_high:.5f}")
            return True
            
        return False

    def _is_macd_crossover_near_fvg(self):
        """Verificar MACD crossover cerca de la zona del FVG"""
        if not self.fair_value_gaps or len(self.macd.macd) < 2:
            return False
            
        # Verificar crossover alcista reciente
        if self._is_macd_bullish_crossover():
            # Verificar que el crossover ocurrió cerca del FVG
            latest_fvg = self.fair_value_gaps[-1]
            fvg_mid = latest_fvg['fvg_mid']
            current_price = float(self.data_close[0])
            
            # Tolerancia para considerar "cerca"
            tolerance = latest_fvg['gap_size'] * 0.2  # 20% del tamaño del gap
            
            if abs(current_price - fvg_mid) <= tolerance:
                print(f"MACD crossover cerca del FVG: Precio {current_price:.5f}, FVG medio {fvg_mid:.5f}")
                return True
                
        return False

    def _is_rsi_bullish_reaction(self):
        """Verificar reacción alcista del RSI en zona 50-60"""
        if len(self.rsi) < 3:
            return False
            
        current_rsi = self.rsi[0]
        prev_rsi = self.rsi[-1]
        prev2_rsi = self.rsi[-2]
        
        # Verificar que RSI esté en zona 50-60
        if 50 <= current_rsi <= 60:
            # Verificar giro alcista (RSI aumentando)
            if current_rsi > prev_rsi and prev_rsi > prev2_rsi:
                print(f"RSI reacción alcista: {prev2_rsi:.2f} -> {prev_rsi:.2f} -> {current_rsi:.2f}")
                return True
                
        return False

    def _check_no_unmitigated_fvg_15m(self):
        """Verificar que no haya FVG sin mitigar en niveles superiores (15M)"""
        if len(self.df_buffer) < 12:  # Necesitamos suficientes datos
            return True  # Si no hay suficientes datos, asumimos que no hay FVG sin mitigar
            
        # Crear DataFrame de 15M
        df_5m = self._get_df()
        df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
        
        # Resamplear a 15M
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_15m = df_5m.resample('15min').agg(ohlc_dict).dropna()
        
        if len(df_15m) < 5:
            return True
            
        current_price = float(self.data_close[0])
        
        # Buscar FVG sin mitigar en 15M
        for i in range(len(df_15m)-1):
            vela_n = df_15m.iloc[i]
            vela_n1 = df_15m.iloc[i+1]
            
            # Verificar gap alcista
            if vela_n1['low'] > vela_n['high']:
                gap_high = vela_n['high']
                gap_low = vela_n1['low']
                
                # Verificar si el gap está por encima del precio actual y sin mitigar
                if gap_low > current_price:
                    # Verificar si el precio ha tocado el gap
                    if current_price < gap_high:
                        print(f"⚠️ FVG sin mitigar detectado en 15M: {gap_high:.5f} - {gap_low:.5f}")
                        return False
                        
        return True

    def _is_high_volume(self, window=20):
        """Verificar si el volumen actual es alto comparado con el promedio"""
        if len(self.data_close) < window + 1:
            return False
        vol_array = np.array(self.data_volume.get(size=len(self.data_volume)))
        avg_vol = np.mean(vol_array[-window-1:-1])  # promedio de las N anteriores, excluyendo la actual
        is_high = vol_array[-1] > avg_vol * 1.5  # 50% más alto que el promedio
        if is_high:
            print(f"Volumen alto: {vol_array[-1]} > {avg_vol * 1.5}")
        return is_high

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

    # ===== NUEVOS MÉTODOS DE GESTIÓN DE RIESGO =====

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

    def _get_order_block_sl_buy(self):
        """Buscar Order Block alcista más cercano para SL de compra"""
        if not hasattr(self, 'order_blocks_1h') or self.order_blocks_1h is None or self.order_blocks_1h.empty:
            return None
        
        try:
            current_price = float(self.data_close[0])
            
            # Buscar Order Block alcista más cercano por debajo del precio actual
            if 'OB' in self.order_blocks_1h.columns and 'Bottom' in self.order_blocks_1h.columns:
                bullish_obs = self.order_blocks_1h[self.order_blocks_1h['OB'].notna()]
                valid_obs = bullish_obs[bullish_obs['Bottom'] < current_price]
                
                if not valid_obs.empty:
                    # Tomar el Order Block más cercano al precio actual
                    closest_ob = valid_obs.iloc[(valid_obs['Bottom'] - current_price).abs().argsort()[:1]]
                    return closest_ob['Bottom'].iloc[0]
        except Exception as e:
            print(f"Error en _get_order_block_sl_buy: {e}")
        
        return None

    def _get_order_block_sl_sell(self):
        """Buscar Order Block bajista más cercano para SL de venta"""
        if not hasattr(self, 'order_blocks_1h') or self.order_blocks_1h is None or self.order_blocks_1h.empty:
            return None
        
        try:
            current_price = float(self.data_close[0])
            
            # Buscar Order Block bajista más cercano por encima del precio actual
            if 'OB' in self.order_blocks_1h.columns and 'Top' in self.order_blocks_1h.columns:
                bearish_obs = self.order_blocks_1h[self.order_blocks_1h['OB'].notna()]
                valid_obs = bearish_obs[bearish_obs['Top'] > current_price]
                
                if not valid_obs.empty:
                    # Tomar el Order Block más cercano al precio actual
                    closest_ob = valid_obs.iloc[(valid_obs['Top'] - current_price).abs().argsort()[:1]]
                    return closest_ob['Top'].iloc[0]
        except Exception as e:
            print(f"Error en _get_order_block_sl_sell: {e}")
        
        return None

    def _get_swing_low_sl_buy(self):
        """Buscar swing low más cercano para SL de compra"""
        if self.swing_highs_lows is not None and not self.swing_highs_lows.empty:
            try:
                current_price = float(self.data_close[0])
                
                if 'type' in self.swing_highs_lows.columns:
                    swing_lows = self.swing_highs_lows[self.swing_highs_lows['type'] == 'low']
                    valid_lows = swing_lows[swing_lows['low'] < current_price]
                    
                    if not valid_lows.empty:
                        closest_low = valid_lows.iloc[(valid_lows['low'] - current_price).abs().argsort()[:1]]
                        return closest_low['low'].iloc[0]
                else:
                    if 'low' in self.swing_highs_lows.columns:
                        return self.swing_highs_lows['low'].min()
            except Exception as e:
                print(f"Error en _get_swing_low_sl_buy: {e}")
        
        return None

    def _get_swing_high_sl_sell(self):
        """Buscar swing high más cercano para SL de venta"""
        if self.swing_highs_lows is not None and not self.swing_highs_lows.empty:
            try:
                current_price = float(self.data_close[0])
                
                if 'type' in self.swing_highs_lows.columns:
                    swing_highs = self.swing_highs_lows[self.swing_highs_lows['type'] == 'high']
                    valid_highs = swing_highs[swing_highs['high'] > current_price]
                    
                    if not valid_highs.empty:
                        closest_high = valid_highs.iloc[(valid_highs['high'] - current_price).abs().argsort()[:1]]
                        return closest_high['high'].iloc[0]
                else:
                    if 'high' in self.swing_highs_lows.columns:
                        return self.swing_highs_lows['high'].max()
            except Exception as e:
                print(f"Error en _get_swing_high_sl_sell: {e}")
        
        return None

    def _get_swing_high_tp_buy(self):
        """Buscar swing high en 15M para TP1 de compra"""
        try:
            # Crear DataFrame de 15M
            df_5m = self._get_df()
            df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
            
            # Resamplear a 15M
            ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
            df_15m = df_5m.resample('15min').agg(ohlc_dict).dropna()
            
            if len(df_15m) < 10:
                return None
            
            # Calcular swing highs en 15M
            swing_15m = smc.swing_highs_lows(df_15m, swing_length=self.p.swing_length)
            if swing_15m is not None and not swing_15m.empty:
                if 'type' in swing_15m.columns:
                    swing_highs = swing_15m[swing_15m['type'] == 'high']
                    if not swing_highs.empty:
                        return swing_highs['high'].iloc[-1]  # Último swing high
                else:
                    if 'high' in swing_15m.columns:
                        return swing_15m['high'].max()
        except Exception as e:
            print(f"Error en _get_swing_high_tp_buy: {e}")
        
        return None

    def _get_swing_low_tp_sell(self):
        """Buscar swing low en 15M para TP1 de venta"""
        try:
            # Crear DataFrame de 15M
            df_5m = self._get_df()
            df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
            
            # Resamplear a 15M
            df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
            
            # Resamplear a 15M
            ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
            df_15m = df_5m.resample('15min').agg(ohlc_dict).dropna()
            
            if len(df_15m) < 10:
                return None
            
            # Calcular swing lows en 15M
            swing_15m = smc.swing_highs_lows(df_15m, swing_length=self.p.swing_length)
            if swing_15m is not None and not swing_15m.empty:
                if 'type' in swing_15m.columns:
                    swing_lows = swing_15m[swing_15m['type'] == 'low']
                    if not swing_lows.empty:
                        return swing_lows['low'].iloc[-1]  # Último swing low
                else:
                    if 'low' in swing_15m.columns:
                        return swing_15m['low'].min()
        except Exception as e:
            print(f"Error en _get_swing_low_tp_sell: {e}")
        
        return None

    def _get_breaker_block_tp_buy(self):
        """Buscar Breaker Block en 15M/1H para TP2 de compra"""
        # Implementación simplificada - buscar en Order Blocks existentes
        if hasattr(self, 'order_blocks_1h') and self.order_blocks_1h is not None and not self.order_blocks_1h.empty:
            try:
                current_price = float(self.data_close[0])
                
                if 'OB' in self.order_blocks_1h.columns and 'Top' in self.order_blocks_1h.columns:
                    # Buscar Order Block por encima del precio actual (potencial resistencia)
                    bullish_obs = self.order_blocks_1h[self.order_blocks_1h['OB'].notna()]
                    valid_obs = bullish_obs[bullish_obs['Top'] > current_price]
                    
                    if not valid_obs.empty:
                        # Tomar el más cercano
                        closest_ob = valid_obs.iloc[(valid_obs['Top'] - current_price).abs().argsort()[:1]]
                        return closest_ob['Top'].iloc[0]
            except Exception as e:
                print(f"Error en _get_breaker_block_tp_buy: {e}")
        
        return None

    def _get_breaker_block_tp_sell(self):
        """Buscar Breaker Block en 15M/1H para TP2 de venta"""
        # Implementación simplificada - buscar en Order Blocks existentes
        if hasattr(self, 'order_blocks_1h') and self.order_blocks_1h is not None and not self.order_blocks_1h.empty:
            try:
                current_price = float(self.data_close[0])
                
                if 'OB' in self.order_blocks_1h.columns and 'Bottom' in self.order_blocks_1h.columns:
                    # Buscar Order Block por debajo del precio actual (potencial soporte)
                    bearish_obs = self.order_blocks_1h[self.order_blocks_1h['OB'].notna()]
                    valid_obs = bearish_obs[bearish_obs['Bottom'] < current_price]
                    
                    if not valid_obs.empty:
                        # Tomar el más cercano
                        closest_ob = valid_obs.iloc[(valid_obs['Bottom'] - current_price).abs().argsort()[:1]]
                        return closest_ob['Bottom'].iloc[0]
            except Exception as e:
                print(f"Error en _get_breaker_block_tp_sell: {e}")
        
        return None

    def _update_trailing_stop(self):
        """Actualizar trailing stop según las reglas especificadas"""
        if not self.position:
            return
        
        current_price = float(self.data_close[0])
        entry_price = self.position.price
        
        # Calcular porcentaje de ganancia
        if self.position.size > 0:  # Posición larga
            profit_pct = (current_price - entry_price) / entry_price * 100
            tp1 = self._get_tp1_buy(entry_price)
            
            if tp1 is None:
                return
            
            # Calcular porcentaje hacia TP1
            tp1_pct = (tp1 - entry_price) / entry_price * 100
            progress_pct = (profit_pct / tp1_pct) * 100 if tp1_pct > 0 else 0
            
            # Regla 1: Tras alcanzar 50% de TP, mover SL a break-even
            if progress_pct >= 50 and self.sl_order and self.sl_order.price < entry_price:
                new_sl = entry_price * 1.001  # Justo por encima del break-even
                self.broker.cancel(self.sl_order)
                self.sl_order = self.sell(exectype=bt.Order.Stop, price=new_sl, size=self.position.size)
                print(f"🔄 Trailing Stop: Movido a break-even ({new_sl:.5f})")
            
            # Regla 2: Cuando alcance TP1, mover SL a la mitad del TP1 y punto de salida
            elif current_price >= tp1 and self.sl_order:
                mid_point = (entry_price + tp1) / 2
                new_sl = mid_point * 1.001  # Justo por encima del punto medio
                self.broker.cancel(self.sl_order)
                self.sl_order = self.sell(exectype=bt.Order.Stop, price=new_sl, size=self.position.size)
                print(f"🔄 Trailing Stop: Movido a punto medio ({new_sl:.5f})")
        
        elif self.position.size < 0:  # Posición corta
            profit_pct = (entry_price - current_price) / entry_price * 100
            tp1 = self._get_tp1_sell(entry_price)
            
            if tp1 is None:
                return
            
            # Calcular porcentaje hacia TP1
            tp1_pct = (entry_price - tp1) / entry_price * 100
            progress_pct = (profit_pct / tp1_pct) * 100 if tp1_pct > 0 else 0
            
            # Regla 1: Tras alcanzar 50% de TP, mover SL a break-even
            if progress_pct >= 50 and self.sl_order and self.sl_order.price > entry_price:
                new_sl = entry_price * 0.999  # Justo por debajo del break-even
                self.broker.cancel(self.sl_order)
                self.sl_order = self.buy(exectype=bt.Order.Stop, price=new_sl, size=abs(self.position.size))
                print(f"🔄 Trailing Stop: Movido a break-even ({new_sl:.5f})")
            
            # Regla 2: Cuando alcance TP1, mover SL a la mitad del TP1 y punto de salida
            elif current_price <= tp1 and self.sl_order:
                mid_point = (entry_price + tp1) / 2
                new_sl = mid_point * 0.999  # Justo por debajo del punto medio
                self.broker.cancel(self.sl_order)
                self.sl_order = self.buy(exectype=bt.Order.Stop, price=new_sl, size=abs(self.position.size))
                print(f"🔄 Trailing Stop: Movido a punto medio ({new_sl:.5f})")

    def _get_sl_buy(self, entry_price):
        """
        Stop Loss para compras: 
        - Ubicación: Justo por debajo del mínimo del Order Block
        - Buffer: 1.5× ATR(14) para evitar salidas prematuras
        - Considera el más alejado para estar protegidos
        """
        # Calcular ATR para el buffer de volatilidad
        atr = self._calculate_atr(14)
        atr_buffer = atr * 1.5
        
        # Buscar Order Block alcista más cercano
        ob_sl = self._get_order_block_sl_buy()
        
        # Buscar swing low más cercano
        swing_sl = self._get_swing_low_sl_buy()
        
        # Tomar el más alejado (más conservador)
        if ob_sl is not None and swing_sl is not None:
            sl_price = min(ob_sl, swing_sl)  # El más bajo es más conservador
        elif ob_sl is not None:
            sl_price = ob_sl
        elif swing_sl is not None:
            sl_price = swing_sl
        else:
            # Fallback: 2% del precio de entrada
            sl_price = entry_price * 0.98
        
        # Aplicar buffer de ATR
        final_sl = sl_price - atr_buffer
        
        print(f"SL Compra: OB/Swing={sl_price:.5f}, ATR Buffer={atr_buffer:.5f}, Final={final_sl:.5f}")
        return final_sl

    def _get_sl_sell(self, entry_price):
        """
        Stop Loss para ventas:
        - Ubicación: Justo por encima del máximo del Order Block
        - Buffer: 1.5× ATR(14) para evitar salidas prematuras
        - Considera el más alejado para estar protegidos
        """
        # Calcular ATR para el buffer de volatilidad
        atr = self._calculate_atr(14)
        atr_buffer = atr * 1.5
        
        # Buscar Order Block bajista más cercano
        ob_sl = self._get_order_block_sl_sell()
        
        # Buscar swing high más cercano
        swing_sl = self._get_swing_high_sl_sell()
        
        # Tomar el más alejado (más conservador)
        if ob_sl is not None and swing_sl is not None:
            sl_price = max(ob_sl, swing_sl)  # El más alto es más conservador
        elif ob_sl is not None:
            sl_price = ob_sl
        elif swing_sl is not None:
            sl_price = swing_sl
        else:
            # Fallback: 2% del precio de entrada
            sl_price = entry_price * 1.02
        
        # Aplicar buffer de ATR
        final_sl = sl_price + atr_buffer
        
        print(f"SL Venta: OB/Swing={sl_price:.5f}, ATR Buffer={atr_buffer:.5f}, Final={final_sl:.5f}")
        return final_sl

    def _get_tp1_buy(self, entry_price):
        """
        Take Profit 1 para compras: 
        Nivel del swing high en timeframe superior (15M) donde confluyan estructuras relevantes
        """
        tp1 = self._get_swing_high_tp_buy()
        if tp1 is None:
            # Fallback: 1:2 RR
            risk = entry_price - self._get_sl_buy(entry_price)
            tp1 = entry_price + (risk * 2)
        
        print(f"TP1 Compra: Swing High 15M={tp1:.5f}")
        return tp1

    def _get_tp2_buy(self, entry_price):
        """
        Take Profit 2 para compras: 
        Zonas clave en mitigación o Breaker Block identificado en 15M/1H
        """
        tp2 = self._get_breaker_block_tp_buy()
        if tp2 is None:
            # Fallback: 5% del precio de entrada
            tp2 = entry_price * 1.05
        
        print(f"TP2 Compra: Breaker Block={tp2:.5f}")
        return tp2

    def _get_tp1_sell(self, entry_price):
        """
        Take Profit 1 para ventas: 
        Nivel del swing low en timeframe superior (15M) donde confluyan estructuras relevantes
        """
        tp1 = self._get_swing_low_tp_sell()
        if tp1 is None:
            # Fallback: 1:2 RR
            risk = self._get_sl_sell(entry_price) - entry_price
            tp1 = entry_price - (risk * 2)
        
        print(f"TP1 Venta: Swing Low 15M={tp1:.5f}")
        return tp1

    def _get_tp2_sell(self, entry_price):
        """
        Take Profit 2 para ventas: 
        Zonas clave en mitigación o Breaker Block identificado en 15M/1H
        """
        tp2 = self._get_breaker_block_tp_sell()
        if tp2 is None:
            # Fallback: 5% del precio de entrada
            tp2 = entry_price * 0.95
        
        print(f"TP2 Venta: Breaker Block={tp2:.5f}")
        return tp2 

    def _update_fibonacci_levels(self):
        """Actualizar niveles de Fibonacci y Order Blocks para visualización"""
        if self.last_swing_high is not None and self.last_swing_low is not None:
            swing_range = self.last_swing_high - self.last_swing_low
            
            # Calcular niveles de Fibonacci
            fib_618_level = self.last_swing_high - (swing_range * 0.618)
            fib_786_level = self.last_swing_high - (swing_range * 0.786)
            
            # Actualizar líneas de Fibonacci
            self.fibonacci.lines.fib_618[0] = fib_618_level
            self.fibonacci.lines.fib_786[0] = fib_786_level
            
            # Actualizar Order Blocks (usar los mismos niveles que los swings)
            self.order_block_indicator.lines.ob_high[0] = self.last_swing_high
            self.order_block_indicator.lines.ob_low[0] = self.last_swing_low
        else:
            # Si no hay swings, usar valores nulos
            self.fibonacci.lines.fib_618[0] = float('nan')
            self.fibonacci.lines.fib_786[0] = float('nan')
            self.order_block_indicator.lines.ob_high[0] = float('nan')
            self.order_block_indicator.lines.ob_low[0] = float('nan')

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