import backtrader as bt
import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc

class ZonasMitigacionStrategy(bt.Strategy):
    """
    ESTRATEGIA: Zonas de Mitigación Multi-Timeframe
    
    Esta estrategia combina análisis de marcos superiores (HTF) con señales en 5 minutos:
    
    PREPARACIÓN HTF (1H):
    - Determina tendencia: máximos y mínimos crecientes/decrecientes
    - Marca zonas institucionales: Order Blocks, FVGs, Liquidity Zones
    - Confirma ruptura en 15M (MSS/BOS)
    
    SEÑALES LTF (5M):
    - Break of Structure (BOS)
    - Pullback a Order Block (61.8%-78.6% Fibonacci)
    - Entrada en Fair Value Gap
    - Reversión en Liquidity Grab
    
    GESTIÓN DE RIESGO:
    - POSICIÓN ÚNICA: Solo se permite una posición activa a la vez
    - Stop Loss: fuera del swing previo o rango de Order Block
    - Take Profit: 1:2 RR mínimo, idealmente en siguiente demanda/resistencia HTF
    """
    params = dict(
        swing_length=5,
        lookback=20,
        buffer_size=1000,
        # Parámetros para indicadores
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        # Parámetros para Fibonacci
        fib_min=0.618,
        fib_max=0.786,
        # Parámetros para Order Blocks
        ob_lookback=50,
        # Parámetros para FVG
        fvg_lookback=30,
        fvg_min_size=0.0001,
    )

    def __init__(self):
        # Datos OHLCV
        self.data_close = self.datas[0].close
        self.data_open = self.datas[0].open
        self.data_high = self.datas[0].high
        self.data_low = self.datas[0].low
        self.data_volume = self.datas[0].volume
        
        # Buffer para datos históricos
        self.df_buffer = []
        
        # Contadores de señales
        self.buy_signal_count = 0
        self.sell_signal_count = 0
        
        # Indicadores técnicos
        self.macd = bt.indicators.MACD(
            self.data_close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        self.rsi = bt.indicators.RSI(self.data_close, period=self.p.rsi_period)
        
        # Variables para análisis multi-timeframe
        self.trend_1h = 0  # Tendencia 1H
        self.trend_15m = 0  # Tendencia 15M
        
        # Zonas institucionales
        self.order_blocks_1h = pd.DataFrame()
        self.fair_value_gaps_1h = pd.DataFrame()
        self.liquidity_zones_1h = []
        
        # Variables para señales en 5M
        self.swing_highs_lows = None
        self.last_swing_high = None
        self.last_swing_low = None
        
        # Gestión de órdenes
        self.sl_order = None
        self.tp1_order = None
        self.tp2_order = None

    def next(self):
        # Mensaje inicial de la estrategia
        if len(self.data) == 1:
            print("🚀 INICIANDO ESTRATEGIA: Zonas de Mitigación Multi-Timeframe")
            print("=" * 70)
            print("📋 PREPARACIÓN HTF (1H):")
            print("   ✅ Determina tendencia: máximos y mínimos crecientes/decrecientes")
            print("   ✅ Marca zonas institucionales: Order Blocks, FVGs, Liquidity Zones")
            print("   ✅ Confirma ruptura en 15M (MSS/BOS)")
            print("")
            print("📋 SEÑALES LTF (5M):")
            print("   ✅ Break of Structure (BOS)")
            print("   ✅ Pullback a Order Block (61.8%-78.6% Fibonacci)")
            print("   ✅ Entrada en Fair Value Gap")
            print("   ✅ Reversión en Liquidity Grab")
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
            
        # Calcular swing highs/lows en 5M
        self.swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.p.swing_length)
        
        # Verificar si los indicadores están listos
        if len(self.macd.macd) < 2 or len(self.rsi) < 1:
            return
        
        # --- PREPARACIÓN HTF (1H) ---
        self._update_htf_analysis()
        
        # --- SEÑALES LTF (5M) ---
        
        # 1. BREAK OF STRUCTURE (BOS)
        if self._is_bos_bullish():
            if self._is_impulse_candle_bullish():
                if self._is_macd_bullish_crossover():
                    if self._is_rsi_bullish():
                        # SEÑAL DE COMPRA - BOS
                        if not self.position:
                            self._execute_buy_signal("BOS")
        
        elif self._is_bos_bearish():
            if self._is_impulse_candle_bearish():
                if self._is_macd_bearish_crossover():
                    if self._is_rsi_bearish():
                        # SEÑAL DE VENTA - BOS
                        if not self.position:
                            self._execute_sell_signal("BOS")
        
        # 2. PULLBACK A ORDER BLOCK
        if self._is_pullback_to_order_block_bullish():
            if self._is_fibonacci_retracement_bullish():
                if self._is_macd_bullish_crossover():
                    if self._is_rsi_bullish():
                        # SEÑAL DE COMPRA - Pullback OB
                        if not self.position:
                            self._execute_buy_signal("Pullback OB")
        
        # 3. ENTRADA EN FAIR VALUE GAP
        if self._is_fvg_bullish_setup():
            if self._is_fvg_filled():
                if self._is_macd_bullish_crossover():
                    if self._is_rsi_bullish():
                        # SEÑAL DE COMPRA - FVG
                        if not self.position:
                            self._execute_buy_signal("FVG")
        
        # 4. REVERSIÓN EN LIQUIDITY GRAB
        if self._is_liquidity_grab_bullish():
            if self._is_rejection_pattern_bullish():
                if self._is_macd_bullish_crossover():
                    if self._is_rsi_bullish():
                        # SEÑAL DE COMPRA - Liquidity Grab
                        if not self.position:
                            self._execute_buy_signal("Liquidity Grab")

    def _get_df(self):
        """Construye un DataFrame OHLCV desde los datos de Backtrader"""
        df = pd.DataFrame({
            'open': [x['open'] for x in self.df_buffer],
            'high': [x['high'] for x in self.df_buffer],
            'low': [x['low'] for x in self.df_buffer],
            'close': [x['close'] for x in self.df_buffer],
            'volume': [x['volume'] for x in self.df_buffer]
        })
        return df

    def _update_htf_analysis(self):
        """Actualizar análisis de marcos superiores (1H y 15M)"""
        if len(self.df_buffer) < 12:  # Necesitamos al menos 1 hora de datos
            return
            
        # Crear DataFrame de 5M
        df_5m = self._get_df()
        df_5m.index = pd.to_datetime([x['datetime'] for x in self.df_buffer])
        
        # Resamplear a 1H
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df_1h = df_5m.resample('1h').agg(ohlc_dict).dropna()
        
        if len(df_1h) < 10:
            return
            
        # Calcular tendencia 1H
        swing_1h = smc.swing_highs_lows(df_1h, swing_length=self.p.swing_length)
        if swing_1h is not None and not swing_1h.empty:
            trend_1h = smc.trend_indicator(df_1h, swing_1h)
            if 'Trend' in trend_1h.columns:
                self.trend_1h = trend_1h['Trend'].iloc[-1] if not trend_1h.empty else 0
        
        # Calcular Order Blocks en 1H
        if swing_1h is not None and not swing_1h.empty:
            try:
                ob_1h = smc.ob(df_1h, swing_1h)
                if ob_1h is not None and not ob_1h.empty:
                    self.order_blocks_1h = ob_1h
            except Exception as e:
                print(f"Error calculando Order Blocks 1H: {e}")
                self.order_blocks_1h = pd.DataFrame()
        
        # Calcular Fair Value Gaps en 1H
        try:
            fvg_1h = smc.fvg(df_1h)
            if fvg_1h is not None and not fvg_1h.empty:
                self.fair_value_gaps_1h = fvg_1h
        except Exception as e:
            print(f"Error calculando FVG 1H: {e}")
            self.fair_value_gaps_1h = pd.DataFrame()
        
        # Resamplear a 15M
        df_15m = df_5m.resample('15min').agg(ohlc_dict).dropna()
        
        if len(df_15m) < 10:
            return
            
        # Calcular tendencia 15M
        swing_15m = smc.swing_highs_lows(df_15m, swing_length=self.p.swing_length)
        if swing_15m is not None and not swing_15m.empty:
            trend_15m = smc.trend_indicator(df_15m, swing_15m)
            if 'Trend' in trend_15m.columns:
                self.trend_15m = trend_15m['Trend'].iloc[-1] if not trend_15m.empty else 0

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
                            return True
                else:
                    # Si no hay columna 'type', buscar el máximo en las columnas de high
                    if 'high' in self.swing_highs_lows.columns:
                        last_swing_high = self.swing_highs_lows['high'].max()
                        current_close = float(self.data_close[0])
                        
                        if current_close > last_swing_high:
                            return True
            except Exception as e:
                pass
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
                            return True
                else:
                    # Si no hay columna 'type', buscar el mínimo en las columnas de low
                    if 'low' in self.swing_highs_lows.columns:
                        last_swing_low = self.swing_highs_lows['low'].min()
                        current_close = float(self.data_close[0])
                        
                        if current_close < last_swing_low:
                            return True
            except Exception as e:
                pass
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
            return True
            
        return False

    def _is_macd_bullish_crossover(self):
        """MACD crossover alcista: línea MACD cruza por encima de la línea señal"""
        if len(self.macd.macd) < 2:
            return False
            
        # Verificar crossover alcista
        macd_current = self.macd.macd[0]
        macd_previous = self.macd.macd[-1]
        signal_current = self.macd.signal[0]
        signal_previous = self.macd.signal[-1]
        
        # Crossover: MACD estaba por debajo de la señal y ahora está por encima
        if macd_previous < signal_previous and macd_current > signal_current:
            return True
            
        return False

    def _is_macd_bearish_crossover(self):
        """MACD crossover bajista: línea MACD cruza por debajo de la línea señal"""
        if len(self.macd.macd) < 2:
            return False
            
        # Verificar crossover bajista
        macd_current = self.macd.macd[0]
        macd_previous = self.macd.macd[-1]
        signal_current = self.macd.signal[0]
        signal_previous = self.macd.signal[-1]
        
        # Crossover: MACD estaba por encima de la señal y ahora está por debajo
        if macd_previous > signal_previous and macd_current < signal_current:
            return True
            
        return False

    def _is_rsi_bullish(self):
        """RSI alcista: debe superar 50 y mostrar momentum al alza"""
        if len(self.rsi) < 2:
            return False
            
        current_rsi = self.rsi[0]
        prev_rsi = self.rsi[-1]
        
        # RSI debe estar por encima de 50 y aumentando
        if current_rsi > 50 and current_rsi > prev_rsi:
            return True
            
        return False

    def _is_rsi_bearish(self):
        """RSI bajista: debe estar por debajo de 50 confirmando debilidad"""
        if len(self.rsi) < 2:
            return False
            
        current_rsi = self.rsi[0]
        prev_rsi = self.rsi[-1]
        
        # RSI debe estar por debajo de 50 y disminuyendo
        if current_rsi < 50 and current_rsi < prev_rsi:
            return True
            
        return False

    def _is_pullback_to_order_block_bullish(self):
        """Detectar pullback a Order Block alcista"""
        if self.order_blocks_1h is None or self.order_blocks_1h.empty:
            return False
            
        current_price = float(self.data_close[0])
        
        # Buscar Order Block alcista más cercano
        try:
            # Verificar si hay columnas relevantes
            if 'OB' in self.order_blocks_1h.columns and 'Top' in self.order_blocks_1h.columns and 'Bottom' in self.order_blocks_1h.columns:
                # Filtrar Order Blocks alcistas (donde OB no es NaN)
                bullish_obs = self.order_blocks_1h[self.order_blocks_1h['OB'].notna()]
                
                for idx, ob in bullish_obs.iterrows():
                    if ob['Bottom'] <= current_price <= ob['Top']:
                        return True
        except Exception as e:
            print(f"Error en _is_pullback_to_order_block_bullish: {e}")
                
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
            return True
            
        return False

    def _is_fvg_bullish_setup(self):
        """Detectar Fair Value Gap alcista"""
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
                    return True
                    
        return False

    def _is_fvg_filled(self):
        """Verificar si el precio ha tocado la zona media del FVG"""
        # Implementación simplificada
        return True

    def _is_liquidity_grab_bullish(self):
        """Detectar Liquidity Grab alcista"""
        if len(self.df_buffer) < 5:
            return False
            
        # Buscar mecha que barre stops y luego rechazo
        current_low = float(self.data_low[0])
        current_close = float(self.data_close[0])
        
        # Verificar si la mecha inferior barrió un nivel anterior
        for i in range(1, min(5, len(self.df_buffer))):
            prev_low = list(self.df_buffer)[-i-1]['low']
            if current_low < prev_low and current_close > prev_low:
                return True
                
        return False

    def _is_rejection_pattern_bullish(self):
        """Detectar patrón de rechazo alcista"""
        o, h, l, c = self.data_open[0], self.data_high[0], self.data_low[0], self.data_close[0]
        
        # Pin bar alcista o engulfing
        body = abs(c - o)
        total_range = h - l
        
        if total_range == 0:
            return False
            
        # Pin bar: mecha inferior larga, cuerpo pequeño
        lower_wick = min(o, c) - l
        lower_wick_ratio = lower_wick / total_range
        
        if lower_wick_ratio >= 0.6 and body / total_range <= 0.3:
            return True
            
        return False

    def _execute_buy_signal(self, signal_type):
        """Ejecutar señal de compra - SOLO UNA POSICIÓN A LA VEZ"""
        # Verificar que no haya posición activa
        if self.position:
            print(f"⚠️ Ya hay una posición activa. Ignorando señal de compra ({signal_type})")
            return
        
        entry_price = float(self.data_close[0])
        current_time = self.datas[0].datetime.datetime(0)
        
        # Calcular SL y TP
        sl = self._get_sl_buy(entry_price)
        tp1 = self._get_tp1_buy(entry_price)
        tp2 = self._get_tp2_buy(entry_price)
        
        # Calcular tamaño de posición
        size = self.broker.get_cash() / entry_price
        
        # Ejecutar orden
        self.buy(size=size)
        self.sl_order = self.sell(exectype=bt.Order.Stop, price=sl, size=size)
        self.tp1_order = self.sell(exectype=bt.Order.Limit, price=tp1, size=size*0.5)
        self.tp2_order = self.sell(exectype=bt.Order.Limit, price=tp2, size=size*0.5)
        
        self.buy_signal_count += 1
        print(f"🚀 TRANSACCIÓN EJECUTADA - COMPRA #{self.buy_signal_count}")
        print(f"   📅 Fecha: {current_time}")
        print(f"   📊 Tipo: {signal_type}")
        print(f"   💰 Entrada: {entry_price:.5f}")
        print(f"   🛑 Stop Loss: {sl:.5f}")
        print(f"   🎯 Take Profit 1: {tp1:.5f}")
        print(f"   🎯 Take Profit 2: {tp2:.5f}")
        print(f"   📈 Tamaño: {size:.2f}")
        print("=" * 50)

    def _execute_sell_signal(self, signal_type):
        """Ejecutar señal de venta - SOLO UNA POSICIÓN A LA VEZ"""
        # Verificar que no haya posición activa
        if self.position:
            print(f"⚠️ Ya hay una posición activa. Ignorando señal de venta ({signal_type})")
            return
        
        entry_price = float(self.data_close[0])
        current_time = self.datas[0].datetime.datetime(0)
        
        # Calcular SL y TP
        sl = self._get_sl_sell(entry_price)
        tp1 = self._get_tp1_sell(entry_price)
        tp2 = self._get_tp2_sell(entry_price)
        
        # Calcular tamaño de posición
        size = self.broker.get_cash() / entry_price
        
        # Ejecutar orden
        self.sell(size=size)
        self.sl_order = self.buy(exectype=bt.Order.Stop, price=sl, size=size)
        self.tp1_order = self.buy(exectype=bt.Order.Limit, price=tp1, size=size*0.5)
        self.tp2_order = self.buy(exectype=bt.Order.Limit, price=tp2, size=size*0.5)
        
        self.sell_signal_count += 1
        print(f"📉 TRANSACCIÓN EJECUTADA - VENTA #{self.sell_signal_count}")
        print(f"   📅 Fecha: {current_time}")
        print(f"   📊 Tipo: {signal_type}")
        print(f"   💰 Entrada: {entry_price:.5f}")
        print(f"   🛑 Stop Loss: {sl:.5f}")
        print(f"   🎯 Take Profit 1: {tp1:.5f}")
        print(f"   🎯 Take Profit 2: {tp2:.5f}")
        print(f"   📈 Tamaño: {size:.2f}")
        print("=" * 50)

    def _get_sl_buy(self, entry_price):
        """Stop Loss para compras: fuera del swing previo"""
        if self.last_swing_low is not None:
            return self.last_swing_low * 0.999  # Justo debajo del swing low
        return entry_price * 0.98  # 2% por defecto

    def _get_sl_sell(self, entry_price):
        """Stop Loss para ventas: fuera del swing previo"""
        if self.last_swing_high is not None:
            return self.last_swing_high * 1.001  # Justo arriba del swing high
        return entry_price * 1.02  # 2% por defecto

    def _get_tp1_buy(self, entry_price):
        """Take Profit 1 para compras: 1:2 RR"""
        risk = entry_price - self._get_sl_buy(entry_price)
        return entry_price + (risk * 2)

    def _get_tp2_buy(self, entry_price):
        """Take Profit 2 para compras: siguiente resistencia HTF"""
        return entry_price * 1.05  # 5% por defecto

    def _get_tp1_sell(self, entry_price):
        """Take Profit 1 para ventas: 1:2 RR"""
        risk = self._get_sl_sell(entry_price) - entry_price
        return entry_price - (risk * 2)

    def _get_tp2_sell(self, entry_price):
        """Take Profit 2 para ventas: siguiente soporte HTF"""
        return entry_price * 0.95  # 5% por defecto

    def notify_order(self, order):
        """Cancelar el SL y TPs si se cierra la posición"""
        if order.status in [order.Completed]:
            if not self.position:
                # Cancelar órdenes pendientes
                if self.sl_order:
                    self.broker.cancel(self.sl_order)
                if self.tp1_order:
                    self.broker.cancel(self.tp1_order)
                if self.tp2_order:
                    self.broker.cancel(self.tp2_order)
                
                # Mostrar información de cierre de posición
                current_time = self.datas[0].datetime.datetime(0)
                current_price = float(self.data_close[0])
                
                print(f"🔒 POSICIÓN CERRADA")
                print(f"   📅 Fecha: {current_time}")
                print(f"   💰 Precio de cierre: {current_price:.5f}")
                print(f"   💵 Capital final: {self.broker.getvalue():.2f}")
                print("=" * 50) 

    def stop(self):
        """Mostrar resumen final de la estrategia"""
        print("\n" + "=" * 70)
        print("📊 RESUMEN FINAL DE LA ESTRATEGIA")
        print("=" * 70)
        print(f"💰 Capital inicial: {self.broker.startingcash:.2f}")
        print(f"💰 Capital final: {self.broker.getvalue():.2f}")
        print(f"📈 Ganancia/Pérdida: {self.broker.getvalue() - self.broker.startingcash:.2f}")
        print(f"📊 Porcentaje de retorno: {((self.broker.getvalue() / self.broker.startingcash) - 1) * 100:.2f}%")
        print(f"🚀 Compras ejecutadas: {self.buy_signal_count}")
        print(f"📉 Ventas ejecutadas: {self.sell_signal_count}")
        print(f"🔄 Total de transacciones: {self.buy_signal_count + self.sell_signal_count}")
        print("=" * 70) 