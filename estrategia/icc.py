"""
ICC Strategy - Imbalance Context Confirmation
Estrategia de trading basada en Smart Money Concepts (SMC)

Esta estrategia combina:
1. Contexto desde temporalidades superiores (H1, H4)
2. Identificación de Order Blocks (OB)
3. Detección de Fair Value Gaps (FVG)
4. Espera de pullback y confirmación
5. Break of Structure (BOS) para entrada
6. Gestión de riesgo con R:R mínimo 1:3

Autor: SmartMoneyPython
Versión: 1.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Importar librerías SMC
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib


class ICCStrategy:
    """
    Estrategia ICC - Imbalance Context Confirmation
    
    Combina análisis de múltiples timeframes con detección de zonas de imbalance
    para identificar entradas de alta probabilidad en el mercado.
    """
    
    def __init__(self, 
                 risk_reward_min: float = 3.0,
                 ob_lookback: int = 50,
                 fvg_lookback: int = 30,
                 swing_length: int = 20):
        """
        Inicializar estrategia ICC
        
        Parámetros:
        -----------
        risk_reward_min : float
            Ratio riesgo/beneficio mínimo requerido (por defecto: 3.0)
        ob_lookback : int
            Períodos hacia atrás para buscar Order Blocks (por defecto: 50)
        fvg_lookback : int
            Períodos hacia atrás para buscar FVG (por defecto: 30)
        swing_length : int
            Longitud para identificar swing highs/lows (por defecto: 20)
        """
        self.risk_reward_min = risk_reward_min
        self.ob_lookback = ob_lookback
        self.fvg_lookback = fvg_lookback
        self.swing_length = swing_length
        
        # Inicializar MarketAnalysisLib
        self.market_analysis = MarketAnalysisLib()
        
        # Almacenar contexto de timeframes superiores
        self.h1_context = None
        self.h4_context = None
        
        # Almacenar señales detectadas
        self.signals = []
        
        print(f"🚀 Estrategia ICC inicializada")
        print(f"   📊 R:R mínimo: 1:{risk_reward_min}")
        print(f"   🔍 Lookback OB: {ob_lookback} períodos")
        print(f"   🔍 Lookback FVG: {fvg_lookback} períodos")
        print(f"   🔍 Swing length: {swing_length} períodos")
    
    def analyze_higher_timeframes(self, df_5m: pd.DataFrame, df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
        """
        1. CONTEXTO DESDE TEMPORALIDADES SUPERIORES
        
        Analiza H1 y H4 para determinar la tendencia mayor y evitar operar contra corriente.
        
        Parámetros:
        -----------
        df_5m : DataFrame
            Datos de 5 minutos (timeframe de operación)
        df_1h : DataFrame
            Datos de 1 hora (contexto intermedio)
        df_4h : DataFrame
            Datos de 4 horas (contexto mayor)
        
        Retorna:
        --------
        Dict con contexto de timeframes superiores
        """
        print(f"\n🔍 ANALIZANDO CONTEXTO DE TIMEFRAMES SUPERIORES...")
        
        context = {
            'h1_trend': None,
            'h4_trend': None,
            'overall_bias': None,
            'trend_strength': 0,
            'recommended_direction': None
        }
        
        try:
            # Analizar tendencia H1
            if len(df_1h) >= 20:
                h1_trend_result = self.market_analysis.detect_trend(df_1h, method='structural')
                h1_trend = h1_trend_result['trend'].iloc[-1]
                
                if h1_trend > 0.5:
                    context['h1_trend'] = 'ALCISTA'
                    print(f"   ✅ H1: Tendencia ALCISTA (fuerza: {h1_trend:.2f})")
                elif h1_trend < -0.5:
                    context['h1_trend'] = 'BAJISTA'
                    print(f"   ✅ H1: Tendencia BAJISTA (fuerza: {h1_trend:.2f})")
                else:
                    context['h1_trend'] = 'LATERAL'
                    print(f"   ⚠️ H1: Tendencia LATERAL (fuerza: {h1_trend:.2f})")
            else:
                print(f"   ❌ H1: Datos insuficientes ({len(df_1h)} velas)")
            
            # Analizar tendencia H4
            if len(df_4h) >= 20:
                h4_trend_result = self.market_analysis.detect_trend(df_4h, method='structural')
                h4_trend = h4_trend_result['trend'].iloc[-1]
                
                if h4_trend > 0.5:
                    context['h4_trend'] = 'ALCISTA'
                    print(f"   ✅ H4: Tendencia ALCISTA (fuerza: {h4_trend:.2f})")
                elif h4_trend < -0.5:
                    context['h4_trend'] = 'BAJISTA'
                    print(f"   ✅ H4: Tendencia BAJISTA (fuerza: {h4_trend:.2f})")
                else:
                    context['h4_trend'] = 'LATERAL'
                    print(f"   ⚠️ H4: Tendencia LATERAL (fuerza: {h4_trend:.2f})")
            else:
                print(f"   ❌ H4: Datos insuficientes ({len(df_4h)} velas)")
            
            # Determinar sesgo general
            if context['h1_trend'] and context['h4_trend']:
                if context['h1_trend'] == context['h4_trend'] and context['h1_trend'] != 'LATERAL':
                    context['overall_bias'] = context['h1_trend']
                    context['trend_strength'] = 2  # Máxima fuerza
                    print(f"   🎯 SESGO GENERAL: {context['overall_bias']} (ALINEADO H1+H4)")
                elif context['h1_trend'] != 'LATERAL':
                    context['overall_bias'] = context['h1_trend']
                    context['trend_strength'] = 1  # Fuerza media
                    print(f"   🎯 SESGO GENERAL: {context['overall_bias']} (H1 dominante)")
                else:
                    context['overall_bias'] = 'LATERAL'
                    context['trend_strength'] = 0
                    print(f"   ⚠️ SESGO GENERAL: LATERAL (evitar operaciones)")
                
                # Recomendación de dirección
                if context['overall_bias'] == 'ALCISTA':
                    context['recommended_direction'] = 'LONG'
                    print(f"   📈 RECOMENDACIÓN: Buscar entradas ALCISTAS")
                elif context['overall_bias'] == 'BAJISTA':
                    context['recommended_direction'] = 'SHORT'
                    print(f"   📉 RECOMENDACIÓN: Buscar entradas BAJISTAS")
                else:
                    context['recommended_direction'] = 'NEUTRAL'
                    print(f"   ⏸️ RECOMENDACIÓN: Mantener NEUTRAL")
            
            # Guardar contexto
            self.h1_context = context['h1_trend']
            self.h4_context = context['h4_trend']
            
        except Exception as e:
            print(f"   ❌ Error analizando timeframes superiores: {e}")
        
        return context
    
    def identify_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        2. MARCAR ZONAS CLAVE (Order Blocks)
        
        Identifica Order Blocks en el timeframe de operación (5M) que actúan
        como soporte o resistencia refinada.
        
        Parámetros:
        -----------
        df : DataFrame
            Datos OHLC del timeframe de operación
        
        Retorna:
        --------
        DataFrame con Order Blocks identificados
        """
        print(f"\n🔍 IDENTIFICANDO ORDER BLOCKS...")
        
        try:
            # Obtener swing highs/lows para identificar OB
            swing_data = smc.swing_highs_lows(df, swing_length=self.swing_length)
            print(f"   🔍 Swing data obtenida: {len(swing_data)} filas")
            print(f"   🔍 Swing data columns: {swing_data.columns.tolist() if hasattr(swing_data, 'columns') else 'No columns'}")
            
            # Identificar Order Blocks
            ob_data = smc.ob(df, swing_data, close_mitigation=False)
            print(f"   🔍 OB data obtenida: {type(ob_data)}")
            if ob_data is not None:
                print(f"   🔍 OB data length: {len(ob_data)}")
                print(f"   🔍 OB data sample: {ob_data.head() if hasattr(ob_data, 'head') else ob_data[:5]}")
            
            if ob_data is not None and not ob_data.empty:
                # Convertir Series a DataFrame si es necesario
                if isinstance(ob_data, pd.Series):
                    # Crear DataFrame con la columna OB
                    ob_df = pd.DataFrame({
                        'OB': ob_data.values,
                        'index': ob_data.index
                    })
                    ob_df.set_index('index', inplace=True)
                else:
                    ob_df = ob_data
                
                # Filtrar solo los OB más recientes
                recent_ob = ob_df.tail(self.ob_lookback)
                
                # Contar OB por tipo (1 = alcista, -1 = bajista, 0 = neutral)
                bullish_ob = recent_ob[recent_ob['OB'] == 1]
                bearish_ob = recent_ob[recent_ob['OB'] == -1]
                neutral_ob = recent_ob[recent_ob['OB'] == 0]
                
                print(f"   ✅ Order Blocks identificados:")
                print(f"      • ALCISTAS: {len(bullish_ob)}")
                print(f"      • BAJISTAS: {len(bearish_ob)}")
                print(f"      • NEUTRALES: {len(neutral_ob)}")
                print(f"      • Total: {len(recent_ob)}")
                
                # Mostrar algunos detalles de los OB encontrados
                if len(bullish_ob) > 0:
                    print(f"      📈 OB Alcistas en índices: {bullish_ob.index.tolist()[:5]}")
                if len(bearish_ob) > 0:
                    print(f"      📉 OB Bajistas en índices: {bearish_ob.index.tolist()[:5]}")
                
                return recent_ob
            else:
                print(f"   ⚠️ No se encontraron Order Blocks")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"   ❌ Error identificando Order Blocks: {e}")
            print(f"   🔍 Debug: ob_data type: {type(ob_data)}")
            if ob_data is not None:
                print(f"   🔍 Debug: ob_data shape: {ob_data.shape if hasattr(ob_data, 'shape') else 'No shape'}")
                print(f"   🔍 Debug: ob_data head: {ob_data.head() if hasattr(ob_data, 'head') else ob_data[:5]}")
            return pd.DataFrame()
    
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        3. IDENTIFICAR FAIR VALUE GAPS (FVG)
        
        Busca zonas de imbalances que tienden a atraer el precio y funcionar
        como puntos óptimos de entrada.
        
        Parámetros:
        -----------
        df : DataFrame
            Datos OHLC del timeframe de operación
        
        Retorna:
        --------
        DataFrame con FVG identificados
        """
        print(f"\n🔍 IDENTIFICANDO FAIR VALUE GAPS...")
        
        try:
            # Identificar FVG con join_consecutive para evitar duplicados
            fvg_data = smc.fvg(df, join_consecutive=True)
            print(f"   🔍 FVG data obtenida: {type(fvg_data)}")
            if fvg_data is not None:
                print(f"   🔍 FVG data length: {len(fvg_data)}")
                print(f"   🔍 FVG data sample: {fvg_data.head() if hasattr(fvg_data, 'head') else fvg_data[:5]}")
            
            if fvg_data is not None and not fvg_data.empty:
                # Convertir Series a DataFrame si es necesario
                if isinstance(fvg_data, pd.Series):
                    # Crear DataFrame con la columna FVG
                    fvg_df = pd.DataFrame({
                        'FVG': fvg_data.values,
                        'index': fvg_data.index
                    })
                    fvg_df.set_index('index', inplace=True)
                else:
                    fvg_df = fvg_data
                
                # Filtrar solo los FVG más recientes
                recent_fvg = fvg_df.tail(self.fvg_lookback)
                
                # Contar FVG por tipo (1 = alcista, -1 = bajista, NaN = no hay FVG)
                bullish_fvg = recent_fvg[recent_fvg['FVG'] == 1]
                bearish_fvg = recent_fvg[recent_fvg['FVG'] == -1]
                no_fvg = recent_fvg[recent_fvg['FVG'].isna()]
                
                print(f"   ✅ Fair Value Gaps identificados:")
                print(f"      • ALCISTAS: {len(bullish_fvg)}")
                print(f"      • BAJISTAS: {len(bearish_fvg)}")
                print(f"      • SIN FVG: {len(no_fvg)}")
                print(f"      • Total: {len(recent_fvg)}")
                
                # Mostrar algunos detalles de los FVG encontrados
                if len(bullish_fvg) > 0:
                    print(f"      📈 FVG Alcistas en índices: {bullish_fvg.index.tolist()[:5]}")
                if len(bearish_fvg) > 0:
                    print(f"      📉 FVG Bajistas en índices: {bearish_fvg.index.tolist()[:5]}")
                
                return recent_fvg
            else:
                print(f"   ⚠️ No se encontraron Fair Value Gaps")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"   ❌ Error identificando FVG: {e}")
            return pd.DataFrame()
    
    def wait_for_pullback(self, df: pd.DataFrame, ob_data: pd.DataFrame, fvg_data: pd.DataFrame) -> List[Dict]:
        """
        4. WAIT FOR PULLBACK (Espera retroceso)
        
        Identifica cuando el precio retorna a zonas de OB o FVG y busca
        velas de rechazo claras que sugieren respeto del nivel.
        
        Parámetros:
        -----------
        df : DataFrame
            Datos OHLC del timeframe de operación
        ob_data : DataFrame
            Order Blocks identificados
        fvg_data : DataFrame
            Fair Value Gaps identificados
        
        Retorna:
        --------
        Lista de señales de pullback identificadas
        """
        print(f"\n🔍 ANALIZANDO PULLBACKS...")
        
        pullback_signals = []
        
        try:
            # Analizar las últimas velas para pullbacks
            recent_candles = df.tail(10)  # Últimas 10 velas
            
            for i, candle in recent_candles.iterrows():
                current_price = candle['close']
                current_high = candle['high']
                current_low = candle['low']
                current_open = candle['open']
                
                # Verificar si el precio está cerca de un OB
                for _, ob in ob_data.iterrows():
                    if ob['OB'] != 0:  # Si es un OB válido
                        ob_top = ob['Top']
                        ob_bottom = ob['Bottom']
                        
                        # Verificar si el precio está dentro o cerca del OB
                        if ob_bottom <= current_price <= ob_top:
                            # Buscar velas de rechazo
                            rejection_signal = self._detect_rejection_candle(
                                candle, ob['OB'], ob_top, ob_bottom
                            )
                            
                            if rejection_signal:
                                signal = {
                                    'type': 'OB_PULLBACK',
                                    'direction': 'LONG' if ob['OB'] == 1 else 'SHORT',
                                    'price': current_price,
                                    'ob_top': ob_top,
                                    'ob_bottom': ob_bottom,
                                    'strength': rejection_signal['strength'],
                                    'timestamp': i,
                                    'source': 'Order Block'
                                }
                                pullback_signals.append(signal)
                                print(f"   ✅ Pullback detectado en OB: {signal['direction']} en {i}")
                
                # Verificar si el precio está cerca de un FVG
                for _, fvg in fvg_data.iterrows():
                    if not pd.isna(fvg['FVG']):  # Si es un FVG válido
                        fvg_top = fvg['Top']
                        fvg_bottom = fvg['Bottom']
                        
                        # Verificar si el precio está dentro o cerca del FVG
                        if fvg_bottom <= current_price <= fvg_top:
                            # Buscar velas de rechazo
                            rejection_signal = self._detect_rejection_candle(
                                candle, fvg['FVG'], fvg_top, fvg_bottom
                            )
                            
                            if rejection_signal:
                                signal = {
                                    'type': 'FVG_PULLBACK',
                                    'direction': 'LONG' if fvg['FVG'] == 1 else 'SHORT',
                                    'price': current_price,
                                    'fvg_top': fvg_top,
                                    'fvg_bottom': fvg_bottom,
                                    'strength': rejection_signal['strength'],
                                    'timestamp': i,
                                    'source': 'Fair Value Gap'
                                }
                                pullback_signals.append(signal)
                                print(f"   ✅ Pullback detectado en FVG: {signal['direction']} en {i}")
            
            print(f"   📊 Total de señales de pullback: {len(pullback_signals)}")
            
        except Exception as e:
            print(f"   ❌ Error analizando pullbacks: {e}")
        
        return pullback_signals
    
    def _detect_rejection_candle(self, candle: pd.Series, direction: int, top: float, bottom: float) -> Optional[Dict]:
        """
        Detecta velas de rechazo en zonas de OB o FVG
        
        Parámetros:
        -----------
        candle : Series
            Vela actual
        direction : int
            Dirección del OB/FVG (1: alcista, -1: bajista)
        top : float
            Precio superior de la zona
        bottom : float
            Precio inferior de la zona
        
        Retorna:
        --------
        Dict con información de rechazo o None
        """
        try:
            open_price = candle['open']
            close_price = candle['close']
            high_price = candle['high']
            low_price = candle['low']
            
            # Calcular tamaño de la vela
            body_size = abs(close_price - open_price)
            total_range = high_price - low_price
            
            # Calcular sombras
            upper_shadow = high_price - max(open_price, close_price)
            lower_shadow = min(open_price, close_price) - low_price
            
            rejection_strength = 0
            
            if direction == 1:  # OB/FVG alcista
                # Buscar rechazo en la parte superior
                if close_price < open_price:  # Vela roja
                    if upper_shadow > body_size * 0.5:  # Sombra superior notable
                        rejection_strength = 1
                    if close_price < (top + bottom) / 2:  # Cierre en mitad inferior
                        rejection_strength += 1
                        
            elif direction == -1:  # OB/FVG bajista
                # Buscar rechazo en la parte inferior
                if close_price > open_price:  # Vela verde
                    if lower_shadow > body_size * 0.5:  # Sombra inferior notable
                        rejection_strength = 1
                    if close_price > (top + bottom) / 2:  # Cierre en mitad superior
                        rejection_strength += 1
            
            if rejection_strength > 0:
                return {
                    'strength': rejection_strength,
                    'body_size': body_size,
                    'upper_shadow': upper_shadow,
                    'lower_shadow': lower_shadow
                }
            
        except Exception as e:
            print(f"   ❌ Error detectando vela de rechazo: {e}")
        
        return None
    
    def confirm_break_of_structure(self, df: pd.DataFrame, pullback_signals: List[Dict]) -> List[Dict]:
        """
        5. CONFIRMACIÓN: BREAK OF STRUCTURE (BOS)
        
        Confirma la entrada tras el toque y rechazo, esperando que el precio
        rompa un swing high (tendencia alcista) o swing low (bajista).
        
        Parámetros:
        -----------
        df : DataFrame
            Datos OHLC del timeframe de operación
        pullback_signals : List[Dict]
            Señales de pullback identificadas
        
        Retorna:
        --------
        Lista de señales confirmadas con BOS
        """
        print(f"\n🔍 CONFIRMANDO BREAK OF STRUCTURE...")
        
        confirmed_signals = []
        
        try:
            # Obtener swing highs/lows para identificar BOS
            swing_data = smc.swing_highs_lows(df, swing_length=self.swing_length)
            
            for signal in pullback_signals:
                # Buscar BOS después del pullback
                bos_detected = self._detect_bos(
                    df, swing_data, signal, lookback_periods=5
                )
                
                if bos_detected:
                    # Agregar información de BOS a la señal
                    signal['bos_confirmed'] = True
                    signal['bos_price'] = bos_detected['price']
                    signal['bos_timestamp'] = bos_detected['timestamp']
                    signal['entry_price'] = bos_detected['price']
                    
                    confirmed_signals.append(signal)
                    print(f"   ✅ BOS confirmado para {signal['direction']} en {signal['bos_timestamp']}")
                else:
                    print(f"   ⏳ Esperando BOS para {signal['direction']}")
            
            print(f"   📊 Total de señales confirmadas: {len(confirmed_signals)}")
            
        except Exception as e:
            print(f"   ❌ Error confirmando BOS: {e}")
        
        return confirmed_signals
    
    def _detect_bos(self, df: pd.DataFrame, swing_data: pd.DataFrame, signal: Dict, lookback_periods: int = 5) -> Optional[Dict]:
        """
        Detecta Break of Structure después de un pullback
        
        Parámetros:
        -----------
        df : DataFrame
            Datos OHLC
        swing_data : DataFrame
            Datos de swing highs/lows
        signal : Dict
            Señal de pullback
        lookback_periods : int
            Períodos hacia atrás para buscar BOS
        
        Retorna:
        --------
        Dict con información de BOS o None
        """
        try:
            signal_timestamp = signal['timestamp']
            
            # Buscar en los períodos después del pullback
            start_idx = df.index.get_loc(signal_timestamp) + 1
            end_idx = min(start_idx + lookback_periods, len(df))
            
            if start_idx >= len(df):
                return None
            
            # Obtener datos después del pullback
            post_pullback_data = df.iloc[start_idx:end_idx]
            
            if signal['direction'] == 'LONG':
                # Buscar ruptura de swing high
                for i, candle in post_pullback_data.iterrows():
                    if candle['high'] > signal.get('ob_top', signal.get('fvg_top', 0)):
                        return {
                            'price': candle['high'],
                            'timestamp': i,
                            'type': 'swing_high_break'
                        }
                        
            elif signal['direction'] == 'SHORT':
                # Buscar ruptura de swing low
                for i, candle in post_pullback_data.iterrows():
                    if candle['low'] < signal.get('ob_bottom', signal.get('fvg_bottom', 0)):
                        return {
                            'price': candle['low'],
                            'timestamp': i,
                            'type': 'swing_low_break'
                        }
            
        except Exception as e:
            print(f"   ❌ Error detectando BOS: {e}")
        
        return None
    
    def calculate_risk_reward(self, signal: Dict, df: pd.DataFrame) -> Dict:
        """
        6. GESTIÓN DE LA OPERACIÓN
        
        Calcula Stop Loss, Take Profit y ratio riesgo/beneficio.
        
        Parámetros:
        -----------
        signal : Dict
            Señal confirmada
        df : DataFrame
            Datos OHLC para cálculos
        
        Retorna:
        --------
        Dict con niveles de SL, TP y R:R
        """
        print(f"\n🔍 CALCULANDO GESTIÓN DE RIESGO...")
        
        try:
            entry_price = signal['entry_price']
            direction = signal['direction']
            
            # Calcular Stop Loss (punto más alejado)
            if direction == 'LONG':
                if 'ob_bottom' in signal:
                    stop_loss = signal['ob_bottom'] * 0.999  # Justo fuera del OB
                elif 'fvg_bottom' in signal:
                    stop_loss = signal['fvg_bottom'] * 0.999  # Justo fuera del FVG
                else:
                    stop_loss = entry_price * 0.995  # 0.5% por defecto
                    
                # Take Profit 1:3 (punto más alejado)
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * self.risk_reward_min)
                
            else:  # SHORT
                if 'ob_top' in signal:
                    stop_loss = signal['ob_top'] * 1.001  # Justo fuera del OB
                elif 'fvg_top' in signal:
                    stop_loss = signal['fvg_top'] * 1.001  # Justo fuera del FVG
                else:
                    stop_loss = entry_price * 1.005  # 0.5% por defecto
                    
                # Take Profit 1:3 (punto más alejado)
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * self.risk_reward_min)
            
            # Calcular R:R
            risk_amount = abs(entry_price - stop_loss)
            reward_amount = abs(take_profit - entry_price)
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            
            # Verificar si cumple R:R mínimo
            meets_min_ratio = risk_reward_ratio >= self.risk_reward_min
            
            risk_management = {
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_amount': risk_amount,
                'reward_amount': reward_amount,
                'risk_reward_ratio': risk_reward_ratio,
                'meets_min_ratio': meets_min_ratio,
                'direction': direction
            }
            
            print(f"   ✅ Gestión de riesgo calculada:")
            print(f"      • Entrada: {entry_price:.5f}")
            print(f"      • Stop Loss: {stop_loss:.5f}")
            print(f"      • Take Profit: {take_profit:.5f}")
            print(f"      • R:R: 1:{risk_reward_ratio:.2f}")
            print(f"      • Cumple R:R mínimo: {'✅' if meets_min_ratio else '❌'}")
            
            return risk_management
            
        except Exception as e:
            print(f"   ❌ Error calculando gestión de riesgo: {e}")
            return {}
    
    def scan_for_icc_signals(self, df_5m: pd.DataFrame, df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> List[Dict]:
        """
        ESCANEO COMPLETO PARA SEÑALES ICC
        
        Ejecuta toda la estrategia ICC paso a paso.
        
        Parámetros:
        -----------
        df_5m : DataFrame
            Datos de 5 minutos (timeframe de operación)
        df_1h : DataFrame
            Datos de 1 hora (contexto intermedio)
        df_4h : DataFrame
            Datos de 4 horas (contexto mayor)
        
        Retorna:
        --------
        Lista de señales ICC completas
        """
        print(f"\n🚀 INICIANDO ESCANEO COMPLETO ICC...")
        print(f"=" * 60)
        
        try:
            # 1. Contexto desde temporalidades superiores
            context = self.analyze_higher_timeframes(df_5m, df_1h, df_4h)
            
            # Si no hay sesgo claro, no continuar
            if context['overall_bias'] == 'LATERAL' or context['trend_strength'] == 0:
                print(f"   ⚠️ No hay sesgo claro en timeframes superiores")
                print(f"   ⏸️ Pausando escaneo ICC...")
                return []
            
            # 2. Identificar Order Blocks
            ob_data = self.identify_order_blocks(df_5m)
            
            # 3. Identificar Fair Value Gaps
            fvg_data = self.identify_fair_value_gaps(df_5m)
            
            # Si no hay zonas de imbalance, no continuar
            if ob_data.empty and fvg_data.empty:
                print(f"   ⚠️ No se encontraron zonas de imbalance")
                print(f"   ⏸️ Pausando escaneo ICC...")
                return []
            
            # 4. Esperar pullback
            pullback_signals = self.wait_for_pullback(df_5m, ob_data, fvg_data)
            
            # Si no hay pullbacks, no continuar
            if not pullback_signals:
                print(f"   ⚠️ No se detectaron pullbacks")
                print(f"   ⏸️ Pausando escaneo ICC...")
                return []
            
            # 5. Confirmar Break of Structure
            confirmed_signals = self.confirm_break_of_structure(df_5m, pullback_signals)
            
            # Si no hay confirmaciones, no continuar
            if not confirmed_signals:
                print(f"   ⚠️ No se confirmaron señales con BOS")
                print(f"   ⏸️ Pausando escaneo ICC...")
                return []
            
            # 6. Calcular gestión de riesgo para cada señal
            final_signals = []
            for signal in confirmed_signals:
                risk_management = self.calculate_risk_reward(signal, df_5m)
                
                if risk_management and risk_management.get('meets_min_ratio', False):
                    # Agregar gestión de riesgo a la señal
                    signal['risk_management'] = risk_management
                    signal['context'] = context
                    signal['timestamp_analysis'] = datetime.now()
                    
                    final_signals.append(signal)
                    print(f"   🎯 SEÑAL ICC COMPLETA: {signal['direction']} en {signal['timestamp']}")
            
            print(f"\n🎯 ESCANEO ICC COMPLETADO")
            print(f"   📊 Total de señales ICC: {len(final_signals)}")
            print(f"   ✅ Todas las señales cumplen R:R mínimo 1:{self.risk_reward_min}")
            
            # Guardar señales
            self.signals = final_signals
            
            return final_signals
            
        except Exception as e:
            print(f"   ❌ Error en escaneo ICC: {e}")
            return []
    
    def get_signal_summary(self) -> Dict:
        """
        Obtiene resumen de las señales ICC detectadas
        """
        if not self.signals:
            return {'total_signals': 0, 'message': 'No hay señales ICC activas'}
        
        summary = {
            'total_signals': len(self.signals),
            'long_signals': len([s for s in self.signals if s['direction'] == 'LONG']),
            'short_signals': len([s for s in self.signals if s['direction'] == 'SHORT']),
            'avg_risk_reward': np.mean([s['risk_management']['risk_reward_ratio'] for s in self.signals]),
            'signals': []
        }
        
        for signal in self.signals:
            signal_info = {
                'direction': signal['direction'],
                'source': signal['source'],
                'entry_price': signal['entry_price'],
                'stop_loss': signal['risk_management']['stop_loss'],
                'take_profit': signal['risk_management']['take_profit'],
                'risk_reward_ratio': signal['risk_management']['risk_reward_ratio'],
                'timestamp': signal['timestamp']
            }
            summary['signals'].append(signal_info)
        
        return summary


# Función de ejemplo para usar la estrategia
def example_icc_usage():
    """
    Ejemplo de uso de la estrategia ICC
    """
    print("📚 EJEMPLO DE USO DE ESTRATEGIA ICC")
    print("=" * 50)
    
    # Crear instancia de la estrategia
    icc_strategy = ICCStrategy(
        risk_reward_min=3.0,
        ob_lookback=50,
        fvg_lookback=30,
        swing_length=20
    )
    
    print(f"\n🔧 Configuración de la estrategia:")
    print(f"   • R:R mínimo: 1:{icc_strategy.risk_reward_min}")
    print(f"   • Lookback OB: {icc_strategy.ob_lookback} períodos")
    print(f"   • Lookback FVG: {icc_strategy.fvg_lookback} períodos")
    print(f"   • Swing length: {icc_strategy.swing_length} períodos")
    
    print(f"\n📋 Pasos de la estrategia:")
    print(f"   1. Contexto desde temporalidades superiores (H1, H4)")
    print(f"   2. Marcar zonas clave (Order Blocks)")
    print(f"   3. Identificar Fair Value Gaps (FVG)")
    print(f"   4. Wait for Pullback (espera retroceso)")
    print(f"   5. Confirmación: Break of Structure (BOS)")
    print(f"   6. Gestión de la operación (SL, TP, R:R)")
    
    print(f"\n💡 Para usar la estrategia:")
    print(f"   # Crear instancia")
    print(f"   icc = ICCStrategy()")
    print(f"   ")
    print(f"   # Escanear señales")
    print(f"   signals = icc.scan_for_icc_signals(df_5m, df_1h, df_4h)")
    print(f"   ")
    print(f"   # Obtener resumen")
    print(f"   summary = icc.get_signal_summary()")
    
    return icc_strategy


if __name__ == "__main__":
    # Ejecutar ejemplo
    example_icc_usage()
