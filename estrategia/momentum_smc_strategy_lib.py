import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib

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
        
        # Inicializar MarketAnalysisLib como base
        self.market_analysis = MarketAnalysisLib(
            swing_length=swing_length,
            lookback=lookback,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            rsi_period=rsi_period
        )
        
        # Parámetros específicos de la estrategia
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
        """Calcular MACD usando MarketAnalysisLib"""
        return self.market_analysis.calculate_macd(df)
    
    def calculate_rsi(self, df):
        """Calcular RSI usando MarketAnalysisLib"""
        return self.market_analysis.calculate_rsi(df)
    
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
    
    
    
    def analyze_strategy_2_order_block_fibonacci(self, df):
        """
        ESTRATEGIA 2: ORDER BLOCK + FIBONACCI
        Detecta señales tanto alcistas (BUY) como bajistas (SELL)
        """
        signals = []
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
                    
                    # Retroceso entre 61.8% y 78.6% (sin MACD/RSI)
                    if self.fib_min <= retracement <= self.fib_max:
                        confidence = self._calculate_confidence_2(window_df, i, retracement)
                        signals.append({
                            'type': 'BUY',
                            'strategy': 'Order Block + Fibonacci',
                            'index': i,
                            'price': current_price,
                            'timestamp': df.index[i],
                            'confidence': confidence
                        })
            
            # Verificar Order Block bajista (SELL)
            elif not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == -1:
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    # Para ventas, calculamos el retroceso desde el mínimo
                    retracement = (current_price - recent_low) / (recent_high - recent_low)
                    
                    # Retroceso entre 61.8% y 78.6% (sin MACD/RSI)
                    if self.fib_min <= retracement <= self.fib_max:
                        confidence = self._calculate_confidence_2(window_df, i, retracement)
                        signals.append({
                            'type': 'SELL',
                            'strategy': 'Order Block + Fibonacci',
                            'index': i,
                            'price': current_price,
                            'timestamp': df.index[i],
                            'confidence': confidence
                        })
        
        return signals
    
    def analyze_strategy_3_fair_value_gap(self, df):
        """
        ESTRATEGIA 3: FAIR VALUE GAP (FVG)
        Detecta señales tanto alcistas (BUY) como bajistas (SELL)
        """
        signals = []
        fvg_data = smc.fvg(df, join_consecutive=True)
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar FVG alcista (BUY)
            if not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == 1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    confidence = self._calculate_confidence_3(window_df, i, fvg_top, fvg_bottom)
                    signals.append({
                        'type': 'BUY',
                        'strategy': 'Fair Value Gap',
                        'index': i,
                        'price': current_price,
                        'timestamp': df.index[i],
                        'confidence': confidence
                    })
            
            # Verificar FVG bajista (SELL)
            elif not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == -1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    confidence = self._calculate_confidence_3(window_df, i, fvg_top, fvg_bottom)
                    signals.append({
                        'type': 'SELL',
                        'strategy': 'Fair Value Gap',
                        'index': i,
                        'price': current_price,
                        'timestamp': df.index[i],
                        'confidence': confidence
                    })
        
        return signals
    
    def precalculate_indicators(self, df):
        """
        Precalcula todos los indicadores usando MarketAnalysisLib
        """
        return self.market_analysis.precalculate_all_indicators(df)

    def analyze_strategy_1_bos_impulse_with_indicators(self, df, indicators, df_h4=None, df_h1=None, df_m15=None):
        """
        Versión optimizada de analyze_strategy_1_bos_impulse que usa indicadores precalculados
        
        Args:
            df: DataFrame con datos en timeframe base (5M)
            indicators: Diccionario con indicadores precalculados (solo necesita 'bos_choch')
            df_h4: DataFrame opcional con datos en H4 para confirmación de tendencia
            df_h1: DataFrame opcional con datos en H1 para confirmación de tendencia  
            df_m15: DataFrame opcional con datos en M15 para confirmación de tendencia
        """
        signals = []
        # Preparar timeframes superiores si no se proporcionan
        df_h4_use = df_h4 if df_h4 is not None and len(df_h4) > 0 else None
        df_h1_use = df_h1 if df_h1 is not None and len(df_h1) > 0 else None
        df_m15_use = df_m15 if df_m15 is not None and len(df_m15) > 0 else None

        # Intentar resamplear desde 5M si faltan
        if df_h4_use is None:
            try:
                df_h4_use = self._resample_ohlcv(df, '4h')
            except Exception:
                df_h4_use = None
        if df_h1_use is None:
            try:
                df_h1_use = self._resample_ohlcv(df, '1h')
            except Exception:
                df_h1_use = None
        if df_m15_use is None:
            try:
                df_m15_use = self._resample_ohlcv(df, '15min')
            except Exception:
                df_m15_use = None

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
                        # VALIDAR TENDENCIA EN TIMEFRAMES SUPERIORES
                        trend_validation = self._validate_trend_timeframes(
                            df, i, 'BUY', df_h4_use, df_h1_use, df_m15_use
                        )
                        
                        # Solo generar señal si la validación de tendencia es exitosa
                        if trend_validation['overall_valid']:
                            # Bonus de confianza por validación de tendencia
                            trend_bonus = 0
                            if trend_validation['h4_trend'] == 'bullish':
                                trend_bonus += 5
                            if trend_validation['h1_trend'] == 'bullish':
                                trend_bonus += 5
                            if trend_validation['m15_trend'] == 'bullish':
                                trend_bonus += 5
                                
                                signals.append({
                                    'type': 'BUY',
                                    'strategy': 'BOS + Impulse',
                                    'index': i,
                                    'price': current_candle['close'],
                                    'timestamp': df.index[i],
                                    'confidence': min(100, 70 + trend_bonus),  # Confianza base sin MACD/RSI
                                    'entry_type': 'bos_impulse',
                                    'trend_validation': trend_validation
                                })
                    
                    # Señal de VENTA
                    elif not np.isnan(bos_choch['BOS'].iloc[-1]) and bos_choch['BOS'].iloc[-1] == -1:
                        # VALIDAR TENDENCIA EN TIMEFRAMES SUPERIORES
                        trend_validation = self._validate_trend_timeframes(
                            df, i, 'SELL', df_h4_use, df_h1_use, df_m15_use
                        )
                        
                        # Solo generar señal si la validación de tendencia es exitosa
                        if trend_validation['overall_valid']:
                            # Bonus de confianza por validación de tendencia
                            trend_bonus = 0
                            if trend_validation['h4_trend'] == 'bearish':
                                trend_bonus += 5
                            if trend_validation['h1_trend'] == 'bearish':
                                trend_bonus += 5
                            if trend_validation['m15_trend'] == 'bearish':
                                trend_bonus += 5
                                
                                signals.append({
                                    'type': 'SELL',
                                    'strategy': 'BOS + Impulse',
                                    'index': i,
                                    'price': current_candle['close'],
                                    'timestamp': df.index[i],
                                    'confidence': min(100, 70 + trend_bonus),  # Confianza base sin MACD/RSI
                                    'entry_type': 'bos_impulse',
                                    'trend_validation': trend_validation
                                })
        return signals

    def _resample_ohlcv(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """
        Resamplear un DataFrame OHLCV a un timeframe superior (p.ej., '15min', '1h', '4h').
        """
        if df is None or len(df) == 0:
            return df
        ohlc = df.copy()
        ohlc.index = pd.to_datetime(ohlc.index)
        resampled = (
            ohlc.resample(rule)
                .agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
                .dropna()
        )
        return resampled
    
    def _validate_trend_timeframes(self, df, index, signal_type, df_h4=None, df_h1=None, df_m15=None):
        """
        Validar que la tendencia en los timeframes superiores sea cfzonsistente con la señal
        
        Args:
            df: DataFrame base (5M)
            index: Índice actual
            signal_type: 'BUY' o 'SELL'
            df_h4, df_h1, df_m15: DataFrames de timeframes superiores
            
        Returns:
            dict: {
                'valid': bool,
                'h4_trend': str,  # 'bullish', 'bearish', 'lateral', 'unknown'
                'h1_trend': str,
                'm15_trend': str,
                'overall_valid': bool
            }
        """
        result = {
            'valid': True,
            'h4_trend': 'unknown',
            'h1_trend': 'unknown', 
            'm15_trend': 'unknown',
            'overall_valid': True
        }
        
        # Obtener timestamp actual
        current_timestamp = df.index[index]
        
        # Validar H4
        if df_h4 is not None:
            try:
                # Encontrar el índice correspondiente en H4
                idx_h4 = df_h4.index.get_loc(current_timestamp, method='ffill')
                
                # Calcular tendencia en H4 usando MarketAnalysisLib
                h4_trend_data = self.market_analysis.detect_trend(df_h4.iloc[:idx_h4+1], method='combined')
                h4_trend = h4_trend_data['trend'].iloc[-1]
                
                if h4_trend == 1:
                    result['h4_trend'] = 'bullish'
                elif h4_trend == -1:
                    result['h4_trend'] = 'bearish'
                else:
                    result['h4_trend'] = 'lateral'
                
                # Validar consistencia
                if signal_type == 'BUY' and h4_trend == -1:
                    result['valid'] = False
                elif signal_type == 'SELL' and h4_trend == 1:
                    result['valid'] = False
                    
            except Exception as e:
                print(f"Error validando H4: {e}")
        
        # Validar H1
        if df_h1 is not None:
            try:
                idx_h1 = df_h1.index.get_loc(current_timestamp, method='ffill')
                h1_trend_data = self.market_analysis.detect_trend(df_h1.iloc[:idx_h1+1], method='combined')
                h1_trend = h1_trend_data['trend'].iloc[-1]
                
                if h1_trend == 1:
                    result['h1_trend'] = 'bullish'
                elif h1_trend == -1:
                    result['h1_trend'] = 'bearish'
                else:
                    result['h1_trend'] = 'lateral'
                
                # Validar consistencia
                if signal_type == 'BUY' and h1_trend == -1:
                    result['valid'] = False
                elif signal_type == 'SELL' and h1_trend == 1:
                    result['valid'] = False
                    
            except Exception as e:
                print(f"Error validando H1: {e}")
        
        # Validar M15
        if df_m15 is not None:
            try:
                idx_m15 = df_m15.index.get_loc(current_timestamp, method='ffill')
                m15_trend_data = self.market_analysis.detect_trend(df_m15.iloc[:idx_m15+1], method='combined')
                m15_trend = m15_trend_data['trend'].iloc[-1]
                
                if m15_trend == 1:
                    result['m15_trend'] = 'bullish'
                elif m15_trend == -1:
                    result['m15_trend'] = 'bearish'
                else:
                    result['m15_trend'] = 'lateral'
                
                # Validar consistencia
                if signal_type == 'BUY' and m15_trend == -1:
                    result['valid'] = False
                elif signal_type == 'SELL' and m15_trend == 1:
                    result['valid'] = False
                    
            except Exception as e:
                print(f"Error validando M15: {e}")
        
        # Determinar validación general
        # Para BUY: al menos 2 timeframes deben ser alcistas o laterales
        # Para SELL: al menos 2 timeframes deben ser bajistas o laterales
        bullish_count = sum([
            1 if result['h4_trend'] in ['bullish', 'lateral'] else 0,
            1 if result['h1_trend'] in ['bullish', 'lateral'] else 0,
            1 if result['m15_trend'] in ['bullish', 'lateral'] else 0
        ])
        
        bearish_count = sum([
            1 if result['h4_trend'] in ['bearish', 'lateral'] else 0,
            1 if result['h1_trend'] in ['bearish', 'lateral'] else 0,
            1 if result['m15_trend'] in ['bearish', 'lateral'] else 0
        ])
        
        if signal_type == 'BUY':
            result['overall_valid'] = bullish_count >= 2 and result['valid']
        else:  # SELL
            result['overall_valid'] = bearish_count >= 2 and result['valid']
        
        return result

    def analyze_strategy_2_order_block_fibonacci_with_indicators(self, df, indicators, df_1h=None):
        """
        Versión optimizada de analyze_strategy_2_order_block_fibonacci que usa indicadores precalculados
        
        Args:
            df: DataFrame con datos en timeframe base (5 min)
            indicators: Diccionario con indicadores precalculados
            df_1h: DataFrame opcional con datos en timeframe de 1 hora para confirmación
        """
        signals = []
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
                        # Confirmar en timeframe superior si está disponible (sin MACD/RSI)
                        confirmacion_1h = True
                        if df_1h is not None:
                            # Encontrar el índice correspondiente en 1h
                            timestamp = df.index[i]
                            idx_1h = df_1h.index.get_loc(timestamp, method='ffill')
                            # Verificar que no hay OB contrario reciente en 1h
                            ob_1h = smc.ob(
                                df_1h.iloc[:idx_1h+1],
                                smc.swing_highs_lows(df_1h.iloc[:idx_1h+1], swing_length=self.swing_length)
                            )
                            if not np.isnan(ob_1h['OB'].iloc[-1]) and ob_1h['OB'].iloc[-1] == -1:
                                confirmacion_1h = False
                        
                        if confirmacion_1h:
                            confidence = self._calculate_confidence_2(
                                window_df, i, retracement, confirmacion_1h=confirmacion_1h
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
                        confirmacion_1h = True
                        if df_1h is not None:
                            timestamp = df.index[i]
                            idx_1h = df_1h.index.get_loc(timestamp, method='ffill')
                            ob_1h = smc.ob(
                                df_1h.iloc[:idx_1h+1],
                                smc.swing_highs_lows(df_1h.iloc[:idx_1h+1], swing_length=self.swing_length)
                            )
                            if not np.isnan(ob_1h['OB'].iloc[-1]) and ob_1h['OB'].iloc[-1] == 1:
                                confirmacion_1h = False
                        if confirmacion_1h:
                            confidence = self._calculate_confidence_2(
                                window_df, i, retracement, confirmacion_1h=confirmacion_1h
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
                                    'confirmacion_1h': confirmacion_1h
                                }
                            })
        return signals

    def analyze_strategy_3_fair_value_gap_with_indicators(self, df, indicators):
        """Versión optimizada de analyze_strategy_3_fair_value_gap que usa indicadores precalculados"""
        signals = []
        fvg_data = indicators['fvg_data']
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar FVG alcista (BUY)
            if not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == 1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    confidence = self._calculate_confidence_3(window_df, i, fvg_top, fvg_bottom)
                    signals.append({
                        'type': 'BUY',
                        'strategy': 'Fair Value Gap',
                        'index': i,
                        'price': current_price,
                        'timestamp': df.index[i],
                        'confidence': confidence
                    })
            
            # Verificar FVG bajista (SELL)
            elif not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == -1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    confidence = self._calculate_confidence_3(window_df, i, fvg_top, fvg_bottom)
                    signals.append({
                        'type': 'SELL',
                        'strategy': 'Fair Value Gap',
                        'index': i,
                        'price': current_price,
                        'timestamp': df.index[i],
                        'confidence': confidence
                    })
        return signals

    def analyze_all_strategies(self, df, df_h4=None, df_h1=None, df_m15=None):
        """
        Analizar todas las estrategias en paralelo usando hilos y devolver señales combinadas.
        Utiliza indicadores precalculados para mejorar el rendimiento.
        
        Args:
            df: DataFrame con datos en timeframe base (5M)
            df_h4: DataFrame opcional con datos en H4 para confirmación de tendencia
            df_h1: DataFrame opcional con datos en H1 para confirmación de tendencia
            df_m15: DataFrame opcional con datos en M15 para confirmación de tendencia
        """
        import concurrent.futures
        
        # Preparar timeframes superiores si no se proporcionan
        df_h4_use = df_h4 if df_h4 is not None and len(df_h4) > 0 else None
        df_h1_use = df_h1 if df_h1 is not None and len(df_h1) > 0 else None
        df_m15_use = df_m15 if df_m15 is not None and len(df_m15) > 0 else None

        if df_h4_use is None:
            try:
                df_h4_use = self._resample_ohlcv(df, '4h')
            except Exception:
                df_h4_use = None
        if df_h1_use is None:
            try:
                df_h1_use = self._resample_ohlcv(df, '1h')
            except Exception:
                df_h1_use = None
        if df_m15_use is None:
            try:
                df_m15_use = self._resample_ohlcv(df, '15min')
            except Exception:
                df_m15_use = None
        
        # Precalcular todos los indicadores
        indicators = self.precalculate_indicators(df)
        
        # Definimos las funciones que ejecutarán cada estrategia con los indicadores precalculados
        def run_strategy_1():
            return self.analyze_strategy_1_bos_impulse_with_indicators(df, indicators, df_h4_use, df_h1_use, df_m15_use)
            
        def run_strategy_2():
            # Estrategia 2 usa 1H como validación opcional
            return self.analyze_strategy_2_order_block_fibonacci_with_indicators(df, indicators, df_h1_use)
            
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
    

    
    def _calculate_confidence_2(self, df, index, retracement,
                           confirmacion_1h=True):
        """
        Calcular nivel de confianza para Estrategia 2 (Order Block + Fibonacci)
        
        Args:
            df: DataFrame con datos
            index: Índice actual
            retracement: Valor del retroceso Fibonacci
            confirmacion_1h: Si hay confirmación en timeframe de 1 hora
        """
        confidence = 0
        
        # 1. Retroceso Fibonacci óptimo (25%)
        if 0.65 <= retracement <= 0.75:  # Zona óptima
            confidence += 25
        elif self.fib_min <= retracement <= self.fib_max:  # Zona aceptable
            confidence += 15
        
        # 2. Volumen y confirmación timeframe superior (máx 40%)
        # Volumen (hasta 30%)
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.5:
                confidence += 20
            elif df['volume'].iloc[index] > avg_volume * 1.2:
                confidence += 10
        
        # Confirmación timeframe superior (hasta 20%)
        if confirmacion_1h:
            confidence += 20
        
        return min(confidence, 100)
    
    def _calculate_confidence_3(self, df, index, fvg_top, fvg_bottom):
        """Calcular nivel de confianza para Estrategia 3"""
        confidence = 0
        
        # 1. Profundidad en el FVG (hasta 40%)
        price = df['close'].iloc[index]
        mid = (fvg_top + fvg_bottom) / 2
        if fvg_bottom < price < fvg_top:
            confidence += 20
            if price <= mid:
                confidence += 20  # Mejor si entra al 50%
        
        # 2. Volumen (hasta 30%)
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.5:
                confidence += 20
            elif df['volume'].iloc[index] > avg_volume * 1.2:
                confidence += 10
        
        # 3. Vela de salida rápida (hasta 30%)
        if index > 0:
            prev_close = df['close'].iloc[index-1]
            if prev_close <= fvg_top and df['close'].iloc[index] > fvg_top:
                confidence += 30
        
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