import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib

class ZonasMitigacionStrategyLib:
    """
    Librería independiente de ZonasMitigacionStrategy para análisis de señales de trading
    
    Esta clase proporciona las mismas funcionalidades que ZonasMitigacionStrategy
    pero sin depender de Backtrader, permitiendo su uso como librería pura.
    
    ESTRATEGIA: Zonas de Mitigación Multi-Timeframe
    
    PREPARACIÓN HTF (1H):
    - Determina tendencia: máximos y mínimos crecientes/decrecientes
    - Marca zonas institucionales: Order Blocks, FVGs, Liquidity Zones
    - Confirma ruptura en 15M (MSS/BOS)
    
    SEÑALES LTF (5M):
    - Break of Structure (BOS)
    - Pullback a Order Block (61.8%-78.6% Fibonacci)
    - Entrada en Fair Value Gap
    - Reversión en Liquidity Grab
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
        """Calcular ATR usando MarketAnalysisLib"""
        return self.market_analysis.calculate_atr(df)
    
    def precalculate_indicators(self, df):
        """
        Precalcula todos los indicadores usando MarketAnalysisLib
        """
        return self.market_analysis.precalculate_all_indicators(df)
    
    def analyze_strategy_1_bos_mitigation(self, df, indicators):
        """
        ESTRATEGIA 1: BOS + MITIGACIÓN
        Detecta señales de Break of Structure con confirmación de mitigación
        """
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        rsi = indicators['rsi']
        bos_choch = indicators['bos_choch']
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_candle = df.iloc[i]
            
            # Verificar BOS alcista
            if not np.isnan(bos_choch['BOS'].iloc[i]) and bos_choch['BOS'].iloc[i] == 1:
                # Confirmar con MACD crossover alcista
                if (macd_line.iloc[i] > signal_line.iloc[i] and 
                    macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                    # Verificar RSI > 50
                    if rsi.iloc[i] > 50:
                        # Verificar mitigación (pullback al BOS)
                        if self._is_pullback_to_bos(df, i, bos_choch):
                            signals.append({
                                'type': 'BUY',
                                'strategy': 'BOS + Mitigation',
                                'index': i,
                                'price': current_candle['close'],
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_bos_mitigation(window_df, i, macd_line, signal_line, rsi)
                            })
            
            # Verificar BOS bajista
            elif not np.isnan(bos_choch['BOS'].iloc[i]) and bos_choch['BOS'].iloc[i] == -1:
                # Confirmar con MACD crossover bajista
                if (macd_line.iloc[i] < signal_line.iloc[i] and 
                    macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                    # Verificar RSI < 50
                    if rsi.iloc[i] < 50:
                        # Verificar mitigación (pullback al BOS)
                        if self._is_pullback_to_bos(df, i, bos_choch):
                            signals.append({
                                'type': 'SELL',
                                'strategy': 'BOS + Mitigation',
                                'index': i,
                                'price': current_candle['close'],
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_bos_mitigation(window_df, i, macd_line, signal_line, rsi)
                            })
        
        return signals
    
    def analyze_strategy_2_order_block_fibonacci(self, df, indicators):
        """
        ESTRATEGIA 2: ORDER BLOCK + FIBONACCI
        Detecta señales en Order Blocks con retrocesos Fibonacci
        """
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        rsi = indicators['rsi']
        ob_data = indicators['ob_data']
        
        for i in range(10, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar Order Block alcista
            if not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == 1:
                # Analizar retroceso Fibonacci
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    retracement = (recent_high - current_price) / (recent_high - recent_low)
                    
                    # Verificar retroceso entre 61.8% y 78.6%
                    if self.fib_min <= retracement <= self.fib_max:
                        # Confirmar con MACD
                        if (macd_line.iloc[i] > signal_line.iloc[i] and 
                            macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                            # Verificar RSI > 30
                            if rsi.iloc[i] > 30:
                                signals.append({
                                    'type': 'BUY',
                                    'strategy': 'Order Block + Fibonacci',
                                    'index': i,
                                    'price': current_price,
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_ob_fib(window_df, i, macd_line, rsi, retracement)
                                })
            
            # Verificar Order Block bajista
            elif not np.isnan(ob_data['OB'].iloc[i]) and ob_data['OB'].iloc[i] == -1:
                # Analizar retroceso Fibonacci
                recent_high = df['high'].iloc[max(0, i-10):i+1].max()
                recent_low = df['low'].iloc[max(0, i-10):i+1].min()
                
                if recent_high > recent_low:
                    retracement = (current_price - recent_low) / (recent_high - recent_low)
                    
                    if self.fib_min <= retracement <= self.fib_max:
                        # Confirmar con MACD
                        if (macd_line.iloc[i] < signal_line.iloc[i] and 
                            macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                            # Verificar RSI < 70
                            if rsi.iloc[i] < 70:
                                signals.append({
                                    'type': 'SELL',
                                    'strategy': 'Order Block + Fibonacci',
                                    'index': i,
                                    'price': current_price,
                                    'timestamp': df.index[i],
                                    'confidence': self._calculate_confidence_ob_fib(window_df, i, macd_line, rsi, retracement)
                                })
        
        return signals
    
    def analyze_strategy_3_fair_value_gap(self, df, indicators):
        """
        ESTRATEGIA 3: FAIR VALUE GAP (FVG)
        Detecta señales en Fair Value Gaps
        """
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        rsi = indicators['rsi']
        fvg_data = indicators['fvg_data']
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_price = df['close'].iloc[i]
            
            # Verificar FVG alcista
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
                                'confidence': self._calculate_confidence_fvg(window_df, i, macd_line, signal_line, rsi)
                            })
            
            # Verificar FVG bajista
            elif not np.isnan(fvg_data['FVG'].iloc[i]) and fvg_data['FVG'].iloc[i] == -1:
                fvg_top = fvg_data['Top'].iloc[i]
                fvg_bottom = fvg_data['Bottom'].iloc[i]
                
                if fvg_bottom < current_price < fvg_top:
                    # Verificar MACD crossover bajista cerca del FVG
                    if (macd_line.iloc[i] < signal_line.iloc[i] and 
                        macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                        # Verificar RSI entre 40-50
                        if 40 <= rsi.iloc[i] <= 50:
                            signals.append({
                                'type': 'SELL',
                                'strategy': 'Fair Value Gap',
                                'index': i,
                                'price': current_price,
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_fvg(window_df, i, macd_line, signal_line, rsi)
                            })
        
        return signals
    
    def analyze_strategy_4_liquidity_grab(self, df, indicators):
        """
        ESTRATEGIA 4: LIQUIDITY GRAB
        Detecta señales de reversión en zonas de liquidez
        """
        signals = []
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        rsi = indicators['rsi']
        liquidity_data = indicators['liquidity_data']
        
        for i in range(5, len(df)):
            window_df = df.iloc[:i+1]
            current_candle = df.iloc[i]
            
            # Verificar Liquidity Grab alcista
            if not np.isnan(liquidity_data['Liquidity'].iloc[i]) and liquidity_data['Liquidity'].iloc[i] == 1:
                # Verificar patrón de rechazo alcista
                if self._is_rejection_pattern_bullish(current_candle):
                    # Confirmar con MACD crossover alcista
                    if (macd_line.iloc[i] > signal_line.iloc[i] and 
                        macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                        # Verificar RSI > 50
                        if rsi.iloc[i] > 50:
                            signals.append({
                                'type': 'BUY',
                                'strategy': 'Liquidity Grab',
                                'index': i,
                                'price': current_candle['close'],
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_liquidity(window_df, i, macd_line, signal_line, rsi)
                            })
            
            # Verificar Liquidity Grab bajista
            elif not np.isnan(liquidity_data['Liquidity'].iloc[i]) and liquidity_data['Liquidity'].iloc[i] == -1:
                # Verificar patrón de rechazo bajista
                if self._is_rejection_pattern_bearish(current_candle):
                    # Confirmar con MACD crossover bajista
                    if (macd_line.iloc[i] < signal_line.iloc[i] and 
                        macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                        # Verificar RSI < 50
                        if rsi.iloc[i] < 50:
                            signals.append({
                                'type': 'SELL',
                                'strategy': 'Liquidity Grab',
                                'index': i,
                                'price': current_candle['close'],
                                'timestamp': df.index[i],
                                'confidence': self._calculate_confidence_liquidity(window_df, i, macd_line, signal_line, rsi)
                            })
        
        return signals
    
    def analyze_all_strategies(self, df):
        """
        Analizar todas las estrategias y devolver señales combinadas
        """
        # Precalcular todos los indicadores
        indicators = self.precalculate_indicators(df)
        
        # Analizar cada estrategia
        signals_1 = self.analyze_strategy_1_bos_mitigation(df, indicators)
        signals_2 = self.analyze_strategy_2_order_block_fibonacci(df, indicators)
        signals_3 = self.analyze_strategy_3_fair_value_gap(df, indicators)
        signals_4 = self.analyze_strategy_4_liquidity_grab(df, indicators)
        
        # Combinar todas las señales
        all_signals = signals_1 + signals_2 + signals_3 + signals_4
        
        # Ordenar por índice
        all_signals.sort(key=lambda x: x['index'])
        
        return all_signals
    
    # ===== MÉTODOS AUXILIARES =====
    
    def _is_pullback_to_bos(self, df, index, bos_choch):
        """Verificar si hay un pullback al BOS"""
        if index < 3:
            return False
        
        # Buscar el último BOS
        for i in range(index-1, max(0, index-10), -1):
            if not np.isnan(bos_choch['BOS'].iloc[i]) and bos_choch['BOS'].iloc[i] != 0:
                # Verificar si el precio actual está cerca del nivel del BOS
                bos_level = bos_choch['Level'].iloc[i]
                current_price = df['close'].iloc[index]
                
                # Tolerancia del 0.1%
                tolerance = bos_level * 0.001
                return abs(current_price - bos_level) <= tolerance
        
        return False
    
    def _is_rejection_pattern_bullish(self, candle):
        """Verificar patrón de rechazo alcista (Pin bar o engulfing)"""
        o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
        body = abs(c - o)
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        
        # Pin bar alcista
        if body < (h - l) * 0.3 and lower_wick > upper_wick * 1.5:
            return True
        
        return False
    
    def _is_rejection_pattern_bearish(self, candle):
        """Verificar patrón de rechazo bajista (Pin bar o engulfing)"""
        o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
        body = abs(c - o)
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        
        # Pin bar bajista
        if body < (h - l) * 0.3 and upper_wick > lower_wick * 1.5:
            return True
        
        return False
    
    def _calculate_confidence_bos_mitigation(self, df, index, macd_line, signal_line, rsi):
        """Calcular nivel de confianza para BOS + Mitigation"""
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
        
        # Mitigación clara
        confidence += 25
        
        return min(confidence, 100)
    
    def _calculate_confidence_ob_fib(self, df, index, macd_line, rsi, retracement):
        """Calcular nivel de confianza para Order Block + Fibonacci"""
        confidence = 0
        
        # Retroceso Fibonacci óptimo
        if 0.65 <= retracement <= 0.75:
            confidence += 25
        elif self.fib_min <= retracement <= self.fib_max:
            confidence += 15
        
        # MACD crossover
        if macd_line.iloc[index] > macd_line.iloc[index-1]:
            confidence += 25
        
        # RSI en zona de recuperación
        if 35 <= rsi.iloc[index] <= 65:
            confidence += 20
        
        # Volumen confirmación
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.2:
                confidence += 15
        
        return min(confidence, 100)
    
    def _calculate_confidence_fvg(self, df, index, macd_line, signal_line, rsi):
        """Calcular nivel de confianza para Fair Value Gap"""
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
    
    def _calculate_confidence_liquidity(self, df, index, macd_line, signal_line, rsi):
        """Calcular nivel de confianza para Liquidity Grab"""
        confidence = 0
        
        # MACD crossover
        if macd_line.iloc[index] > signal_line.iloc[index]:
            confidence += 30
        
        # RSI en zona fuerte
        if 60 <= rsi.iloc[index] <= 80:
            confidence += 25
        
        # Patrón de rechazo claro
        confidence += 25
        
        # Volumen alto
        if 'volume' in df.columns and index > 0:
            avg_volume = df['volume'].iloc[max(0, index-20):index].mean()
            if df['volume'].iloc[index] > avg_volume * 1.5:
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
