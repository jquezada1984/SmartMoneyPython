"""
Estrategia SMC con Validación de Tendencia y Gestión de Riesgo
Esta librería implementa una estrategia avanzada que valida la tendencia antes de generar señales
y calcula SL/TP según la estructura del mercado y gestión de riesgo.
"""

import pandas as pd
import numpy as np
from .smc import smc
from .buy_strategy import BuyStrategy
from .sell_strategy import SellStrategy
import threading
import time
from .candlestick_patterns import CandlestickPatterns

class TrendValidatedStrategy:
    """
    Estrategia SMC con validación de tendencia y gestión de riesgo avanzada
    
    Reglas:
    - Solo operar a favor de la tendencia
    - SL calculado según estructura del mercado
    - Ratio R:R mínimo 1:1.5
    - Buffer de 2-5 pips para evitar saltos menores
    """
    
    @staticmethod
    def validate_trend(ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, lookback: int = 20) -> pd.Series:
        """
        Valida la tendencia usando múltiples confirmaciones
        
        parámetros:
        ohlc: DataFrame - datos OHLC
        swing_highs_lows: DataFrame - datos de swing highs/lows
        lookback: int - período para analizar la tendencia
        
        retorna:
        Series con 1 si tendencia alcista, -1 si bajista, 0 si lateral
        """
        n = len(ohlc)
        trend = np.full(n, np.nan, dtype=np.float32)
        
        # Calcula indicadores de tendencia
        trend_indicator = smc.trend_indicator(ohlc, swing_highs_lows, lookback)
        
        for i in range(lookback, n):
            # Usa el indicador de tendencia SMC
            if not np.isnan(trend_indicator.iloc[i]['Trend']):
                trend[i] = trend_indicator.iloc[i]['Trend']
            else:
                # Fallback: análisis de swing highs/lows
                recent_swings = swing_highs_lows.iloc[max(0, i-lookback):i+1]
                recent_highs = recent_swings[recent_swings['HighLow'] == 1]['Level'].dropna()
                recent_lows = recent_swings[recent_swings['HighLow'] == -1]['Level'].dropna()
                
                if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                    # Tendencias de swing highs y lows
                    high_trend = 1 if recent_highs.iloc[-1] > recent_highs.iloc[-2] else -1
                    low_trend = 1 if recent_lows.iloc[-1] > recent_lows.iloc[-2] else -1
                    
                    if high_trend == 1 and low_trend == 1:
                        trend[i] = 1  # Alcista
                    elif high_trend == -1 and low_trend == -1:
                        trend[i] = -1  # Bajista
                    else:
                        trend[i] = 0  # Lateral
        
        return pd.Series(trend, name="Trend")
    
    @staticmethod
    def calculate_sl_for_retest_support(ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, 
                                       entry_index: int, buffer_pips: float = 0.0003) -> float:
        """
        Calcula SL para entrada en retesteo de soporte (resistencia rota)
        
        SL: unos pocos pips por debajo del mínimo del retesteo
        """
        current_candle = ohlc.iloc[entry_index]
        retest_low = current_candle['low']
        
        # Busca el swing low más cercano por debajo del retesteo
        swing_lows = swing_highs_lows[swing_highs_lows['HighLow'] == -1]
        swing_lows_below = swing_lows[swing_lows['Level'] < retest_low]
        
        if len(swing_lows_below) > 0:
            # Usa el swing low más cercano
            closest_swing_low = swing_lows_below['Level'].iloc[-1]
            sl = closest_swing_low - buffer_pips
        else:
            # Usa el mínimo del retesteo con buffer
            sl = retest_low - buffer_pips
        
        return sl
    
    @staticmethod
    def calculate_sl_for_order_block(ob_data: pd.DataFrame, entry_index: int, 
                                   buffer_pips: float = 0.0003) -> float:
        """
        Calcula SL para entrada en Order Block
        
        SL: justo por debajo de la base del Order Block
        """
        ob_bottom = ob_data.iloc[entry_index]['Bottom']
        sl = ob_bottom - buffer_pips
        return sl
    
    @staticmethod
    def calculate_sl_for_fvg(fvg_data: pd.DataFrame, entry_index: int, 
                           buffer_pips: float = 0.0003) -> float:
        """
        Calcula SL para entrada en Fair Value Gap
        
        SL: un poco por debajo del extremo inferior del gap
        """
        fvg_bottom = fvg_data.iloc[entry_index]['Bottom']
        sl = fvg_bottom - buffer_pips
        return sl
    
    @staticmethod
    def calculate_sl_for_retest_resistance(ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, 
                                         entry_index: int, buffer_pips: float = 0.0003) -> float:
        """
        Calcula SL para entrada en retesteo de resistencia (soporte roto)
        
        SL: unos pocos pips por encima del máximo del retesteo
        """
        current_candle = ohlc.iloc[entry_index]
        retest_high = current_candle['high']
        
        # Busca el swing high más cercano por encima del retesteo
        swing_highs = swing_highs_lows[swing_highs_lows['HighLow'] == 1]
        swing_highs_above = swing_highs[swing_highs['Level'] > retest_high]
        
        if len(swing_highs_above) > 0:
            # Usa el swing high más cercano
            closest_swing_high = swing_highs_above['Level'].iloc[0]
            sl = closest_swing_high + buffer_pips
        else:
            # Usa el máximo del retesteo con buffer
            sl = retest_high + buffer_pips
        
        return sl
    
    @staticmethod
    def calculate_sl_for_order_block_bearish(ob_data: pd.DataFrame, entry_index: int, 
                                           buffer_pips: float = 0.0003) -> float:
        """
        Calcula SL para entrada en Order Block bajista
        
        SL: justo por encima de la cúspide del OB
        """
        ob_top = ob_data.iloc[entry_index]['Top']
        sl = ob_top + buffer_pips
        return sl
    
    @staticmethod
    def calculate_sl_for_fvg_bearish(fvg_data: pd.DataFrame, entry_index: int, 
                                   buffer_pips: float = 0.0003) -> float:
        """
        Calcula SL para entrada en Fair Value Gap bajista
        
        SL: un poco por encima del extremo superior del gap
        """
        fvg_top = fvg_data.iloc[entry_index]['Top']
        sl = fvg_top + buffer_pips
        return sl
    
    @staticmethod
    def calculate_tp(entry_price: float, sl_price: float, trade_type: str, 
                    rr_ratio: float = 1.5) -> float:
        """
        Calcula Take Profit basado en el ratio R:R
        
        parámetros:
        entry_price: float - precio de entrada
        sl_price: float - precio del stop loss
        trade_type: str - 'buy' o 'sell'
        rr_ratio: float - ratio riesgo:retorno mínimo
        
        retorna:
        float - precio del take profit
        """
        risk = abs(entry_price - sl_price)
        reward = risk * rr_ratio
        
        if trade_type == 'buy':
            tp = entry_price + reward
        else:  # sell
            tp = entry_price - reward
        
        return tp
    
    @staticmethod
    def generate_trend_validated_signals(ohlc: pd.DataFrame, swing_highs_lows: pd.DataFrame, 
                                       buffer_pips: float = 0.0003, rr_ratio: float = 1.5) -> pd.DataFrame:
        """
        Genera señales validadas por tendencia con SL/TP calculados
        """
        # Valida tendencia
        trend = TrendValidatedStrategy.validate_trend(ohlc, swing_highs_lows)

        # Calcula indicadores SMC en paralelo
        results = {}
        def run_bos_choch():
            results['bos_choch'] = smc.bos_choch(ohlc, swing_highs_lows)
        def run_fvg():
            results['fvg'] = smc.fvg(ohlc, join_consecutive=True)
        def run_ob():
            results['ob'] = smc.ob(ohlc, swing_highs_lows)
        threads = [
            threading.Thread(target=run_bos_choch),
            threading.Thread(target=run_fvg),
            threading.Thread(target=run_ob)
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        bos_choch = results['bos_choch']
        fvg = results['fvg']
        ob = results['ob']

        # Calcular patrones de velas en paralelo y centralizado
        patterns = {}
        def run_pin_bar_bullish():
            patterns['pin_bar_bullish'] = CandlestickPatterns.hammer(ohlc)
        def run_pin_bar_bearish():
            patterns['pin_bar_bearish'] = CandlestickPatterns.shooting_star(ohlc)
        def run_engulfing():
            patterns['engulfing'] = CandlestickPatterns.engulfing(ohlc)
        pattern_threads = [
            threading.Thread(target=run_pin_bar_bullish),
            threading.Thread(target=run_pin_bar_bearish),
            threading.Thread(target=run_engulfing)
        ]
        for th in pattern_threads:
            th.start()
        for th in pattern_threads:
            th.join()

        # Genera señales básicas usando los indicadores y patrones ya calculados
        buy_signals = BuyStrategy.generate_buy_signals(ohlc, swing_highs_lows, bos_choch=bos_choch, fvg=fvg, ob=ob, patterns=patterns)
        sell_signals = SellStrategy.generate_sell_signals(ohlc, swing_highs_lows, bos_choch=bos_choch, fvg=fvg, ob=ob, patterns=patterns)
        
        # Crea DataFrame de resultados
        results = pd.DataFrame(index=ohlc.index)
        results['Trend'] = trend
        results['Signal'] = 0  # 1=buy, -1=sell, 0=no signal
        results['EntryPrice'] = np.nan
        results['StopLoss'] = np.nan
        results['TakeProfit'] = np.nan
        results['EntryType'] = ''  # 'retest', 'ob', 'fvg'
        results['SignalStrength'] = np.nan
        results['RR_Ratio'] = np.nan
        
        for i in range(len(ohlc)):
            print(f"[Progreso señales tendencia] Procesando vela {i+1}/{len(ohlc)}...", end='\r', flush=True)
            current_trend = trend.iloc[i]
            # Solo genera señales si hay tendencia definida
            if np.isnan(current_trend) or current_trend == 0:
                continue
            # Señales de compra en tendencia alcista
            if current_trend == 1 and buy_signals.iloc[i]['BuySignal'] == 1:
                print(f"Entrando a BUY en vela {i}")
                entry_price = ohlc.iloc[i]['close']
                sl_price = np.nan
                entry_type = ''
                # Determina tipo de entrada y calcula SL
                if buy_signals.iloc[i]['RetestSupport']:
                    print(f"BUY tipo retest_support en vela {i}")
                    sl_price = TrendValidatedStrategy.calculate_sl_for_retest_support(
                        ohlc, swing_highs_lows, i, buffer_pips)
                    entry_type = 'retest_support'
                elif buy_signals.iloc[i]['OB_Bullish']:
                    print(f"BUY tipo order_block en vela {i}")
                    sl_price = TrendValidatedStrategy.calculate_sl_for_order_block(
                        ob, i, buffer_pips)
                    entry_type = 'order_block'
                elif buy_signals.iloc[i]['FVG_Bullish']:
                    print(f"BUY tipo fvg en vela {i}")
                    sl_price = TrendValidatedStrategy.calculate_sl_for_fvg(
                        fvg, i, buffer_pips)
                    entry_type = 'fvg'
                print(f"SL calculado: {sl_price}")
                if not np.isnan(sl_price):
                    tp_price = TrendValidatedStrategy.calculate_tp(
                        entry_price, sl_price, 'buy', rr_ratio)
                    # Calcula ratio R:R real
                    risk = abs(entry_price - sl_price)
                    reward = abs(tp_price - entry_price)
                    actual_rr = reward / risk if risk > 0 else 0
                    print(f"TP calculado: {tp_price}, R:R: {actual_rr}")
                    # Solo acepta si cumple el ratio mínimo
                    if actual_rr >= rr_ratio:
                        print(f"BUY válido en vela {i}, registrando señal...")
                        results.iloc[i, results.columns.get_loc('Signal')] = 1
                        results.iloc[i, results.columns.get_loc('EntryPrice')] = entry_price
                        results.iloc[i, results.columns.get_loc('StopLoss')] = sl_price
                        results.iloc[i, results.columns.get_loc('TakeProfit')] = tp_price
                        results.iloc[i, results.columns.get_loc('EntryType')] = entry_type
                        results.iloc[i, results.columns.get_loc('SignalStrength')] = BuyStrategy.get_signal_strength(ohlc, buy_signals, i)
                        results.iloc[i, results.columns.get_loc('RR_Ratio')] = actual_rr
            
            # Señales de venta en tendencia bajista
            elif current_trend == -1 and sell_signals.iloc[i]['SellSignal'] == 1:
                entry_price = ohlc.iloc[i]['close']
                sl_price = np.nan
                entry_type = ''
                
                # Determina tipo de entrada y calcula SL
                if sell_signals.iloc[i]['RetestResistance']:
                    sl_price = TrendValidatedStrategy.calculate_sl_for_retest_resistance(
                        ohlc, swing_highs_lows, i, buffer_pips)
                    entry_type = 'retest_resistance'
                elif sell_signals.iloc[i]['OB_Bearish']:
                    sl_price = TrendValidatedStrategy.calculate_sl_for_order_block_bearish(
                        ob, i, buffer_pips)
                    entry_type = 'order_block'
                elif sell_signals.iloc[i]['FVG_Bearish']:
                    sl_price = TrendValidatedStrategy.calculate_sl_for_fvg_bearish(
                        fvg, i, buffer_pips)
                    entry_type = 'fvg'
                
                if not np.isnan(sl_price):
                    tp_price = TrendValidatedStrategy.calculate_tp(
                        entry_price, sl_price, 'sell', rr_ratio)
                    
                    # Calcula ratio R:R real
                    risk = abs(entry_price - sl_price)
                    reward = abs(entry_price - tp_price)
                    actual_rr = reward / risk if risk > 0 else 0
                    
                    # Solo acepta si cumple el ratio mínimo
                    if actual_rr >= rr_ratio:
                        results.iloc[i, results.columns.get_loc('Signal')] = -1
                        results.iloc[i, results.columns.get_loc('EntryPrice')] = entry_price
                        results.iloc[i, results.columns.get_loc('StopLoss')] = sl_price
                        results.iloc[i, results.columns.get_loc('TakeProfit')] = tp_price
                        results.iloc[i, results.columns.get_loc('EntryType')] = entry_type
                        results.iloc[i, results.columns.get_loc('SignalStrength')] = SellStrategy.get_signal_strength(ohlc, sell_signals, i)
                        results.iloc[i, results.columns.get_loc('RR_Ratio')] = actual_rr
        
        return results
    
    @staticmethod
    def log_trade(ohlc: pd.DataFrame, signals: pd.DataFrame, index: int, 
                  log_file: str = "trade_logs/trades.csv"):
        """
        Registra una operación en el archivo de log
        
        parámetros:
        ohlc: DataFrame - datos OHLC
        signals: DataFrame - señales generadas
        index: int - índice de la señal
        log_file: str - archivo de log
        """
        import os
        from datetime import datetime
        
        # Crea el directorio si no existe
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Prepara los datos de la operación
        signal = signals.iloc[index]
        candle = ohlc.iloc[index]
        
        trade_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'index': index,
            'date': candle.name if hasattr(candle, 'name') else index,
            'signal_type': 'BUY' if signal['Signal'] == 1 else 'SELL',
            'entry_price': signal['EntryPrice'],
            'stop_loss': signal['StopLoss'],
            'take_profit': signal['TakeProfit'],
            'entry_type': signal['EntryType'],
            'signal_strength': signal['SignalStrength'],
            'rr_ratio': signal['RR_Ratio'],
            'trend': 'BULLISH' if signal['Trend'] == 1 else 'BEARISH',
            'candle_open': candle['open'],
            'candle_high': candle['high'],
            'candle_low': candle['low'],
            'candle_close': candle['close'],
            'volume': candle['volume']
        }
        
        # Convierte a DataFrame
        trade_df = pd.DataFrame([trade_data])
        
        # Guarda en CSV
        if os.path.exists(log_file):
            trade_df.to_csv(log_file, mode='a', header=False, index=False)
        else:
            trade_df.to_csv(log_file, index=False)
        
        print(f"Operación registrada: {trade_data['signal_type']} en índice {index}")
        print(f"Entrada: {trade_data['entry_price']:.5f}, SL: {trade_data['stop_loss']:.5f}, TP: {trade_data['take_profit']:.5f}")
        print(f"Tipo: {trade_data['entry_type']}, R:R: {trade_data['rr_ratio']:.2f}")
        print("-" * 50) 