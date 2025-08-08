import pandas as pd
import numpy as np

class CandlestickPatterns:
    """
    Librería para detección de patrones de velas japonesas en un DataFrame OHLC.
    Todos los métodos devuelven una Serie booleana o categórica indicando la presencia del patrón.
    """

    @staticmethod
    def hammer(ohlc: pd.DataFrame, body_ratio: float = 0.3, shadow_ratio: float = 2.0) -> pd.Series:
        """
        Detecta el patrón de Martillo (Hammer).
        Un martillo tiene una mecha inferior larga, cuerpo pequeño y poca mecha superior.

        Parámetros:
        body_ratio: float - proporción máxima del cuerpo respecto al rango total de la vela
        shadow_ratio: float - proporción mínima de la mecha inferior respecto al cuerpo

        Retorna:
        Serie booleana: True si la vela es un martillo
        """
        o = ohlc['open']
        c = ohlc['close']
        h = ohlc['high']
        l = ohlc['low']
        body = abs(c - o)
        upper = h - np.maximum(c, o)
        lower = np.minimum(c, o) - l
        total = h - l
        is_hammer = (
            (body / total < body_ratio) &
            (lower / body > shadow_ratio) &
            (upper / total < 0.2)
        )
        return is_hammer

    @staticmethod
    def shooting_star(ohlc: pd.DataFrame, body_ratio: float = 0.3, shadow_ratio: float = 2.0) -> pd.Series:
        """
        Detecta el patrón de Estrella Fugaz (Shooting Star).
        Es lo opuesto al martillo: mecha superior larga, cuerpo pequeño y poca mecha inferior.
        """
        o = ohlc['open']
        c = ohlc['close']
        h = ohlc['high']
        l = ohlc['low']
        body = abs(c - o)
        upper = h - np.maximum(c, o)
        lower = np.minimum(c, o) - l
        total = h - l
        is_star = (
            (body / total < body_ratio) &
            (upper / body > shadow_ratio) &
            (lower / total < 0.2)
        )
        return is_star

    @staticmethod
    def doji(ohlc: pd.DataFrame, threshold: float = 0.05) -> pd.Series:
        """
        Detecta el patrón Doji (cuerpo muy pequeño).
        """
        o = ohlc['open']
        c = ohlc['close']
        h = ohlc['high']
        l = ohlc['low']
        total = h - l
        body = abs(c - o)
        is_doji = (body / total) < threshold
        return is_doji

    @staticmethod
    def engulfing(ohlc: pd.DataFrame) -> pd.Series:
        """
        Detecta el patrón Envolvente (Engulfing), alcista o bajista.
        Retorna:
        1 = Envolvente alcista, -1 = Envolvente bajista, 0 = no patrón
        """
        o = ohlc['open']
        c = ohlc['close']
        prev_o = o.shift(1)
        prev_c = c.shift(1)
        bullish = (prev_c < prev_o) & (c > o) & (c > prev_o) & (o < prev_c)
        bearish = (prev_c > prev_o) & (c < o) & (c < prev_o) & (o > prev_c)
        result = pd.Series(0, index=ohlc.index)
        result[bullish] = 1
        result[bearish] = -1
        return result

    @staticmethod
    def morning_star(ohlc: pd.DataFrame, body_threshold: float = 0.3) -> pd.Series:
        """
        Detecta el patrón Estrella de la Mañana (Morning Star).
        """
        o = ohlc['open']
        c = ohlc['close']
        h = ohlc['high']
        l = ohlc['low']
        total = h - l
        body = abs(c - o)
        prev_body = body.shift(1)
        next_body = body.shift(-1)
        # Criterios simplificados: vela bajista, doji/pequeña, vela alcista
        is_morning = (
            (c.shift(2) < o.shift(2)) &
            (prev_body / total.shift(1) < body_threshold) &
            (c > o)
        )
        return is_morning

    @staticmethod
    def evening_star(ohlc: pd.DataFrame, body_threshold: float = 0.3) -> pd.Series:
        """
        Detecta el patrón Estrella de la Tarde (Evening Star).
        """
        o = ohlc['open']
        c = ohlc['close']
        h = ohlc['high']
        l = ohlc['low']
        total = h - l
        body = abs(c - o)
        prev_body = body.shift(1)
        next_body = body.shift(-1)
        # Criterios simplificados: vela alcista, doji/pequeña, vela bajista
        is_evening = (
            (c.shift(2) > o.shift(2)) &
            (prev_body / total.shift(1) < body_threshold) &
            (c < o)
        )
        return is_evening

    # ===== CONFIRMACIÓN POR VOLUMEN =====
    
    @staticmethod
    def volume_confirmation(ohlc: pd.DataFrame, vol_window: int = 20, vol_mult: float = 1.2) -> pd.Series:
        """
        Confirma señales por volumen. Verifica si el volumen actual es mayor que la media
        de las últimas N velas multiplicada por un factor.
        
        Parámetros:
        ohlc: pd.DataFrame - DataFrame con columnas OHLCV
        vol_window: int - Ventana para calcular la media de volumen (default: 20)
        vol_mult: float - Multiplicador para la media de volumen (default: 1.2)
        
        Retorna:
        pd.Series - True si el volumen actual es mayor que la media * multiplicador
        """
        if 'volume' not in ohlc.columns:
            # Si no hay columna volume, crear una con valores NaN
            volume = pd.Series(np.nan, index=ohlc.index)
        else:
            volume = ohlc['volume']
        
        # Calcular media móvil del volumen
        vol_ma = volume.rolling(window=vol_window, min_periods=1).mean()
        
        # Umbral de confirmación
        threshold = vol_ma * vol_mult
        
        # Confirmación por volumen
        confirmation = volume > threshold
        
        return confirmation
    
    @staticmethod
    def high_volume_relative(ohlc: pd.DataFrame, vol_window: int = 20, vol_mult: float = 1.2) -> pd.Series:
        """
        Versión alternativa que calcula el volumen relativo (volumen actual / media).
        
        Parámetros:
        ohlc: pd.DataFrame - DataFrame con columnas OHLCV
        vol_window: int - Ventana para calcular la media de volumen
        vol_mult: float - Multiplicador mínimo para considerar alto volumen
        
        Retorna:
        pd.Series - Ratio volumen actual / media de volumen
        """
        if 'volume' not in ohlc.columns:
            return pd.Series(1.0, index=ohlc.index)  # Sin datos de volumen
        
        volume = ohlc['volume']
        vol_ma = volume.rolling(window=vol_window, min_periods=1).mean()
        
        # Evitar división por cero
        vol_ma = vol_ma.replace(0, np.nan)
        volume_ratio = volume / vol_ma
        
        return volume_ratio
    
    @staticmethod
    def volume_spike(ohlc: pd.DataFrame, vol_window: int = 20, spike_threshold: float = 2.0) -> pd.Series:
        """
        Detecta picos de volumen (spikes) que pueden indicar movimientos importantes.
        
        Parámetros:
        ohlc: pd.DataFrame - DataFrame con columnas OHLCV
        vol_window: int - Ventana para calcular la media de volumen
        spike_threshold: float - Umbral para considerar un pico (default: 2.0 = 200% de la media)
        
        Retorna:
        pd.Series - True si hay un pico de volumen
        """
        if 'volume' not in ohlc.columns:
            return pd.Series(False, index=ohlc.index)
        
        volume = ohlc['volume']
        vol_ma = volume.rolling(window=vol_window, min_periods=1).mean()
        
        # Detectar picos
        spike = volume > (vol_ma * spike_threshold)
        
        return spike
    
    @staticmethod
    def volume_trend_confirmation(ohlc: pd.DataFrame, vol_window: int = 20) -> pd.Series:
        """
        Confirma la tendencia del precio con el volumen.
        - Volumen alto en dirección de la tendencia = confirmación
        - Volumen bajo en dirección de la tendencia = divergencia
        
        Parámetros:
        ohlc: pd.DataFrame - DataFrame con columnas OHLCV
        vol_window: int - Ventana para calcular la media de volumen
        
        Retorna:
        pd.Series - 1 = confirmación alcista, -1 = confirmación bajista, 0 = neutral
        """
        if 'volume' not in ohlc.columns:
            return pd.Series(0, index=ohlc.index)
        
        volume = ohlc['volume']
        close = ohlc['close']
        
        # Calcular cambios de precio
        price_change = close.diff()
        
        # Calcular media de volumen
        vol_ma = volume.rolling(window=vol_window, min_periods=1).mean()
        
        # Determinar confirmación
        bullish_conf = (price_change > 0) & (volume > vol_ma)
        bearish_conf = (price_change < 0) & (volume > vol_ma)
        
        confirmation = pd.Series(0, index=ohlc.index)
        confirmation[bullish_conf] = 1
        confirmation[bearish_conf] = -1
        
        return confirmation 