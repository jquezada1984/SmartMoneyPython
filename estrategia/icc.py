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
                 risk_reward_min: float = 1.0,  # Mínimo: 1:1 para operar
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
        print(f"   📊 R:R configurado: 1:1 mínimo (TP1), 1:2 (TP2), 1:3 (TP3)")
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
                    # print(f"   🔍 Swing data obtenida: {len(swing_data)} filas")
        # print(f"   🔍 Swing data columns: {swing_data.columns.tolist() if hasattr(swing_data, 'columns') else 'No columns'}")
            
            # Identificar Order Blocks
            ob_data = smc.ob(df, swing_data, close_mitigation=False)
                    # print(f"   🔍 OB data obtenida: {type(ob_data)}")
        # if ob_data is not None:
        #     print(f"   🔍 OB data length: {len(ob_data)}")
        #     print(f"   🔍 OB data sample: {ob_data.head() if hasattr(ob_data, 'head') else ob_data[:5]}")
            
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
            # print(f"   🔍 FVG data obtenida: {type(fvg_data)}")
            # if fvg_data is not None:
            #     print(f"   🔍 FVG data length: {len(fvg_data)}")
            #     print(f"   🔍 FVG data sample: {fvg_data.head() if hasattr(fvg_data, 'head') else fvg_data[:5]}")
            
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
                
                # print(f"   ✅ Fair Value Gaps identificados:")
                # print(f"      • ALCISTAS: {len(bullish_fvg)}")
                # print(f"      • BAJISTAS: {len(bearish_fvg)}")
                # print(f"      • SIN FVG: {len(no_fvg)}")
                # print(f"      • Total: {len(recent_fvg)}")
                
                # # Mostrar algunos detalles de los FVG encontrados
                # if len(bullish_fvg) > 0:
                #     print(f"      📈 FVG Alcistas en índices: {bullish_fvg.index.tolist()[:5]}")
                # if len(bearish_fvg) > 0:
                #     print(f"      📉 FVG Bajistas en índices: {bearish_fvg.index.tolist()[:5]}")
                
                return recent_fvg
            else:
                print(f"   ⚠️ No se encontraron Fair Value Gaps")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"   ❌ Error identificando FVG: {e}")
            return pd.DataFrame()
    
    def wait_for_pullback(self, df: pd.DataFrame, ob_data: pd.DataFrame, fvg_data: pd.DataFrame, context: Dict = None) -> List[Dict]:
        """
        4. WAIT FOR PULLBACK (Espera retroceso)
        
        Identifica cuando el precio retorna a zonas de OB o FVG y busca
        velas de rechazo claras que sugieren respeto del nivel.
        
        IMPORTANTE: Solo genera señales cuando hay confirmación de timeframes superiores
        
        Parámetros:
        -----------
        df : DataFrame
            Datos OHLC del timeframe de operación
        ob_data : DataFrame
            Order Blocks identificados
        fvg_data : DataFrame
            Fair Value Gaps identificados
        context : Dict
            Contexto de timeframes superiores (H1, H4)
        
        Retorna:
        --------
        Lista de señales de pullback identificadas
        """
        print(f"\n🔍 ANALIZANDO PULLBACKS...")
        
        pullback_signals = []
        
        # VALIDAR CONTEXTO DE TIMEFRAMES SUPERIORES
        if context is None:
            print(f"   ⚠️ No hay contexto de timeframes superiores")
            print(f"   ⏸️ Pausando análisis de pullbacks...")
            return []
        
        # Obtener tendencias de timeframes superiores
        h1_trend = context.get('h1_trend', 'LATERAL')
        h4_trend = context.get('h4_trend', 'LATERAL')
        
        print(f"   📊 Contexto de timeframes superiores:")
        print(f"      • H1: {h1_trend}")
        print(f"      • H4: {h4_trend}")
        
        # Determinar sesgo general
        overall_bias = context.get('overall_bias', 'LATERAL')
        print(f"      • Sesgo general: {overall_bias}")
        
        # REGLA: Solo generar señales cuando hay confirmación de timeframes superiores
        if overall_bias == 'LATERAL':
            print(f"   ⚠️ Sesgo LATERAL en timeframes superiores")
            print(f"   ⏸️ No se generarán señales sin confirmación de tendencia")
            return []
        
        try:
            # Analizar las últimas velas para pullbacks
            recent_candles = df.tail(10)  # Últimas 10 velas
            
            # DEBUG: Mostrar información de OB y FVG (comentado para reducir output)
            # print(f"   🔍 DEBUG - Datos de OB:")
            # if not ob_data.empty:
            #     print(f"      • OB data shape: {ob_data.shape}")
            #     print(f"      • OB columns: {ob_data.columns.tolist()}")
            #     print(f"      • OB sample: {ob_data.head(3)}")
            #     print(f"      • OB types: {ob_data.dtypes}")
            # else:
            #     print(f"      • OB data está vacío")
            
            # print(f"   🔍 DEBUG - Datos de FVG:")
            # if not fvg_data.empty:
            #     print(f"      • FVG data shape: {fvg_data.shape}")
            #     print(f"      • FVG columns: {fvg_data.columns.tolist()}")
            #     print(f"      • FVG sample: {fvg_data.head(3)}")
            #     print(f"      • FVG types: {fvg_data.dtypes}")
            # else:
            #     print(f"      • FVG data está vacío")
            
            for i, candle in recent_candles.iterrows():
                current_price = candle['close']
                current_high = candle['high']
                current_low = candle['low']
                current_open = candle['open']
                
                # Verificar si el precio está cerca de un OB
                for _, ob in ob_data.iterrows():
                    # DEBUG: Mostrar información del OB actual (comentado)
                    # print(f"   🔍 DEBUG - Procesando OB: {ob.to_dict()}")
                    
                    if ob['OB'] != 0:  # Si es un OB válido
                        ob_top = ob['Top']
                        ob_bottom = ob['Bottom']
                        
                        # print(f"   🔍 DEBUG - OB válido encontrado:")
                        # print(f"      • OB value: {ob['OB']} (tipo: {type(ob['OB'])})")
                        # print(f"      • Top: {ob_top}")
                        # print(f"      • Bottom: {ob_bottom}")
                        # print(f"      • Current price: {current_price}")
                        
                        # Verificar si el precio está dentro o cerca del OB
                        if ob_bottom <= current_price <= ob_top:
                            # print(f"   🔍 DEBUG - Precio dentro del OB")
                            
                            # VALIDAR DIRECCIÓN CON TIMEFRAMES SUPERIORES
                            ob_direction = 'LONG' if ob['OB'] == 1 else 'SHORT'
                            # print(f"   🔍 DEBUG - Dirección del OB: {ob_direction}")
                            
                            # Solo generar señal LONG si H1 o H4 son alcistas
                            if ob_direction == 'LONG' and overall_bias != 'ALCISTA':
                                # print(f"   ⚠️ OB alcista ignorado - H1/H4 no son alcistas")
                                continue
                            
                            # Solo generar señal SHORT si H1 o H4 son bajistas  
                            if ob_direction == 'SHORT' and overall_bias != 'BAJISTA':
                                # print(f"   ⚠️ OB bajista ignorado - H1/H4 no son bajistas")
                                continue
                            
                            # print(f"   🔍 DEBUG - OB validado, buscando vela de rechazo...")
                            
                            # Buscar velas de rechazo
                            rejection_signal = self._detect_rejection_candle(
                                candle, ob['OB'], ob_top, ob_bottom
                            )
                            
                            if rejection_signal:
                                signal = {
                                    'type': 'OB_PULLBACK',
                                    'direction': ob_direction,
                                    'price': current_price,
                                    'ob_top': ob_top,
                                    'ob_bottom': ob_bottom,
                                    'strength': rejection_signal['strength'],
                                    'timestamp': i,
                                    'source': 'Order Block'
                                }
                                pullback_signals.append(signal)
                                print(f"   ✅ Pullback detectado en OB: {signal['direction']} en {i}")
                            else:
                                print(f"   ⚠️ No se detectó vela de rechazo en OB")
                        else:
                            # print(f"   🔍 DEBUG - Precio fuera del OB")
                            pass
                    else:
                        # print(f"   🔍 DEBUG - OB no válido (valor: {ob['OB']})")
                        pass
                
                # Verificar si el precio está cerca de un FVG
                for _, fvg in fvg_data.iterrows():
                    # DEBUG: Mostrar información del FVG actual (comentado)
                    # print(f"   🔍 DEBUG - Procesando FVG: {fvg.to_dict()}")
                    
                    if not pd.isna(fvg['FVG']):  # Si es un FVG válido
                        fvg_top = fvg['Top']
                        fvg_bottom = fvg['Bottom']
                        
                        # print(f"   🔍 DEBUG - FVG válido encontrado:")
                        # print(f"      • FVG value: {fvg['FVG']} (tipo: {type(fvg['FVG'])})")
                        # print(f"      • Top: {fvg_top}")
                        # print(f"      • Bottom: {fvg_bottom}")
                        # print(f"      • Current price: {current_price}")
                        
                        # Verificar si el precio está dentro o cerca del FVG
                        if fvg_bottom <= current_price <= fvg_top:
                            # print(f"   🔍 DEBUG - Precio dentro del FVG")
                            
                            # VALIDAR DIRECCIÓN CON TIMEFRAMES SUPERIORES
                            fvg_direction = 'LONG' if fvg['FVG'] == 1 else 'SHORT'
                            # print(f"   🔍 DEBUG - Dirección del FVG: {fvg_direction}")
                            
                            # Solo generar señal LONG si H1 o H4 son alcistas
                            if fvg_direction == 'LONG' and overall_bias != 'ALCISTA':
                                # print(f"   ⚠️ FVG alcista ignorado - H1/H4 no son alcistas")
                                continue
                            
                            # Solo generar señal SHORT si H1 o H4 son bajistas
                            if fvg_direction == 'SHORT' and overall_bias != 'BAJISTA':
                                # print(f"   ⚠️ FVG bajista ignorado - H1/H4 no son bajistas")
                                continue
                            
                            # print(f"   🔍 DEBUG - FVG validado, buscando vela de rechazo...")
                            
                            # Buscar velas de rechazo
                            rejection_signal = self._detect_rejection_candle(
                                candle, fvg['FVG'], fvg_top, fvg_bottom
                            )
                            
                            if rejection_signal:
                                signal = {
                                    'type': 'FVG_PULLBACK',
                                    'direction': fvg_direction,
                                    'price': current_price,
                                    'fvg_top': fvg_top,
                                    'fvg_bottom': fvg_bottom,
                                    'strength': rejection_signal['strength'],
                                    'timestamp': i,
                                    'source': 'Fair Value Gap'
                                }
                                pullback_signals.append(signal)
                                print(f"   ✅ Pullback detectado en FVG: {signal['direction']} en {i}")
                            else:
                                print(f"   ⚠️ No se detectó vela de rechazo en FVG")
                        else:
                            # print(f"   🔍 DEBUG - Precio fuera del FVG")
                            pass
                    else:
                        # print(f"   🔍 DEBUG - FVG no válido (valor: {fvg['FVG']})")
                        pass
            
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
    
    def calculate_structural_take_profits(self, df: pd.DataFrame, entry_price: float, direction: str, 
                                        df_1h: pd.DataFrame = None, df_4h: pd.DataFrame = None) -> Dict:
        """
        Calcular Take Profits basándose en niveles estructurales
        
        Parámetros:
        -----------
        df : DataFrame
            Datos del timeframe de operación (5M)
        entry_price : float
            Precio de entrada
        direction : str
            Dirección de la operación ('LONG' o 'SHORT')
        df_1h : DataFrame
            Datos de 1H para análisis de marco mayor
        df_4h : DataFrame
            Datos de 4H para análisis de marco mayor
        
        Retorna:
        --------
        Dict con niveles de TP estructurales
        """
        try:
            tp_levels = {
                'tp1': None,  # R:R 1:1 mínimo
                'tp2': None,  # R:R 1:2
                'tp3': None,  # R:R 1:3
                'structural_levels': []
            }
            
            # 1. IDENTIFICAR SWING HIGHS/LOWS EN TIMEFRAMES SUPERIORES
            structural_levels = []
            
            # Analizar 1H si está disponible
            if df_1h is not None and len(df_1h) > 20:
                swing_1h = smc.swing_highs_lows(df_1h, swing_length=10)
                if not swing_1h.empty:
                    # Obtener niveles significativos
                    swing_highs_1h = swing_1h[swing_1h['HighLow'] == 1]['Level'].dropna()
                    swing_lows_1h = swing_1h[swing_1h['HighLow'] == -1]['Level'].dropna()
                    
                    if direction == 'LONG':
                        # Para LONG, buscar swing highs (resistencias) por encima del precio
                        resistance_levels = swing_highs_1h[swing_highs_1h > entry_price].sort_values()
                        if len(resistance_levels) > 0:
                            structural_levels.extend(resistance_levels.head(3).tolist())
                    else:  # SHORT
                        # Para SHORT, buscar swing lows (soportes) por debajo del precio
                        support_levels = swing_lows_1h[swing_lows_1h < entry_price].sort_values(ascending=False)
                        if len(support_levels) > 0:
                            structural_levels.extend(support_levels.head(3).tolist())
            
            # Analizar 4H si está disponible
            if df_4h is not None and len(df_4h) > 20:
                swing_4h = smc.swing_highs_lows(df_4h, swing_length=10)
                if not swing_4h.empty:
                    swing_highs_4h = swing_4h[swing_4h['HighLow'] == 1]['Level'].dropna()
                    swing_lows_4h = swing_4h[swing_4h['HighLow'] == -1]['Level'].dropna()
                    
                    if direction == 'LONG':
                        resistance_levels_4h = swing_highs_4h[swing_highs_4h > entry_price].sort_values()
                        if len(resistance_levels_4h) > 0:
                            structural_levels.extend(resistance_levels_4h.head(2).tolist())
                    else:  # SHORT
                        support_levels_4h = swing_lows_4h[swing_lows_4h < entry_price].sort_values(ascending=False)
                        if len(support_levels_4h) > 0:
                            structural_levels.extend(support_levels_4h.head(2).tolist())
            
            # 2. IDENTIFICAR ZONAS DE LIQUIDEZ
            # Buscar niveles donde hay alta actividad de volumen
            if len(df) > 20:
                volume_profile = df['volume'].rolling(window=10).mean()
                high_volume_levels = df[volume_profile > volume_profile.quantile(0.8)]
                
                if direction == 'LONG':
                    # Para LONG, buscar niveles de alta liquidez por encima
                    liquidity_levels = high_volume_levels[high_volume_levels['high'] > entry_price]['high'].unique()
                    structural_levels.extend(liquidity_levels[:3].tolist())
                else:  # SHORT
                    # Para SHORT, buscar niveles de alta liquidez por debajo
                    liquidity_levels = high_volume_levels[high_volume_levels['low'] < entry_price]['low'].unique()
                    structural_levels.extend(liquidity_levels[:3].tolist())
            
            # 3. IDENTIFICAR EQUAL LOWS/HIGHS
            if len(df) > 50:
                swing_data = smc.swing_highs_lows(df, swing_length=10)
                if not swing_data.empty:
                    if direction == 'LONG':
                        # Buscar equal highs (resistencias)
                        swing_highs = swing_data[swing_data['HighLow'] == 1]['Level'].dropna()
                        equal_highs = self._find_equal_levels(swing_highs, tolerance=0.001)
                        structural_levels.extend([level for level in equal_highs if level > entry_price][:2])
                    else:  # SHORT
                        # Buscar equal lows (soportes)
                        swing_lows = swing_data[swing_data['HighLow'] == -1]['Level'].dropna()
                        equal_lows = self._find_equal_levels(swing_lows, tolerance=0.001)
                        structural_levels.extend([level for level in equal_lows if level < entry_price][:2])
            
            # 4. CALCULAR TP BASÁNDOSE EN NIVELES ESTRUCTURALES
            if structural_levels:
                # Ordenar niveles según la dirección
                if direction == 'LONG':
                    structural_levels = sorted([level for level in structural_levels if level > entry_price])
                else:  # SHORT
                    structural_levels = sorted([level for level in structural_levels if level < entry_price], reverse=True)
                
                # Asignar TP1, TP2, TP3 a los niveles más cercanos
                if len(structural_levels) >= 1:
                    tp_levels['tp1'] = structural_levels[0]
                if len(structural_levels) >= 2:
                    tp_levels['tp2'] = structural_levels[1]
                if len(structural_levels) >= 3:
                    tp_levels['tp3'] = structural_levels[2]
                
                tp_levels['structural_levels'] = structural_levels[:5]  # Guardar hasta 5 niveles
            
            return tp_levels
            
        except Exception as e:
            print(f"   ❌ Error calculando TP estructurales: {e}")
            return {
                'tp1': None,
                'tp2': None, 
                'tp3': None,
                'structural_levels': []
            }
    
    def _find_equal_levels(self, levels: pd.Series, tolerance: float = 0.001) -> List[float]:
        """
        Encontrar niveles iguales o muy cercanos (equal highs/lows)
        
        Parámetros:
        -----------
        levels : pd.Series
            Serie de niveles de precio
        tolerance : float
            Tolerancia para considerar niveles iguales
        
        Retorna:
        --------
        Lista de niveles agrupados
        """
        if len(levels) == 0:
            return []
        
        levels = levels.sort_values()
        equal_levels = []
        
        i = 0
        while i < len(levels):
            current_level = levels.iloc[i]
            group = [current_level]
            
            # Buscar niveles cercanos
            j = i + 1
            while j < len(levels) and abs(levels.iloc[j] - current_level) <= tolerance:
                group.append(levels.iloc[j])
                j += 1
            
            # Calcular promedio del grupo
            avg_level = sum(group) / len(group)
            equal_levels.append(avg_level)
            
            i = j
        
        return equal_levels
    
    def calculate_risk_reward(self, signal: Dict, df: pd.DataFrame, df_1h: pd.DataFrame = None, df_4h: pd.DataFrame = None) -> Dict:
        """
        6. GESTIÓN DE LA OPERACIÓN
        
        Calcula Stop Loss, Take Profit y ratio riesgo/beneficio usando niveles estructurales.
        
        Parámetros:
        -----------
        signal : Dict
            Señal confirmada
        df : DataFrame
            Datos OHLC para cálculos
        df_1h : DataFrame
            Datos de 1H para análisis estructural
        df_4h : DataFrame
            Datos de 4H para análisis estructural
        
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
                    
            else:  # SHORT
                if 'ob_top' in signal:
                    stop_loss = signal['ob_top'] * 1.001  # Justo fuera del OB
                elif 'fvg_top' in signal:
                    stop_loss = signal['fvg_top'] * 1.001  # Justo fuera del FVG
                else:
                    stop_loss = entry_price * 1.005  # 0.5% por defecto
            
            # Calcular Take Profits estructurales
            tp_levels = self.calculate_structural_take_profits(df, entry_price, direction, df_1h, df_4h)
            
            # Si no hay niveles estructurales, usar R:R tradicional
            if tp_levels['tp1'] is None:
                risk = abs(entry_price - stop_loss)
                if direction == 'LONG':
                    tp_levels['tp1'] = entry_price + (risk * 1.0)  # R:R 1:1
                    tp_levels['tp2'] = entry_price + (risk * 2.0)  # R:R 1:2
                    tp_levels['tp3'] = entry_price + (risk * 3.0)  # R:R 1:3
                else:  # SHORT
                    tp_levels['tp1'] = entry_price - (risk * 1.0)  # R:R 1:1
                    tp_levels['tp2'] = entry_price - (risk * 2.0)  # R:R 1:2
                    tp_levels['tp3'] = entry_price - (risk * 3.0)  # R:R 1:3
            
            # Calcular R:R para TP1
            risk_amount = abs(entry_price - stop_loss)
            reward_amount = abs(tp_levels['tp1'] - entry_price)
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
            
            # Verificar si cumple R:R mínimo
            if risk_reward_ratio < self.risk_reward_min:
                print(f"   ⚠️ R:R {risk_reward_ratio:.2f} no cumple mínimo {self.risk_reward_min}")
                return None
            
            result = {
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': tp_levels['tp1'],
                'risk_reward_ratio': risk_reward_ratio,
                'risk_amount': risk_amount,
                'reward_amount': reward_amount,
                'tp_levels': tp_levels,
                'meets_minimum_rr': True
            }
            
            print(f"   ✅ Gestión de riesgo calculada:")
            print(f"      • Entrada: {entry_price:.5f}")
            print(f"      • Stop Loss: {stop_loss:.5f}")
            print(f"      • Take Profit: {tp_levels['tp1']:.5f}")
            print(f"      • R:R: 1:{risk_reward_ratio:.2f}")
            print(f"      • Cumple R:R mínimo: ✅")
            
            if tp_levels['structural_levels']:
                print(f"      • Niveles estructurales: {[f'{level:.5f}' for level in tp_levels['structural_levels'][:3]]}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Error calculando gestión de riesgo: {e}")
            return None
    
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
            pullback_signals = self.wait_for_pullback(df_5m, ob_data, fvg_data, context)
            
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
                risk_management = self.calculate_risk_reward(signal, df_5m, df_1h, df_4h)
                
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
