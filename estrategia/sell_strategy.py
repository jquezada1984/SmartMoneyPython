"""
Estrategia de Venta - Smart Money Concepts con Momentum
Esta librería implementa la estrategia de venta basada en SMC con confirmación de patrones de velas.
"""

import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc

class SellStrategy:
    """
    Estrategia de venta basada en Smart Money Concepts con Momentum
    
    Señal inicial: BOS bajista (BOS↓)
    Zona de entrada: Retesteo de soporte roto (resistencia) / OB / FVG
    Confirmación: Pin bar invertido o engulfing bajista
    """
    
    @staticmethod
    def detect_pin_bar_bearish(ohlc: pd.DataFrame, lookback: int = 3) -> pd.Series:
        """
        Detecta pin bars bajistas (shooting star)
        
        parámetros:
        ohlc: DataFrame - datos OHLC
        lookback: int - número de velas para comparar
        
        retorna:
        Series con 1 si es pin bar bajista, 0 en caso contrario
        """
        pin_bar = np.zeros(len(ohlc))
        
        for i in range(lookback, len(ohlc)):
            current = ohlc.iloc[i]
            prev_candles = ohlc.iloc[i-lookback:i]
            
            # Cuerpo pequeño (menos del 30% del rango total)
            body_size = abs(current['close'] - current['open'])
            total_range = current['high'] - current['low']
            body_ratio = body_size / total_range if total_range > 0 else 0
            
            # Sombra superior larga (más del 60% del rango total)
            upper_shadow = current['high'] - max(current['open'], current['close'])
            upper_shadow_ratio = upper_shadow / total_range if total_range > 0 else 0
            
            # Sombra inferior pequeña (menos del 10% del rango total)
            lower_shadow = min(current['open'], current['close']) - current['low']
            lower_shadow_ratio = lower_shadow / total_range if total_range > 0 else 0
            
            # Condiciones para pin bar bajista
            if (body_ratio < 0.3 and 
                upper_shadow_ratio > 0.6 and 
                lower_shadow_ratio < 0.1 and
                current['close'] < current['open']):  # Vela bajista
                pin_bar[i] = 1
                
        return pd.Series(pin_bar, name="PinBarBearish")
    
    @staticmethod
    def detect_engulfing_bearish(ohlc: pd.DataFrame) -> pd.Series:
        """
        Detecta patrones engulfing bajistas
        
        parámetros:
        ohlc: DataFrame - datos OHLC
        
        retorna:
        Series con 1 si es engulfing bajista, 0 en caso contrario
        """
        engulfing = np.zeros(len(ohlc))
        
        for i in range(1, len(ohlc)):
            current = ohlc.iloc[i]
            previous = ohlc.iloc[i-1]
            
            # Vela anterior alcista
            prev_bullish = previous['close'] > previous['open']
            
            # Vela actual bajista
            current_bearish = current['close'] < current['open']
            
            # El cuerpo de la vela actual engulle completamente el cuerpo de la anterior
            current_body_high = max(current['open'], current['close'])
            current_body_low = min(current['open'], current['close'])
            prev_body_high = max(previous['open'], previous['close'])
            prev_body_low = min(previous['open'], previous['close'])
            
            if (prev_bullish and current_bearish and
                current_body_high > prev_body_high and
                current_body_low < prev_body_low):
                engulfing[i] = 1
                
        return pd.Series(engulfing, name="EngulfingBearish")
    
    @staticmethod
    def detect_retest_resistance(ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, tolerance: float = 0.001) -> pd.Series:
        """
        Detecta retesteos de resistencias rotas (ahora convertidas en resistencia)
        
        parámetros:
        ohlc: DataFrame - datos OHLC
        swing_highs_lows: DataFrame - datos de swing highs/lows
        tolerance: float - tolerancia para considerar un retesteo
        
        retorna:
        Series con 1 si hay retesteo de resistencia, 0 en caso contrario
        """
        retest = np.zeros(len(ohlc))
        
        # Obtiene los swing lows (soportes rotos)
        swing_lows = swing_highs_lows[swing_highs_lows['HighLow'] == -1].copy()
        
        for i in range(1, len(ohlc)):
            current_low = ohlc.iloc[i]['low']
            current_high = ohlc.iloc[i]['high']
            
            # Busca swing lows anteriores que hayan sido rotos
            for _, swing in swing_lows.iterrows():
                swing_level = swing['Level']
                swing_index = swing.name
                
                # Verifica si el swing low fue roto después de su formación
                if swing_index < i:
                    # Busca si el precio rompió este nivel después del swing
                    for j in range(swing_index + 1, i):
                        if ohlc.iloc[j]['low'] < swing_level:
                            # Ahora verifica si el precio actual está retesteando este nivel
                            if (abs(current_high - swing_level) <= tolerance * swing_level or
                                (current_low <= swing_level and current_high >= swing_level)):
                                retest[i] = 1
                                break
                    if retest[i] == 1:
                        break
                        
        return pd.Series(retest, name="RetestResistance")
    
    @staticmethod
    def generate_sell_signals(ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, bos_choch=None, fvg=None, ob=None, patterns=None) -> pd.DataFrame:
        """
        Genera señales de venta basadas en la estrategia SMC con Momentum
        """
        # Calcula indicadores SMC solo si no se pasan como argumento
        if bos_choch is None:
            bos_choch = smc.bos_choch(ohlc, swing_highs_lows)
        if fvg is None:
            fvg = smc.fvg(ohlc, join_consecutive=True)
        if ob is None:
            ob = smc.ob(ohlc, swing_highs_lows)

        # Usar patrones del diccionario si se pasan, si no calcular como antes
        if patterns is not None:
            pin_bar = patterns.get('pin_bar_bearish', SellStrategy.detect_pin_bar_bearish(ohlc))
            engulfing_raw = patterns.get('engulfing', SellStrategy.detect_engulfing_bearish(ohlc))
            # engulfing_raw puede ser 1/-1/0, para venta solo -1
            engulfing = (engulfing_raw == -1).astype(int) if not isinstance(engulfing_raw, pd.Series) else engulfing_raw.apply(lambda x: 1 if x == -1 else 0)
        else:
            pin_bar = SellStrategy.detect_pin_bar_bearish(ohlc)
            engulfing = SellStrategy.detect_engulfing_bearish(ohlc)
        retest_resistance = SellStrategy.detect_retest_resistance(ohlc, swing_highs_lows)

        # Combina las señales
        signals = pd.DataFrame(index=ohlc.index)
        signals['BOS_Bearish'] = np.where(bos_choch['BOS'] == -1, 1, 0)
        signals['FVG_Bearish'] = np.where(fvg['FVG'] == -1, 1, 0)
        signals['OB_Bearish'] = np.where(ob['OB'] == -1, 1, 0)
        signals['PinBar'] = pin_bar
        signals['Engulfing'] = engulfing
        signals['RetestResistance'] = retest_resistance

        # Genera señal final de venta
        signals['SellSignal'] = 0
        for i in range(len(signals)):
            bos_signal = signals.iloc[i]['BOS_Bearish']
            entry_zone = (signals.iloc[i]['RetestResistance'] or 
                         signals.iloc[i]['OB_Bearish'] or 
                         signals.iloc[i]['FVG_Bearish'])
            confirmation = (signals.iloc[i]['PinBar'] or 
                          signals.iloc[i]['Engulfing'])
            if bos_signal and entry_zone and confirmation:
                signals.iloc[i, signals.columns.get_loc('SellSignal')] = 1
        return signals
    
    @staticmethod
    def get_signal_strength(ohlc: pd.DataFrame, signals: pd.DataFrame, index: int) -> float:
        """
        Calcula la fuerza de la señal de venta
        
        parámetros:
        ohlc: DataFrame - datos OHLC
        signals: DataFrame - señales generadas
        index: int - índice de la señal
        
        retorna:
        float - fuerza de la señal (0-100)
        """
        if signals.iloc[index]['SellSignal'] == 0:
            return 0.0
        
        strength = 0.0
        
        # BOS bajista (30 puntos)
        if signals.iloc[index]['BOS_Bearish']:
            strength += 30.0
        
        # Zona de entrada (25 puntos)
        if signals.iloc[index]['RetestResistance']:
            strength += 15.0
        if signals.iloc[index]['OB_Bearish']:
            strength += 10.0
        if signals.iloc[index]['FVG_Bearish']:
            strength += 10.0
        
        # Confirmación (25 puntos)
        if signals.iloc[index]['PinBar']:
            strength += 15.0
        if signals.iloc[index]['Engulfing']:
            strength += 10.0
        
        # Momentum adicional (20 puntos)
        if index > 0:
            price_change = (ohlc.iloc[index]['close'] - ohlc.iloc[index-1]['close']) / ohlc.iloc[index-1]['close']
            if price_change < 0:
                strength += min(20.0, abs(price_change) * 100.0)
        
        return min(100.0, strength) 