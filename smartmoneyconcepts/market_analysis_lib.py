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
        IMPLEMENTACIÓN CORRECTA del algoritmo SMC que describes:
        
        1. Identificación de altos y bajos significativos
           - Swing highs (máximos) y swing lows (mínimos)
           - Puntos donde el mercado reaccionó con fuerza
        
        2. Definición de la tendencia
           - Tendencia alcista: HH (Higher Highs) + HL (Higher Lows)
           - Tendencia bajista: LL (Lower Lows) + LH (Lower Highs)
           - Rango/consolidación: atrapado entre máximo y mínimo claros
        
        3. Confirmación con BOS (Break of Structure)
           - BOS alcista confirma continuidad alcista
           - BOS bajista confirma continuidad bajista
        
        4. Cambio de tendencia (CHoCH)
           - Cuando rompe en dirección contraria a la tendencia previa
        
        RETORNA SOLO: -1 (BAJISTA), 0 (LATERAL), 1 (ALCISTA)
        """
        if len(df) < self.swing_length * 2:
            # Datos insuficientes
            return pd.DataFrame({
                'trend': pd.Series(0.0, index=df.index, dtype=float)
            })
        
        # Calcular swing highs/lows
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
        bos_choch = smc.bos_choch(df, swing_highs_lows)
        
        # Inicializar solo la tendencia
        trend = pd.Series(0.0, index=df.index, dtype=float)
        
        # Analizar cada punto desde swing_length en adelante
        for i in range(self.swing_length, len(df)):
            current_trend = 0
            
            # 1. ANÁLISIS DE BOS (Break of Structure) - Prioridad máxima
            bos_value = bos_choch['BOS'].iloc[i]
            choch_value = bos_choch['CHOCH'].iloc[i]
            
            if not np.isnan(bos_value) and bos_value != 0:
                # BOS detectado - confirmación de tendencia
                current_trend = bos_value  # Ya es -1, 0, o 1
                
            elif not np.isnan(choch_value) and choch_value != 0:
                # CHoCH detectado - cambio de tendencia
                current_trend = choch_value  # Ya es -1, 0, o 1
                
            else:
                # 2. ANÁLISIS DE ESTRUCTURA SEGÚN TU ALGORITMO SMC
                # Usar lookback de 20 velas para identificar estructura clara
                lookback_start = max(0, i - 20)
                recent_data = df.iloc[lookback_start:i+1]
                
                # 2.1. DETECCIÓN PRINCIPAL DE TENDENCIA SMC
                smc_trend = self._detect_smc_trend_correctly(recent_data)
                if smc_trend['detected']:
                    current_trend = smc_trend['trend']  # Ya es -1, 0, o 1
                else:
                    # 2.2. ANÁLISIS DE RANGO/CONSOLIDACIÓN
                    range_analysis = self._analyze_range_consolidation_smc(recent_data)
                    if range_analysis['is_range']:
                        current_trend = 0  # Lateral/Rango
            
            # GARANTIZAR que current_trend sea -1, 0, o 1 (valores claros)
            if current_trend > 0.5:
                current_trend = 1  # ALCISTA
            elif current_trend < -0.5:
                current_trend = -1  # BAJISTA
            else:
                current_trend = 0  # LATERAL
            
            # Asignar solo la tendencia
            trend.iloc[i] = current_trend
        
        return pd.DataFrame({
            'trend': trend
        })
    
    def _analyze_higher_highs_lows_improved(self, highs, lows, price_data):
        """
        Analizar si hay Higher Highs (HH) y Higher Lows (HL) para tendencia alcista
        MEJORADO: Análisis más dinámico y sensible a cambios
        """
        if len(highs) < 1 or len(lows) < 1:
            return {'confirmed': False, 'strength': 0}
        
        # Análisis más dinámico: priorizar swing points más recientes
        high_values = highs['Level'].values
        low_values = lows['Level'].values
        
        # Verificar Higher Highs (HH) - comparar últimos 2 highs
        hh_confirmed = False
        if len(high_values) >= 2:
            hh_confirmed = high_values[-1] > high_values[-2]
        elif len(high_values) == 1:
            # Si solo hay 1 high, verificar que esté por encima del precio medio reciente
            recent_avg = price_data['high'].tail(10).mean()
            hh_confirmed = high_values[-1] > recent_avg
        
        # Verificar Higher Lows (HL) - comparar últimos 2 lows
        hl_confirmed = False
        if len(low_values) >= 2:
            hl_confirmed = low_values[-1] > low_values[-2]
        elif len(low_values) == 1:
            # Si solo hay 1 low, verificar que esté por encima del precio medio reciente
            recent_avg = price_data['low'].tail(10).mean()
            hl_confirmed = low_values[-1] > recent_avg
        
        # Calcular fuerza basada en la pendiente y confirmación
        if hh_confirmed and hl_confirmed:
            # Calcular pendiente considerando todos los puntos disponibles
            if len(high_values) >= 2:
                high_slope = (high_values[-1] - high_values[0]) / max(1, len(high_values) - 1)
            else:
                high_slope = 0.001  # Pendiente mínima si solo hay 1 punto
            
            if len(low_values) >= 2:
                low_slope = (low_values[-1] - low_values[0]) / max(1, len(low_values) - 1)
            else:
                low_slope = 0.001  # Pendiente mínima si solo hay 1 punto
            
            # Escalar la pendiente y considerar la confirmación
            strength = min(80, (high_slope + low_slope) * 2000 + 20)  # +20 por confirmación
            return {'confirmed': True, 'strength': strength}
        
        return {'confirmed': False, 'strength': 0}
    
    def _analyze_lower_lows_highs_improved(self, highs, lows, price_data):
        """
        Analizar si hay Lower Lows (LL) y Lower Highs (LH) para tendencia bajista
        MEJORADO: Análisis más dinámico y sensible a cambios
        """
        if len(highs) < 1 or len(lows) < 1:
            return {'confirmed': False, 'strength': 0}
        
        # Análisis más dinámico: priorizar swing points más recientes
        high_values = highs['Level'].values
        low_values = lows['Level'].values
        
        # Verificar Lower Lows (LL) - comparar últimos 2 lows
        ll_confirmed = False
        if len(low_values) >= 2:
            ll_confirmed = low_values[-1] < low_values[-2]
        elif len(low_values) == 1:
            # Si solo hay 1 low, verificar que esté por debajo del precio medio reciente
            recent_avg = price_data['low'].tail(10).mean()
            ll_confirmed = low_values[-1] < recent_avg
        
        # Verificar Lower Highs (LH) - comparar últimos 2 highs
        lh_confirmed = False
        if len(high_values) >= 2:
            lh_confirmed = high_values[-1] < high_values[-2]
        elif len(high_values) == 1:
            # Si solo hay 1 high, verificar que esté por debajo del precio medio reciente
            recent_avg = price_data['high'].tail(10).mean()
            lh_confirmed = high_values[-1] < recent_avg
        
        # Calcular fuerza basada en la pendiente y confirmación
        if ll_confirmed and lh_confirmed:
            # Calcular pendiente considerando todos los puntos disponibles
            if len(high_values) >= 2:
                high_slope = (high_values[-1] - high_values[0]) / max(1, len(high_values) - 1)
            else:
                high_slope = -0.001  # Pendiente mínima negativa si solo hay 1 punto
            
            if len(low_values) >= 2:
                low_slope = (low_values[-1] - low_values[0]) / max(1, len(low_values) - 1)
            else:
                low_slope = -0.001  # Pendiente mínima negativa si solo hay 1 punto
            
            # Escalar la pendiente y considerar la confirmación
            strength = min(80, abs(high_slope + low_slope) * 2000 + 20)  # +20 por confirmación
            return {'confirmed': True, 'strength': strength}
        
        return {'confirmed': False, 'strength': 0}
    
    def _analyze_range_consolidation_smc(self, df):
        """
        Analizar si el mercado está en rango/consolidación según SMC
        """
        if len(df) < 10:
            return {'is_range': False}
        
        # Calcular swing highs y lows recientes
        highs = df['high'].rolling(window=5, center=True).max()
        lows = df['low'].rolling(window=5, center=True).min()
        
        valid_highs = highs.dropna()
        valid_lows = lows.dropna()
        
        if len(valid_highs) < 3 or len(valid_lows) < 3:
            return {'is_range': False}
        
        # Verificar si está en rango: no hay tendencia clara
        # Los highs y lows no muestran patrón de HH+HL ni LL+LH
        
        # Calcular volatilidad del rango
        price_range = df['high'].max() - df['low'].min()
        avg_price = df['close'].mean()
        volatility = price_range / avg_price
        
        # Si la volatilidad es baja (<3%) y no hay tendencia clara, está en rango
        if volatility < 0.03:
            return {'is_range': True}
        
        return {'is_range': False}
    
    def _detect_smc_trend_correctly(self, df):
        """
        IMPLEMENTACIÓN REAL del algoritmo SMC que describes:
        
        1. IDENTIFICACIÓN DE ALTOS Y BAJOS SIGNIFICATIVOS
           - Swing highs (máximos) y swing lows (mínimos) REALES
           - Puntos donde el mercado reaccionó con fuerza
        
        2. DEFINICIÓN DE LA TENDENCIA
           - Tendencia alcista: HH (Higher Highs) + HL (Higher Lows)
           - Tendencia bajista: LL (Lower Lows) + LH (Lower Highs)
           - Rango/consolidación: atrapado entre máximo y mínimo claros
        
        3. CONFIRMACIÓN CON BOS Y CHoCH
           - Break of Structure (BOS) confirma tendencia
           - Change of Character (CHoCH) indica cambio de tendencia
        
        RETORNA SOLO: -1 (BAJISTA), 0 (LATERAL), 1 (ALCISTA)
        """
        if len(df) < 20:  # Necesitamos al menos 20 velas para identificar estructura SMC
            return {'detected': False, 'trend': 0}
        
        try:
            # 1. IDENTIFICAR SWING HIGHS Y LOWS REALES usando la librería SMC
            swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
            bos_choch = smc.bos_choch(df, swing_highs_lows)
            
            # 2. ANALIZAR BOS Y CHoCH - PRIORIDAD MÁXIMA
            # Buscar el último BOS o CHoCH en los datos
            last_bos_idx = None
            last_choch_idx = None
            
            for i in range(len(bos_choch)):
                if not pd.isna(bos_choch['BOS'].iloc[i]) and bos_choch['BOS'].iloc[i] != 0:
                    last_bos_idx = i
                if not pd.isna(bos_choch['CHOCH'].iloc[i]) and bos_choch['CHOCH'].iloc[i] != 0:
                    last_choch_idx = i
            
            # 3. DETERMINAR TENDENCIA POR BOS/CHoCH
            if last_bos_idx is not None:
                bos_value = bos_choch['BOS'].iloc[last_bos_idx]
                if bos_value == 1:
                    return {'detected': True, 'trend': 1}  # ALCISTA
                elif bos_value == -1:
                    return {'detected': True, 'trend': -1}  # BAJISTA
            
            if last_choch_idx is not None:
                choch_value = bos_choch['CHOCH'].iloc[last_choch_idx]
                if choch_value == 1:
                    return {'detected': True, 'trend': 1}  # ALCISTA
                elif choch_value == -1:
                    return {'detected': True, 'trend': -1}  # BAJISTA
            
            # 4. ANÁLISIS DE ESTRUCTURA SMC REAL (HH+HL, LL+LH)
            # Obtener solo los swing points válidos (no NaN)
            valid_swing_highs = swing_highs_lows[swing_highs_lows['HighLow'] == 1].dropna()
            valid_swing_lows = swing_highs_lows[swing_highs_lows['HighLow'] == -1].dropna()
            
            if len(valid_swing_highs) >= 2 and len(valid_swing_lows) >= 2:
                # Obtener los últimos 2 swing highs y lows
                last_2_highs = valid_swing_highs.tail(2)
                last_2_lows = valid_swing_lows.tail(2)
                
                # Verificar Higher Highs (HH)
                hh_confirmed = False
                if len(last_2_highs) >= 2:
                    hh_confirmed = last_2_highs['Level'].iloc[-1] > last_2_highs['Level'].iloc[-2]
                
                # Verificar Higher Lows (HL)
                hl_confirmed = False
                if len(last_2_lows) >= 2:
                    hl_confirmed = last_2_lows['Level'].iloc[-1] > last_2_lows['Level'].iloc[-2]
                
                # Verificar Lower Lows (LL)
                ll_confirmed = False
                if len(last_2_lows) >= 2:
                    ll_confirmed = last_2_lows['Level'].iloc[-1] < last_2_lows['Level'].iloc[-2]
                
                # Verificar Lower Highs (LH)
                lh_confirmed = False
                if len(last_2_highs) >= 2:
                    lh_confirmed = last_2_highs['Level'].iloc[-1] < last_2_highs['Level'].iloc[-2]
                
                # 5. DETERMINAR TENDENCIA DOMINANTE
                if hh_confirmed and hl_confirmed:
                    # TENDENCIA ALCISTA confirmada: HH + HL
                    return {'detected': True, 'trend': 1}
                
                elif ll_confirmed and lh_confirmed:
                    # TENDENCIA BAJISTA confirmada: LL + LH
                    return {'detected': True, 'trend': -1}
                
                elif hh_confirmed or hl_confirmed:
                    # TENDENCIA ALCISTA parcial
                    return {'detected': True, 'trend': 1}
                
                elif ll_confirmed or lh_confirmed:
                    # TENDENCIA BAJISTA parcial
                    return {'detected': True, 'trend': -1}
            
            # 6. ANÁLISIS DE PRECIO DIRECTO como respaldo
            # Si no hay estructura SMC clara, analizar el movimiento de precios reciente
            recent_prices = df.tail(10)  # Últimas 10 velas
            
            if len(recent_prices) >= 8:
                # Calcular si hay tendencia en precio directo
                recent_highs = recent_prices['high'].tail(8)
                recent_lows = recent_prices['low'].tail(8)
                
                # Tendencia alcista: precios más altos
                if (recent_highs.iloc[-1] > recent_highs.iloc[-2] > recent_highs.iloc[-3] and
                    recent_lows.iloc[-1] > recent_lows.iloc[-2] > recent_lows.iloc[-3]):
                    return {'detected': True, 'trend': 1}
                
                # Tendencia bajista: precios más bajos
                elif (recent_highs.iloc[-1] < recent_highs.iloc[-2] < recent_highs.iloc[-3] and
                      recent_lows.iloc[-1] < recent_lows.iloc[-2] < recent_lows.iloc[-3]):
                    return {'detected': True, 'trend': -1}
            
            # 7. ANÁLISIS DE RANGO/CONSOLIDACIÓN
            # Solo si no hay tendencia clara
            if self._is_in_range_smc(df):
                return {'detected': True, 'trend': 0}  # LATERAL
            
            # 8. NO SE PUDO DETERMINAR TENDENCIA
            return {'detected': False, 'trend': 0}
            
        except Exception as e:
            print(f"Error en análisis SMC: {e}")
            return {'detected': False, 'trend': 0}
    
    def _is_in_range_smc(self, df):
        """
        Verificar si el mercado está en rango/consolidación según SMC
        """
        if len(df) < 15:
            return False
        
        try:
            # Usar swing highs/lows reales para determinar rango
            swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.swing_length)
            
            # Obtener solo los swing points válidos
            valid_highs = swing_highs_lows[swing_highs_lows['HighLow'] == 1]['Level'].dropna()
            valid_lows = swing_highs_lows[swing_highs_lows['HighLow'] == -1]['Level'].dropna()
            
            if len(valid_highs) < 2 or len(valid_lows) < 2:
                return False
            
            # Calcular el rango de precios usando swing points reales
            price_range = valid_highs.max() - valid_lows.min()
            avg_price = (valid_highs.mean() + valid_lows.mean()) / 2
            
            # Si el rango es menor al 2% del precio promedio, está en rango
            volatility = price_range / avg_price
            return volatility < 0.02
            
        except Exception as e:
            print(f"Error analizando rango SMC: {e}")
            return False
    
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
        
        # Inicializar resultados - usar float64 para permitir valores decimales
        trend = pd.Series(0.0, index=df.index, dtype=float)
        strength = pd.Series(0.0, index=df.index, dtype=float)
        confidence = pd.Series(0.0, index=df.index, dtype=float)
        
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
        
        # Combinar resultados - usar float64 para permitir valores decimales
        combined_trend = pd.Series(0.0, index=df.index, dtype=float)
        combined_strength = pd.Series(0.0, index=df.index, dtype=float)
        combined_confidence = pd.Series(0.0, index=df.index, dtype=float)
        
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
