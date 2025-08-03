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