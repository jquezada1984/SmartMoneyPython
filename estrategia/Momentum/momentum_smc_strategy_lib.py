import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc

class MomentumSMCStrategyLib:
    """
    Librería independiente de MomentumSMCStrategy para análisis de señales de trading
    
    Esta clase proporciona las mismas funcionalidades que MomentumSMCStrategy
    pero sin depender de Backtrader, permitiendo su uso como librería pura.
    """
    
    def __init__(self, 
                 swing_length=5,
                 lookback=20,
                 macd_fast=12,
                 macd_slow=26,
                 macd_signal=9,
                 rsi_period=14,
                 ob_lookback=50,
                 fib_min=0.618,
                 fib_max=0.786,
                 fvg_lookback=30,
                 fvg_min_size=0.0001):
        
        self.swing_length = swing_length
        self.lookback = lookback
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.ob_lookback = ob_lookback
        self.fib_min = fib_min
        self.fib_max = fib_max
        self.fvg_lookback = fvg_lookback
        self.fvg_min_size = fvg_min_size
    
    def calculate_macd(self, df):
        """Calcular MACD: MACD Line, Signal Line, Histogram"""
        exp1 = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def calculate_rsi(self, df):
        """Calcular RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_atr(self, df, period=14):
        """Calcular ATR (Average True Range)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def analyze_strategy_1_bos_impulse(self, df):
        """
        ESTRATEGIA 1: BOS + VELA DE IMPULSO
        Detecta señales tanto alcistas (BUY) como bajistas (SELL)
        """
        signals = []
        
        # Calcular indicadores
        macd_line, signal_line, histogram = self.calculate_macd(df)
        rsi = self.calculate_rsi(df)
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
        bos_choch = smc.bos_choch(df, swing_highs_lows)
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_candle = df.iloc[i]
            body_size = abs(current_candle['close'] - current_candle['open'])
            total_range = current_candle['high'] - current_candle['low']
            
            if total_range > 0:
                body_percentage = body_size / total_range
                
                # Vela de impulso: cuerpo amplio (≥60%)
                if body_percentage >= 0.6:
                    # Señal de COMPRA
                    if not np.isnan(bos_choch['BOS'].iloc[-1]) and bos_choch['BOS'].iloc[-1] == 1:
                        # Verificar MACD crossover alcista
                        if (macd_line.iloc[i] > signal_line.iloc[i] and 
                            macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                            # Verificar RSI > 50
                            if rsi.iloc[i] > 50:
                                signals.append({
                                    'type': 'BUY',
                                    'strategy': 'BOS + Impulse',
                                    'index': i,
                                    'price': df['close'].iloc[i],
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_1(window_df, i, macd_line, signal_line, rsi)
                                })
                    
                    # Señal de VENTA
                    elif not np.isnan(bos_choch['BOS'].iloc[-1]) and bos_choch['BOS'].iloc[-1] == -1:
                        # Verificar MACD crossover bajista
                        if (macd_line.iloc[i] < signal_line.iloc[i] and 
                            macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                            # Verificar RSI < 50
                            if rsi.iloc[i] < 50:
                                signals.append({
                                    'type': 'SELL',
                                    'strategy': 'BOS + Impulse',
                                    'index': i,
                                    'price': df['close'].iloc[i],
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_1(window_df, i, macd_line, signal_line, rsi)
                                })
        
        return signals
    
    def analyze_strategy_2_order_block_fibonacci(self, df):
        """
        ESTRATEGIA 2: ORDER BLOCK + FIBONACCI
        Detecta señales tanto alcistas (BUY) como bajistas (SELL)
        """
        signals = []
        
        # Calcular indicadores
        macd_line, signal_line, histogram = self.calculate_macd(df)
        rsi = self.calculate_rsi(df)
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
        ob_data = smc.ob(df, swing_highs_lows)
        
        for i in range(10, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar Order Block alcista (BUY)
            if not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == 1:
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    retracement = (recent_high - current_price) / (recent_high - recent_low)
                    
                    # Retroceso entre 61.8% y 78.6%
                    if self.fib_min <= retracement <= self.fib_max:
                        # Verificar MACD histograma reduciendo debilidad
                        if (macd_line.iloc[i] - macd_line.iloc[i-1] > 
                            macd_line.iloc[i-1] - macd_line.iloc[i-2]):
                            # Verificar RSI > 30
                            if rsi.iloc[i] > 30:
                                signals.append({
                                    'type': 'BUY',
                                    'strategy': 'Order Block + Fibonacci',
                                    'index': i,
                                    'price': current_price,
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_2(window_df, i, macd_line, rsi, retracement)
                                })
            
            # Verificar Order Block bajista (SELL)
            elif not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == -1:
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    # Para ventas, calculamos el retroceso desde el mínimo
                    retracement = (current_price - recent_low) / (recent_high - recent_low)
                    
                    # Retroceso entre 61.8% y 78.6%
                    if self.fib_min <= retracement <= self.fib_max:
                        # Verificar MACD histograma aumentando debilidad
                        if (macd_line.iloc[i] - macd_line.iloc[i-1] < 
                            macd_line.iloc[i-1] - macd_line.iloc[i-2]):
                            # Verificar RSI < 70
                            if rsi.iloc[i] < 70:
                                signals.append({
                                    'type': 'SELL',
                                    'strategy': 'Order Block + Fibonacci',
                                    'index': i,
                                    'price': current_price,
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_2(window_df, i, macd_line, rsi, retracement)
                                })
        
        return signals
    
    def analyze_strategy_3_fair_value_gap(self, df):
        """
        ESTRATEGIA 3: FAIR VALUE GAP (FVG)
        Detecta señales tanto alcistas (BUY) como bajistas (SELL)
        """
        signals = []
        
        # Calcular indicadores
        macd_line, signal_line, histogram = self.calculate_macd(df)
        rsi = self.calculate_rsi(df)
        fvg_data = smc.fvg(df, join_consecutive=True)
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar FVG alcista (BUY)
            if not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == 1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    # Verificar MACD crossover alcista cerca del FVG
                    if (macd_line.iloc[i] > signal_line.iloc[i] and 
                        macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                        # Verificar RSI entre 50-60
                        if 50 <= rsi.iloc[i] <= 60:
                            signals.append({
                                'type': 'BUY',
                                'strategy': 'Fair Value Gap',
                                'index': i,
                                'price': current_price,
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_3(window_df, i, macd_line, signal_line, rsi)
                            })
            
            # Verificar FVG bajista (SELL)
            elif not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == -1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    # Verificar MACD crossover bajista cerca del FVG
                    if (macd_line.iloc[i] < signal_line.iloc[i] and 
                        macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                        # Verificar RSI entre 40-50 (zona bajista)
                        if 40 <= rsi.iloc[i] <= 50:
                            signals.append({
                                'type': 'SELL',
                                'strategy': 'Fair Value Gap',
                                'index': i,
                                'price': current_price,
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_3(window_df, i, macd_line, signal_line, rsi)
                            })
        
        return signals
    
    def precalculate_indicators(self, df):
        """
        Precalcula todos los indicadores comunes usados por las estrategias
        y visualización para evitar cálculos repetidos
        """
        # Indicadores básicos
        macd_line, signal_line, histogram = self.calculate_macd(df)
        rsi = self.calculate_rsi(df)
        
        # Swing highs/lows y patrones derivados
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
        bos_choch = smc.bos_choch(df, swing_highs_lows)
        ob_data = smc.ob(df, swing_highs_lows)
        fvg_data = smc.fvg(df, join_consecutive=True)
        
        # Indicadores adicionales para visualización
        liquidity_data = smc.liquidity(df, swing_highs_lows)
        previous_high_low_data = smc.previous_high_low(df, time_frame="4h")
        sessions_data = smc.sessions(df, session="London")
        retracements_data = smc.retracements(df, swing_highs_lows)
        trend_data = smc.trend_indicator(df, swing_highs_lows, lookback_period=20)
        
        return {
            # Indicadores básicos
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram,
            'rsi': rsi,
            
            # Patrones SMC principales
            'swing_highs_lows': swing_highs_lows,
            'bos_choch': bos_choch,
            'ob_data': ob_data,
            'fvg_data': fvg_data,
            
            # Indicadores adicionales
            'liquidity_data': liquidity_data,
            'previous_high_low_data': previous_high_low_data,
            'sessions_data': sessions_data,
            'retracements_data': retracements_data,
            'trend_data': trend_data
        }

    def analyze_strategy_1_bos_impulse_with_indicators(self, df, indicators):
        """Versión optimizada de analyze_strategy_1_bos_impulse que usa indicadores precalculados"""
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        rsi = indicators['rsi']
        bos_choch = indicators['bos_choch']
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_candle = df.iloc[i]
            body_size = abs(current_candle['close'] - current_candle['open'])
            total_range = current_candle['high'] - current_candle['low']
            
            if total_range > 0:
                body_percentage = body_size / total_range
                
                if body_percentage >= 0.6:
                    # Señal de COMPRA
                    if not np.isnan(bos_choch['BOS'].iloc[-1]) and bos_choch['BOS'].iloc[-1] == 1:
                        # Caso 1: Cruce 1-2 velas ANTES del BOS
                        cruce_previo = False
                        for j in range(1, 3):  # Buscar cruce en las últimas 2 velas
                            if i-j >= 0 and (macd_line.iloc[i-j] > signal_line.iloc[i-j] and 
                                           macd_line.iloc[i-j-1] <= signal_line.iloc[i-j-1]):
                                # Verificar que el cruce sigue vigente (no hay recorte)
                                histograma_subiendo = True
                                for k in range(i-j, i+1):
                                    if macd_line.iloc[k] - signal_line.iloc[k] < macd_line.iloc[k-1] - signal_line.iloc[k-1]:
                                        histograma_subiendo = False
                                        break
                                if histograma_subiendo:
                                    cruce_previo = True
                                    break
                        
                        # Caso 2: BOS primero y cruce 1-2 velas DESPUÉS
                        cruce_posterior = False
                        if i+2 < len(df):  # Asegurar que podemos mirar 2 velas adelante
                            for j in range(1, 3):  # Buscar cruce en las próximas 2 velas
                                if (macd_line.iloc[i+j] > signal_line.iloc[i+j] and 
                                    macd_line.iloc[i+j-1] <= signal_line.iloc[i+j-1]):
                                    # Verificar que el histograma ya viró positivo
                                    if macd_line.iloc[i] - signal_line.iloc[i] > macd_line.iloc[i-1] - signal_line.iloc[i-1]:
                                        cruce_posterior = True
                                        break
                        
                        # Verificar condiciones y generar señal
                        if (cruce_previo or cruce_posterior or 
                            (macd_line.iloc[i] > signal_line.iloc[i] and 
                             macd_line.iloc[i-1] <= signal_line.iloc[i-1])):
                            if rsi.iloc[i] > 50:
                                confidence_mod = 1.0
                                entry_type = 'coincidente'
                                
                                if cruce_previo:
                                    # Reducir confianza si el cruce es muy viejo
                                    velas_desde_cruce = i - (i-2)  # máximo 2 velas atrás
                                    if velas_desde_cruce > 3:
                                        confidence_mod = 0.8  # Señal más vieja, mejor esperar pullback
                                        entry_type = 'cruce_previo_pullback'
                                    else:
                                        entry_type = 'cruce_previo'
                                elif cruce_posterior:
                                    confidence_mod = 0.9  # Ligera reducción por ser cruce posterior
                                    entry_type = 'cruce_posterior'
                                
                                signals.append({
                                    'type': 'BUY',
                                    'strategy': 'BOS + Impulse',
                                    'index': i,
                                    'price': current_candle['close'],
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_1(window_df, i, macd_line, signal_line, rsi) * confidence_mod,
                                    'entry_type': entry_type
                                })
                    
                    # Señal de VENTA (aplicamos la misma lógica pero invertida)
                    elif not np.isnan(bos_choch['BOS'].iloc[-1]) and bos_choch['BOS'].iloc[-1] == -1:
                        # Caso 1: Cruce 1-2 velas ANTES del BOS
                        cruce_previo = False
                        for j in range(1, 3):
                            if i-j >= 0 and (macd_line.iloc[i-j] < signal_line.iloc[i-j] and 
                                           macd_line.iloc[i-j-1] >= signal_line.iloc[i-j-1]):
                                # Verificar que el cruce sigue vigente (no hay recorte)
                                histograma_bajando = True
                                for k in range(i-j, i+1):
                                    if macd_line.iloc[k] - signal_line.iloc[k] > macd_line.iloc[k-1] - signal_line.iloc[k-1]:
                                        histograma_bajando = False
                                        break
                                if histograma_bajando:
                                    cruce_previo = True
                                    break
                        
                        # Caso 2: BOS primero y cruce 1-2 velas DESPUÉS
                        cruce_posterior = False
                        if i+2 < len(df):
                            for j in range(1, 3):
                                if (macd_line.iloc[i+j] < signal_line.iloc[i+j] and 
                                    macd_line.iloc[i+j-1] >= signal_line.iloc[i+j-1]):
                                    # Verificar que el histograma ya viró negativo
                                    if macd_line.iloc[i] - signal_line.iloc[i] < macd_line.iloc[i-1] - signal_line.iloc[i-1]:
                                        cruce_posterior = True
                                        break
                        
                        # Verificar condiciones y generar señal
                        if (cruce_previo or cruce_posterior or 
                            (macd_line.iloc[i] < signal_line.iloc[i] and 
                             macd_line.iloc[i-1] >= signal_line.iloc[i-1])):
                            if rsi.iloc[i] < 50:
                                confidence_mod = 1.0
                                entry_type = 'coincidente'
                                
                                if cruce_previo:
                                    velas_desde_cruce = i - (i-2)
                                    if velas_desde_cruce > 3:
                                        confidence_mod = 0.8
                                        entry_type = 'cruce_previo_pullback'
                                    else:
                                        entry_type = 'cruce_previo'
                                elif cruce_posterior:
                                    confidence_mod = 0.9
                                    entry_type = 'cruce_posterior'
                                
                                signals.append({
                                    'type': 'SELL',
                                    'strategy': 'BOS + Impulse',
                                    'index': i,
                                    'price': current_candle['close'],
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_1(window_df, i, macd_line, signal_line, rsi) * confidence_mod,
                                    'entry_type': entry_type
                                })
        return signals

    def analyze_strategy_2_order_block_fibonacci_with_indicators(self, df, indicators, df_1h=None):
        """
        Versión optimizada de analyze_strategy_2_order_block_fibonacci que usa indicadores precalculados
        
        Args:
            df: DataFrame con datos en timeframe base (5 min)
            indicators: Diccionario con indicadores precalculados
            df_1h: DataFrame opcional con datos en timeframe de 1 hora para confirmación
        """
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        histogram = indicators['histogram']
        rsi = indicators['rsi']
        ob_data = indicators['ob_data']
        
        for i in range(10, len(df)):
            window_df = df.iloc[:i+1]
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            
            # Verificar Order Block alcista (BUY)
            if not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == 1:
                # 1. Validar consolidación en el Order Block
                ob_top = ob_data['Top'].iloc[i]
                ob_bottom = ob_data['Bottom'].iloc[i]
                ob_volume = ob_data['OBVolume'].iloc[i]
                
                # Verificar que el OB está en el cuerpo de la vela previa al impulso
                prev_candle = df.iloc[i-1]
                if not (min(prev_candle['open'], prev_candle['close']) <= ob_bottom and 
                       max(prev_candle['open'], prev_candle['close']) >= ob_top):
                    continue
                
                # 2. Analizar retroceso Fibonacci
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    retracement = (recent_high - current_price) / (recent_high - recent_low)
                    
                    # Verificar retroceso entre 61.8% y 78.6%
                    if self.fib_min <= retracement <= self.fib_max:
                        # 3. Analizar MACD
                        # Buscar reducción de debilidad en histograma
                        histograma_mejorando = False
                        for j in range(max(0, i-3), i+1):
                            if histogram.iloc[j] > histogram.iloc[j-1]:
                                histograma_mejorando = True
                                break
                        
                        if histograma_mejorando:
                            # 4. Analizar RSI
                            if rsi.iloc[i] > 30:
                                # Buscar divergencia alcista en RSI
                                divergencia_rsi = False
                                for j in range(max(0, i-5), i):
                                    if (df['low'].iloc[j] > df['low'].iloc[i] and 
                                        rsi.iloc[j] < rsi.iloc[i]):
                                        divergencia_rsi = True
                                        break
                                
                                if divergencia_rsi:
                                    # 5. Confirmar en timeframe superior si está disponible
                                    confirmacion_1h = True
                                    if df_1h is not None:
                                        # Encontrar el índice correspondiente en 1h
                                        timestamp = df.index[i]
                                        idx_1h = df_1h.index.get_loc(timestamp, method='ffill')
                                        
                                        # Verificar que no hay BOS roto en 1h
                                        ob_1h = smc.ob(df_1h.iloc[:idx_1h+1])
                                        if not np.isnan(ob_1h['OB'].iloc[-1]) and ob_1h['OB'].iloc[-1] == -1:
                                            confirmacion_1h = False
                                    
                                    if confirmacion_1h:
                                        confidence = self._calculate_confidence_2(
                                            window_df, i, macd_line, rsi, retracement,
                                            histograma_mejorando=histograma_mejorando,
                                            divergencia_rsi=divergencia_rsi,
                                            confirmacion_1h=confirmacion_1h
                                        )
                                        
                                        signals.append({
                                            'type': 'BUY',
                                            'strategy': 'Order Block + Fibonacci',
                                            'index': i,
                                            'price': current_price,
                                            'timestamp': df.index[i],
                                            'confidence': confidence,
                                            'ob_info': {
                                                'top': ob_top,
                                                'bottom': ob_bottom,
                                                'volume': ob_volume,
                                                'retracement': retracement,
                                                'divergencia_rsi': divergencia_rsi,
                                                'histograma_mejorando': histograma_mejorando,
                                                'confirmacion_1h': confirmacion_1h
                                            }
                                        })
            
            # Verificar Order Block bajista (SELL) - Lógica similar pero invertida
            elif not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == -1:
                # 1. Validar consolidación en el Order Block
                ob_top = ob_data['Top'].iloc[i]
                ob_bottom = ob_data['Bottom'].iloc[i]
                ob_volume = ob_data['OBVolume'].iloc[i]
                
                # Verificar que el OB está en el cuerpo de la vela previa al impulso
                prev_candle = df.iloc[i-1]
                if not (min(prev_candle['open'], prev_candle['close']) <= ob_bottom and 
                       max(prev_candle['open'], prev_candle['close']) >= ob_top):
                    continue
                
                # 2. Analizar retroceso Fibonacci
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    retracement = (current_price - recent_low) / (recent_high - recent_low)
                    
                    if self.fib_min <= retracement <= self.fib_max:
                        # 3. Analizar MACD
                        histograma_mejorando = False
                        for j in range(max(0, i-3), i+1):
                            if histogram.iloc[j] < histogram.iloc[j-1]:
                                histograma_mejorando = True
                                break
                        
                        if histograma_mejorando:
                            # 4. Analizar RSI
                            if rsi.iloc[i] < 70:
                                # Buscar divergencia bajista en RSI
                                divergencia_rsi = False
                                for j in range(max(0, i-5), i):
                                    if (df['high'].iloc[j] < df['high'].iloc[i] and 
                                        rsi.iloc[j] > rsi.iloc[i]):
                                        divergencia_rsi = True
                                        break
                                
                                if divergencia_rsi:
                                    # 5. Confirmar en timeframe superior si está disponible
                                    confirmacion_1h = True
                                    if df_1h is not None:
                                        timestamp = df.index[i]
                                        idx_1h = df_1h.index.get_loc(timestamp, method='ffill')
                                        
                                        ob_1h = smc.ob(df_1h.iloc[:idx_1h+1])
                                        if not np.isnan(ob_1h['OB'].iloc[-1]) and ob_1h['OB'].iloc[-1] == 1:
                                            confirmacion_1h = False
                                    
                                    if confirmacion_1h:
                                        confidence = self._calculate_confidence_2(
                                            window_df, i, macd_line, rsi, retracement,
                                            histograma_mejorando=histograma_mejorando,
                                            divergencia_rsi=divergencia_rsi,
                                            confirmacion_1h=confirmacion_1h
                                        )
                                        
                                        signals.append({
                                            'type': 'SELL',
                                            'strategy': 'Order Block + Fibonacci',
                                            'index': i,
                                            'price': current_price,
                                            'timestamp': df.index[i],
                                            'confidence': confidence,
                                            'ob_info': {
                                                'top': ob_top,
                                                'bottom': ob_bottom,
                                                'volume': ob_volume,
                                                'retracement': retracement,
                                                'divergencia_rsi': divergencia_rsi,
                                                'histograma_mejorando': histograma_mejorando,
                                                'confirmacion_1h': confirmacion_1h
                                            }
                                        })
        return signals

    def analyze_strategy_3_fair_value_gap_with_indicators(self, df, indicators):
        """Versión optimizada de analyze_strategy_3_fair_value_gap que usa indicadores precalculados"""
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        rsi = indicators['rsi']
        fvg_data = indicators['fvg_data']
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar FVG alcista (BUY)
            if not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == 1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    if (macd_line.iloc[i] > signal_line.iloc[i] and 
                        macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                        if 50 <= rsi.iloc[i] <= 60:
                            signals.append({
                                'type': 'BUY',
                                'strategy': 'Fair Value Gap',
                                'index': i,
                                'price': current_price,
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_3(window_df, i, macd_line, signal_line, rsi)
                            })
            
            # Verificar FVG bajista (SELL)
            elif not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == -1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    if (macd_line.iloc[i] < signal_line.iloc[i] and 
                        macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                        if 40 <= rsi.iloc[i] <= 50:
                            signals.append({
                                'type': 'SELL',
                                'strategy': 'Fair Value Gap',
                                'index': i,
                                'price': current_price,
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_3(window_df, i, macd_line, signal_line, rsi)
                            })
        return signals

    def analyze_all_strategies(self, df):
        """
        Analizar todas las estrategias en paralelo usando hilos y devolver señales combinadas.
        Utiliza indicadores precalculados para mejorar el rendimiento.
        """
        import concurrent.futures
        
        # Precalcular todos los indicadores
        indicators = self.precalculate_indicators(df)
        
        # Definimos las funciones que ejecutarán cada estrategia con los indicadores precalculados
        def run_strategy_1():
            return self.analyze_strategy_1_bos_impulse_with_indicators(df, indicators)
            
        def run_strategy_2():
            return self.analyze_strategy_2_order_block_fibonacci_with_indicators(df, indicators)
            
        def run_strategy_3():
            return self.analyze_strategy_3_fair_value_gap_with_indicators(df, indicators)
        
        # Ejecutamos las estrategias en paralelo usando ThreadPoolExecutor
        all_signals = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Creamos un diccionario de futuros para mantener un seguimiento de cada tarea
            future_to_strategy = {
                executor.submit(run_strategy_1): 'Strategy 1',
                executor.submit(run_strategy_2): 'Strategy 2',
                executor.submit(run_strategy_3): 'Strategy 3'
            }
            
            # Recolectamos los resultados a medida que se completan
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy_name = future_to_strategy[future]
                try:
                    signals = future.result()
                    all_signals.extend(signals)
                except Exception as e:
                    print(f'Error en {strategy_name}: {str(e)}')
        
        # Ordenar por índice
        all_signals.sort(key=lambda x: x['index'])
        
        return all_signals
    
    def _calculate_confidence_1(self, df, index, macd_line, signal_line, rsi):
        """Calcular nivel de confianza para Estrategia 1"""
        confidence = 0
        
        # MACD crossover fuerte
        if macd_line.iloc[index] > signal_line.iloc[index] * 1.1:
            confidence += 30
        
        # RSI en zona fuerte
        if 60 <= rsi.iloc[index] <= 80:
            confidence += 25
        
        # Volumen alto (si está disponible)
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.5:
                confidence += 20
        
        # Vela de impulso muy fuerte
        current_candle = df.iloc[index]
        body_size = abs(current_candle['close'] - current_candle['open'])
        total_range = current_candle['high'] - current_candle['low']
        if total_range > 0:
            body_percentage = body_size / total_range
            if body_percentage >= 0.8:
                confidence += 25
        
        return min(confidence, 100)
    
    def _calculate_confidence_2(self, df, index, macd_line, rsi, retracement,
                           histograma_mejorando=False, divergencia_rsi=False, confirmacion_1h=True):
        """
        Calcular nivel de confianza para Estrategia 2 (Order Block + Fibonacci)
        
        Args:
            df: DataFrame con datos
            index: Índice actual
            macd_line: Serie del MACD
            rsi: Serie del RSI
            retracement: Valor del retroceso Fibonacci
            histograma_mejorando: Si el histograma está reduciendo su debilidad
            divergencia_rsi: Si hay divergencia en el RSI
            confirmacion_1h: Si hay confirmación en timeframe de 1 hora
        """
        confidence = 0
        
        # 1. Retroceso Fibonacci óptimo (25%)
        if 0.65 <= retracement <= 0.75:  # Zona óptima
            confidence += 25
        elif self.fib_min <= retracement <= self.fib_max:  # Zona aceptable
            confidence += 15
        
        # 2. MACD y mejora del histograma (25%)
        if histograma_mejorando:
            confidence += 15
            # Bonus si la mejora es fuerte
            if macd_line.iloc[index] - macd_line.iloc[index-1] > 0:
                confidence += 10
        
        # 3. RSI y divergencia (25%)
        if 35 <= rsi.iloc[index] <= 65:  # Zona de recuperación
            confidence += 10
            if divergencia_rsi:  # Bonus por divergencia
                confidence += 15
        
        # 4. Volumen y confirmación timeframe superior (25%)
        # Volumen (15%)
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.5:
                confidence += 15
            elif df['volume'].iloc[index] > avg_volume * 1.2:
                confidence += 10
        
        # Confirmación timeframe superior (10%)
        if confirmacion_1h:
            confidence += 10
        
        return min(confidence, 100)
    
    def _calculate_confidence_3(self, df, index, macd_line, signal_line, rsi):
        """Calcular nivel de confianza para Estrategia 3"""
        confidence = 0
        
        # MACD crossover fuerte
        if macd_line.iloc[index] > signal_line.iloc[index] * 1.05:
            confidence += 30
        
        # RSI en zona óptima
        if 50 <= rsi.iloc[index] <= 60:
            confidence += 25
        
        # FVG bien definido
        confidence += 25
        
        # Volumen confirmación
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.3:
                confidence += 20
        
        return min(confidence, 100)
    
    def get_signal_summary(self, df):
        """
        Obtener resumen de todas las señales encontradas
        """
        all_signals = self.analyze_all_strategies(df)
        
        summary = {
            'total_signals': len(all_signals),
            'by_strategy': {},
            'by_confidence': {
                'high': 0,    # 80-100
                'medium': 0,  # 50-79
                'low': 0      # 0-49
            }
        }
        
        for signal in all_signals:
            strategy = signal['strategy']
            confidence = signal.get('confidence', 0)
            
            # Contar por estrategia
            if strategy not in summary['by_strategy']:
                summary['by_strategy'][strategy] = 0
            summary['by_strategy'][strategy] += 1
            
            # Contar por nivel de confianza
            if confidence >= 80:
                summary['by_confidence']['high'] += 1
            elif confidence >= 50:
                summary['by_confidence']['medium'] += 1
            else:
                summary['by_confidence']['low'] += 1
        
        return summary 