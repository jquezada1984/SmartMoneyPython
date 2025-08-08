import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc

class MarketAnalysisLib:
    """
    Librería centralizada para análisis de mercado
    Esta es la librería núcleo que maneja toda la lógica común:
    - Análisis de tendencia (alcista/bajista/lateral)
    - Indicadores técnicos básicos
    - Patrones SMC principales
    - Validaciones de volumen
    - Sesiones de mercado
    
    Todas las demás librerías de estrategias utilizan esta como base.
    """
    
    def __init__(self, 
                 swing_length=5,
                 lookback=20,
                 macd_fast=12,
                 macd_slow=26,
                 macd_signal=9,
                 rsi_period=14,
                 atr_period=14,
                 volume_window=20,
                 volume_multiplier=1.2):
        
        # Parámetros de configuración
        self.swing_length = swing_length
        self.lookback = lookback
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.volume_window = volume_window
        self.volume_multiplier = volume_multiplier
        
        # Cache para indicadores calculados
        self._indicators_cache = {}
        self._trend_cache = {}
    
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
    
    def calculate_atr(self, df):
        """Calcular ATR (Average True Range)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()
        return atr
    
    def calculate_volume_confirmation(self, df):
        """
        Calcular confirmación por volumen
        vol_window = 20 → mira las últimas 20 velas y calcula la media
        vol_mult = 1.2 → exige que el volumen sea al menos 20% mayor que la media
        """
        if 'volume' not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        
        volume_ma = df['volume'].rolling(window=self.volume_window).mean()
        volume_threshold = volume_ma * self.volume_multiplier
        volume_confirmation = df['volume'] > volume_threshold
        
        return volume_confirmation
    
    def calculate_volume_ratio(self, df):
        """Calcular ratio de volumen actual vs media"""
        if 'volume' not in df.columns:
            return pd.Series([1.0] * len(df), index=df.index)
        
        volume_ma = df['volume'].rolling(window=self.volume_window).mean()
        volume_ratio = df['volume'] / volume_ma
        return volume_ratio
    
    def detect_trend(self, df, method='structural'):
        """
        DETECTAR TENDENCIA - MÉTODO PRINCIPAL
        
        Parámetros:
        - method: 'structural' (SMC), 'technical' (indicadores), 'combined'
        
        Retorna:
        - DataFrame con columnas: 'trend', 'strength', 'confidence'
        - trend: 1 (alcista), -1 (bajista), 0 (lateral)
        - strength: 0-100 (fuerza de la tendencia)
        - confidence: 0-100 (confianza en la detección)
        """
        
        if method == 'structural':
            return self._detect_trend_structural(df)
        elif method == 'technical':
            return self._detect_trend_technical(df)
        elif method == 'combined':
            return self._detect_trend_combined(df)
        else:
            raise ValueError("Método debe ser 'structural', 'technical' o 'combined'")
    
    def _detect_trend_structural(self, df):
        """
        Detectar tendencia usando análisis estructural SMC
        - Swing highs/lows
        - Break of Structure (BOS)
        - Patrones de estructura de mercado
        """
        # Calcular swing highs/lows
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
        bos_choch = smc.bos_choch(df, swing_highs_lows)
        trend_data = smc.trend_indicator(df, swing_highs_lows, lookback_period=self.lookback)
        
        # Inicializar resultados
        trend = pd.Series(0, index=df.index)
        strength = pd.Series(0, index=df.index)
        confidence = pd.Series(0, index=df.index)
        
        for i in range(self.swing_length, len(df)):
            # Análisis de BOS
            bos_value = bos_choch['BOS'].iloc[i]
            trend_value = trend_data['trend'].iloc[i] if 'trend' in trend_data.columns else 0
            
            # Determinar tendencia basada en BOS
            if not np.isnan(bos_value) and bos_value != 0:
                trend.iloc[i] = bos_value
                strength.iloc[i] = 70  # BOS fuerte
                confidence.iloc[i] = 80
            elif not np.isnan(trend_value) and trend_value != 0:
                trend.iloc[i] = trend_value
                strength.iloc[i] = 60  # Tendencia estructural
                confidence.iloc[i] = 70
            else:
                # Análisis de swing highs/lows
                recent_swings = swing_highs_lows.iloc[max(0, i-10):i+1]
                highs = recent_swings[recent_swings['HighLow'] == 1]
                lows = recent_swings[recent_swings['HighLow'] == -1]
                
                if len(highs) >= 2 and len(lows) >= 2:
                    # Verificar si highs y lows son crecientes/decrecientes
                    high_values = highs['Level'].values
                    low_values = lows['Level'].values
                    
                    if len(high_values) >= 2 and len(low_values) >= 2:
                        high_trend = np.polyfit(range(len(high_values)), high_values, 1)[0]
                        low_trend = np.polyfit(range(len(low_values)), low_values, 1)[0]
                        
                        if high_trend > 0 and low_trend > 0:
                            trend.iloc[i] = 1  # Alcista
                            strength.iloc[i] = 50
                            confidence.iloc[i] = 60
                        elif high_trend < 0 and low_trend < 0:
                            trend.iloc[i] = -1  # Bajista
                            strength.iloc[i] = 50
                            confidence.iloc[i] = 60
        
        return pd.DataFrame({
            'trend': trend,
            'strength': strength,
            'confidence': confidence
        })
    
    def _detect_trend_technical(self, df):
        """
        Detectar tendencia usando indicadores técnicos
        - MACD
        - RSI
        - Medias móviles
        """
        # Calcular indicadores
        macd_line, signal_line, histogram = self.calculate_macd(df)
        rsi = self.calculate_rsi(df)
        
        # Medias móviles
        ma_20 = df['close'].rolling(window=20).mean()
        ma_50 = df['close'].rolling(window=50).mean()
        
        # Inicializar resultados
        trend = pd.Series(0, index=df.index)
        strength = pd.Series(0, index=df.index)
        confidence = pd.Series(0, index=df.index)
        
        for i in range(50, len(df)):
            # Análisis de MACD
            macd_bullish = macd_line.iloc[i] > signal_line.iloc[i]
            macd_bearish = macd_line.iloc[i] < signal_line.iloc[i]
            
            # Análisis de RSI
            rsi_bullish = rsi.iloc[i] > 50
            rsi_bearish = rsi.iloc[i] < 50
            
            # Análisis de medias móviles
            ma_bullish = ma_20.iloc[i] > ma_50.iloc[i]
            ma_bearish = ma_20.iloc[i] < ma_50.iloc[i]
            
            # Contar señales alcistas vs bajistas
            bullish_signals = sum([macd_bullish, rsi_bullish, ma_bullish])
            bearish_signals = sum([macd_bearish, rsi_bearish, ma_bearish])
            
            # Determinar tendencia
            if bullish_signals >= 2:
                trend.iloc[i] = 1
                strength.iloc[i] = bullish_signals * 25
                confidence.iloc[i] = 60 + (bullish_signals * 10)
            elif bearish_signals >= 2:
                trend.iloc[i] = -1
                strength.iloc[i] = bearish_signals * 25
                confidence.iloc[i] = 60 + (bearish_signals * 10)
            else:
                trend.iloc[i] = 0  # Lateral
                strength.iloc[i] = 25
                confidence.iloc[i] = 40
        
        return pd.DataFrame({
            'trend': trend,
            'strength': strength,
            'confidence': confidence
        })
    
    def _detect_trend_combined(self, df):
        """
        Detectar tendencia combinando análisis estructural y técnico
        """
        structural_trend = self._detect_trend_structural(df)
        technical_trend = self._detect_trend_technical(df)
        
        # Combinar resultados
        combined_trend = pd.Series(0, index=df.index)
        combined_strength = pd.Series(0, index=df.index)
        combined_confidence = pd.Series(0, index=df.index)
        
        for i in range(len(df)):
            struct_trend = structural_trend['trend'].iloc[i]
            tech_trend = technical_trend['trend'].iloc[i]
            struct_conf = structural_trend['confidence'].iloc[i]
            tech_conf = technical_trend['confidence'].iloc[i]
            
            # Si ambos métodos coinciden
            if struct_trend == tech_trend and struct_trend != 0:
                combined_trend.iloc[i] = struct_trend
                combined_strength.iloc[i] = max(structural_trend['strength'].iloc[i], 
                                             technical_trend['strength'].iloc[i])
                combined_confidence.iloc[i] = min(100, (struct_conf + tech_conf) / 2 + 10)
            
            # Si solo uno detecta tendencia
            elif struct_trend != 0:
                combined_trend.iloc[i] = struct_trend
                combined_strength.iloc[i] = structural_trend['strength'].iloc[i]
                combined_confidence.iloc[i] = struct_conf
            elif tech_trend != 0:
                combined_trend.iloc[i] = tech_trend
                combined_strength.iloc[i] = technical_trend['strength'].iloc[i]
                combined_confidence.iloc[i] = tech_conf
            else:
                combined_trend.iloc[i] = 0
                combined_strength.iloc[i] = 25
                combined_confidence.iloc[i] = 40
        
        return pd.DataFrame({
            'trend': combined_trend,
            'strength': combined_strength,
            'confidence': combined_confidence
        })
    
    def is_trend_bullish(self, df, method='combined'):
        """
        Verificar si la tendencia es alcista
        Retorna: True/False
        """
        trend_data = self.detect_trend(df, method)
        return trend_data['trend'].iloc[-1] == 1
    
    def is_trend_bearish(self, df, method='combined'):
        """
        Verificar si la tendencia es bajista
        Retorna: True/False
        """
        trend_data = self.detect_trend(df, method)
        return trend_data['trend'].iloc[-1] == -1
    
    def is_trend_lateral(self, df, method='combined'):
        """
        Verificar si la tendencia es lateral
        Retorna: True/False
        """
        trend_data = self.detect_trend(df, method)
        return trend_data['trend'].iloc[-1] == 0
    
    def get_trend_strength(self, df, method='combined'):
        """
        Obtener la fuerza de la tendencia actual
        Retorna: 0-100
        """
        trend_data = self.detect_trend(df, method)
        return trend_data['strength'].iloc[-1]
    
    def get_trend_confidence(self, df, method='combined'):
        """
        Obtener la confianza en la detección de tendencia
        Retorna: 0-100
        """
        trend_data = self.detect_trend(df, method)
        return trend_data['confidence'].iloc[-1]
    
    def precalculate_all_indicators(self, df):
        """
        Precalcular todos los indicadores comunes
        Retorna: diccionario con todos los indicadores
        """
        # Indicadores básicos
        macd_line, signal_line, histogram = self.calculate_macd(df)
        rsi = self.calculate_rsi(df)
        atr = self.calculate_atr(df)
        
        # Confirmación de volumen
        volume_confirmation = self.calculate_volume_confirmation(df)
        volume_ratio = self.calculate_volume_ratio(df)
        
        # Análisis de tendencia
        trend_data = self.detect_trend(df, method='combined')
        
        # Patrones SMC principales
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
        bos_choch = smc.bos_choch(df, swing_highs_lows)
        ob_data = smc.ob(df, swing_highs_lows)
        fvg_data = smc.fvg(df, join_consecutive=True)
        
        # Indicadores adicionales
        liquidity_data = smc.liquidity(df, swing_highs_lows)
        previous_high_low_data = smc.previous_high_low(df, time_frame="4h")
        sessions_data = smc.sessions(df, session="London")
        retracements_data = smc.retracements(df, swing_highs_lows)
        
        return {
            # Indicadores básicos
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram,
            'rsi': rsi,
            'atr': atr,
            
            # Volumen
            'volume_confirmation': volume_confirmation,
            'volume_ratio': volume_ratio,
            
            # Tendencia
            'trend_data': trend_data,
            
            # Patrones SMC principales
            'swing_highs_lows': swing_highs_lows,
            'bos_choch': bos_choch,
            'ob_data': ob_data,
            'fvg_data': fvg_data,
            
            # Indicadores adicionales
            'liquidity_data': liquidity_data,
            'previous_high_low_data': previous_high_low_data,
            'sessions_data': sessions_data,
            'retracements_data': retracements_data
        }
    
    def get_market_summary(self, df):
        """
        Obtener resumen completo del estado del mercado
        """
        indicators = self.precalculate_all_indicators(df)
        
        current_trend = indicators['trend_data']['trend'].iloc[-1]
        trend_strength = indicators['trend_data']['strength'].iloc[-1]
        trend_confidence = indicators['trend_data']['confidence'].iloc[-1]
        
        current_rsi = indicators['rsi'].iloc[-1]
        current_macd = indicators['macd_line'].iloc[-1]
        current_signal = indicators['signal_line'].iloc[-1]
        
        volume_confirmed = indicators['volume_confirmation'].iloc[-1]
        volume_ratio_current = indicators['volume_ratio'].iloc[-1]
        
        # Determinar estado del mercado
        if current_trend == 1:
            trend_status = "ALCISTA"
        elif current_trend == -1:
            trend_status = "BAJISTA"
        else:
            trend_status = "LATERAL"
        
        # Estado de momentum
        if current_macd > current_signal:
            momentum_status = "ALCISTA"
        elif current_macd < current_signal:
            momentum_status = "BAJISTA"
        else:
            momentum_status = "NEUTRO"
        
        # Estado de RSI
        if current_rsi > 70:
            rsi_status = "SOBRECOMPRADO"
        elif current_rsi < 30:
            rsi_status = "SOBREVENDIDO"
        else:
            rsi_status = "NEUTRO"
        
        return {
            'trend': {
                'status': trend_status,
                'strength': trend_strength,
                'confidence': trend_confidence
            },
            'momentum': {
                'status': momentum_status,
                'macd': current_macd,
                'signal': current_signal
            },
            'rsi': {
                'status': rsi_status,
                'value': current_rsi
            },
            'volume': {
                'confirmed': volume_confirmed,
                'ratio': volume_ratio_current
            },
            'timestamp': df.index[-1],
            'price': df['close'].iloc[-1]
        }
    
    def validate_signal(self, signal_type, df, indicators=None):
        """
        Validar una señal de trading contra el estado del mercado
        """
        if indicators is None:
            indicators = self.precalculate_all_indicators(df)
        
        market_summary = self.get_market_summary(df)
        trend_status = market_summary['trend']['status']
        momentum_status = market_summary['momentum']['status']
        rsi_status = market_summary['rsi']['status']
        volume_confirmed = market_summary['volume']['confirmed']
        
        # Validar señal de compra
        if signal_type == 'BUY':
            # Debe haber tendencia alcista o momentum alcista
            trend_valid = trend_status in ['ALCISTA', 'LATERAL']
            momentum_valid = momentum_status in ['ALCISTA', 'NEUTRO']
            rsi_valid = rsi_status not in ['SOBRECOMPRADO']
            
            return {
                'valid': trend_valid and momentum_valid and rsi_valid,
                'trend_valid': trend_valid,
                'momentum_valid': momentum_valid,
                'rsi_valid': rsi_valid,
                'volume_confirmed': volume_confirmed
            }
        
        # Validar señal de venta
        elif signal_type == 'SELL':
            # Debe haber tendencia bajista o momentum bajista
            trend_valid = trend_status in ['BAJISTA', 'LATERAL']
            momentum_valid = momentum_status in ['BAJISTA', 'NEUTRO']
            rsi_valid = rsi_status not in ['SOBREVENDIDO']
            
            return {
                'valid': trend_valid and momentum_valid and rsi_valid,
                'trend_valid': trend_valid,
                'momentum_valid': momentum_valid,
                'rsi_valid': rsi_valid,
                'volume_confirmed': volume_confirmed
            }
        
        return {'valid': False}
