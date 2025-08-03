import backtrader as bt
import pandas as pd
import numpy as np
from smartmoneyconcepts.smc import smc

class ZonasMitigacionStrategy(bt.Strategy):
    """
    ESTRATEGIA: Zonas de Mitigación Multi-Timeframe
    
    Esta estrategia combina análisis de marcos superiores (HTF) con señales en 5 minutos:
    
    PREPARACIÓN HTF (1H):
    - Determina tendencia: máximos y mínimos crecientes/decrecientes
    - Marca zonas institucionales: Order Blocks, FVGs, Liquidity Zones
    - Confirma ruptura en 15M (MSS/BOS)
    
    SEÑALES LTF (5M):
    - Break of Structure (BOS)
    - Pullback a Order Block (61.8%-78.6% Fibonacci)
    - Entrada en Fair Value Gap
    - Reversión en Liquidity Grab
    
    GESTIÓN DE RIESGO:
    - Stop Loss: fuera del swing previo o rango de Order Block
    - Take Profit: 1:2 RR mínimo, idealmente en siguiente demanda/resistencia HTF
    """
    params = dict(
        swing_length=5,
        lookback=20,
        buffer_size=1000,
        # Parámetros para indicadores
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        # Parámetros para Fibonacci
        fib_min=0.618,
        fib_max=0.786,
        # Parámetros para Order Blocks
        ob_lookback=50,
        # Parámetros para FVG
        fvg_lookback=30,
        fvg_min_size=0.0001,
    )

    def __init__(self):
        # Datos OHLCV
        self.data_close = self.datas[0].close
        self.data_open = self.datas[0].open
        self.data_high = self.datas[0].high
        self.data_low = self.datas[0].low
        self.data_volume = self.datas[0].volume
        
        # Buffer para datos históricos
        self.df_buffer = []
        
        # Contadores de señales
        self.buy_signal_count = 0
        self.sell_signal_count = 0
        
        # Indicadores técnicos
        self.macd = bt.indicators.MACD(
            self.data_close,
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        self.rsi = bt.indicators.RSI(self.data_close, period=self.p.rsi_period)
        
        # Variables para análisis multi-timeframe
        self.trend_1h = 0  # Tendencia 1H
        self.trend_15m = 0  # Tendencia 15M
        
        # Zonas institucionales
        self.order_blocks_1h = []
        self.fair_value_gaps_1h = []
        self.liquidity_zones_1h = []
        
        # Variables para señales en 5M
        self.swing_highs_lows = None
        self.last_swing_high = None
        self.last_swing_low = None
        
        # Gestión de órdenes
        self.sl_order = None
        self.tp1_order = None
        self.tp2_order = None

    def next(self):
        # Mensaje inicial de la estrategia
        if len(self.data) == 1:
            print("🚀 INICIANDO ESTRATEGIA: Zonas de Mitigación Multi-Timeframe")
            print("=" * 70)
            print("📋 PREPARACIÓN HTF (1H):")
            print("   ✅ Determina tendencia: máximos y mínimos crecientes/decrecientes")
            print("   ✅ Marca zonas institucionales: Order Blocks, FVGs, Liquidity Zones")
            print("   ✅ Confirma ruptura en 15M (MSS/BOS)")
            print("")
            print("📋 SEÑALES LTF (5M):")
            print("   ✅ Break of Structure (BOS)")
            print("   ✅ Pullback a Order Block (61.8%-78.6% Fibonacci)")
            print("   ✅ Entrada en Fair Value Gap")
            print("   ✅ Reversión en Liquidity Grab")
            print("=" * 70)
        
        # Agregar la nueva barra al buffer
        self.df_buffer.append({
            'open': self.data_open[0],
            'high': self.data_high[0],
            'low': self.data_low[0],
            'close': self.data_close[0],
            'volume': self.data_volume[0],
            'datetime': self.datas[0].datetime.datetime(0)
        })
        
        # Salir si no hay suficientes velas para análisis
        if len(self.df_buffer) < 100:
            return
            
        if len(self.data) % 100 == 0:
            print(f"Procesando barra {len(self.data)} - Fecha: {self.datas[0].datetime.datetime(0)} - Precio: {self.data_close[0]}")
        
        # Obtener DataFrame
        df = self._get_df()
        if len(df) < self.p.lookback:
            return
            
        # Calcular swing highs/lows en 5M
        self.swing_highs_lows = smc.swing_highs_lows(df, swing_length=self.p.swing_length)
        
        # Verificar si los indicadores están listos
        if len(self.macd.macd) < 2 or len(self.rsi) < 1:
            return
        
        # --- PREPARACIÓN HTF (1H) ---
        self._update_htf_analysis()
        
        # --- SEÑALES LTF (5M) ---
        
        # 1. BREAK OF STRUCTURE (BOS)
        if self._is_bos_bullish():
            print("✅ BOS alcista detectado")
            
            if self._is_impulse_candle_bullish():
                print("✅ Vela de impulso alcista detectada")
                
                if self._is_macd_bullish_crossover():
                    print("✅ MACD crossover alcista detectado")
                    
                    if self._is_rsi_bullish():
                        print("✅ RSI > 50 confirmando momentum")
                        
                        # SEÑAL DE COMPRA - BOS
                        if not self.position:
                            self._execute_buy_signal("BOS")
        
        elif self._is_bos_bearish():
            print("✅ BOS bajista detectado")
            
            if self._is_impulse_candle_bearish():
                print("✅ Vela de impulso bajista detectada")
                
                if self._is_macd_bearish_crossover():
                    print("✅ MACD crossover bajista detectado")
                    
                    if self._is_rsi_bearish():
                        print("✅ RSI < 50 confirmando debilidad")
                        
                        # SEÑAL DE VENTA - BOS
                        if not self.position:
                            self._execute_sell_signal("BOS")
        
        # 2. PULLBACK A ORDER BLOCK
        if self._is_pullback_to_order_block_bullish():
            print("✅ Pullback a Order Block alcista detectado")
            
            if self._is_fibonacci_retracement_bullish():
                print("✅ Retroceso Fibonacci alcista detectado")
                
                if self._is_macd_bullish_crossover():
                    print("✅ MACD crossover alcista en pullback")
                    
                    if self._is_rsi_bullish():
                        print("✅ RSI > 50 confirmando momentum")
                        
                        # SEÑAL DE COMPRA - Pullback OB
                        if not self.position:
                            self._execute_buy_signal("Pullback OB")
        
        # 3. ENTRADA EN FAIR VALUE GAP
        if self._is_fvg_bullish_setup():
            print("✅ FVG alcista detectado")
            
            if self._is_fvg_filled():
                print("✅ FVG rellenado")
                
                if self._is_macd_bullish_crossover():
                    print("✅ MACD crossover cerca del FVG")
                    
                    if self._is_rsi_bullish():
                        print("✅ RSI > 50 confirmando momentum")
                        
                        # SEÑAL DE COMPRA - FVG
                        if not self.position:
                            self._execute_buy_signal("FVG")
        
        # 4. REVERSIÓN EN LIQUIDITY GRAB
        if self._is_liquidity_grab_bullish():
            print("✅ Liquidity Grab alcista detectado")
            
            if self._is_rejection_pattern_bullish():
                print("✅ Patrón de rechazo alcista detectado")
                
                if self._is_macd_bullish_crossover():
                    print("✅ MACD crossover después del rechazo")
                    
                    if self._is_rsi_bullish():
                        print("✅ RSI > 50 confirmando momentum")
                        
                        # SEÑAL DE COMPRA - Liquidity Grab
                        if not self.position:
                            self._execute_buy_signal("Liquidity Grab")
        self.fvg_15m = smc.fvg(df_15m)
        self.pdh_15m = df_15m['high'].iloc[-2] if len(df_15m) > 1 else None  # PDH: High de la vela anterior
        self.pdl_15m = df_15m['low'].iloc[-2] if len(df_15m) > 1 else None   # PDL: Low de la vela anterior

        # CHOCH y FVG en 1H
        self.choch_1h = smc.bos_choch(df_1h, swing_1h)
        self.fvg_1h = smc.fvg(df_1h)
        self.pdh_1h = df_1h['high'].iloc[-2] if len(df_1h) > 1 else None
        self.pdl_1h = df_1h['low'].iloc[-2] if len(df_1h) > 1 else None

        # CHOCH y FVG en 4H
        self.choch_4h = smc.bos_choch(df_4h, swing_4h)
        self.fvg_4h = smc.fvg(df_4h)
        self.pdh_4h = df_4h['high'].iloc[-2] if len(df_4h) > 1 else None
        self.pdl_4h = df_4h['low'].iloc[-2] if len(df_4h) > 1 else None
            
        # --- CALCULAR FVGs EN M5 PARA EJECUCIÓN ---
        # FVGs se calculan en M5 para ejecución precisa
        swing_5m = smc.swing_highs_lows(df_window, swing_length=self.p.swing_length)
        if isinstance(swing_5m, pd.Series):
            swing_5m = swing_5m.to_frame()
        self.fvg = smc.fvg(df_window)
        
        # Calcular tendencia estructural en 15M
        trend_15m = smc.trend_indicator(df_15m, swing_15m)
        trend_val_15m = 0
        if hasattr(trend_15m['Trend'], 'isnull'):
            if not trend_15m['Trend'].isnull().all():
                trend_val_15m = trend_15m['Trend'].iloc[-1]
        else:
            trend_val_15m = trend_15m['Trend'] if trend_15m['Trend'] is not None else 0
        # Calcular tendencia estructural en 1H
        trend_h1 = smc.trend_indicator(df_1h, swing_1h)
        trend_val_h1 = 0
        if hasattr(trend_h1['Trend'], 'isnull'):
            if not trend_h1['Trend'].isnull().all():
                trend_val_h1 = trend_h1['Trend'].iloc[-1]
        else:
            trend_val_h1 = trend_h1['Trend'] if trend_h1['Trend'] is not None else 0
        # Calcular tendencia estructural en 4H
        trend_h4 = smc.trend_indicator(df_4h, swing_4h)
        trend_val_h4 = 0
        if hasattr(trend_h4['Trend'], 'isnull'):
            if not trend_h4['Trend'].isnull().all():
                trend_val_h4 = trend_h4['Trend'].iloc[-1]
        else:
            trend_val_h4 = trend_h4['Trend'] if trend_h4['Trend'] is not None else 0
            
        # --- Detectar Zonas de Mitigación y Breaker Blocks en timeframes superiores ---
        self._update_mitigation_zones_multi_timeframe()
        self._update_breaker_blocks_multi_timeframe()
        
        # --- LÓGICA DE ENTRADA MITIGACIÓN ---
        # Buscar zonas relevantes en M15 y H1
        zonas_relevantes = []
        if hasattr(self, 'ob_15m') and self.ob_15m is not None and not getattr(self.ob_15m, 'empty', False):
            zonas_relevantes += [
                {'tipo': 'OB', 'high': row['Top'], 'low': row['Bottom'], 'timeframe': 'M15'}
                for idx, row in self.ob_15m.iterrows() if not pd.isna(row['OB'])
            ]
        if hasattr(self, 'ob_1h') and self.ob_1h is not None and not getattr(self.ob_1h, 'empty', False):
            zonas_relevantes += [
                {'tipo': 'OB', 'high': row['Top'], 'low': row['Bottom'], 'timeframe': 'H1'}
                for idx, row in self.ob_1h.iterrows() if not pd.isna(row['OB'])
            ]
        if hasattr(self, 'breaker_blocks') and isinstance(self.breaker_blocks, list) and len(self.breaker_blocks) > 0:
            zonas_relevantes += [
                {'tipo': 'Breaker', 'high': z['high'], 'low': z['low'], 'timeframe': z['timeframe']} for z in self.breaker_blocks
            ]
        if hasattr(self, 'mitigation_zones') and isinstance(self.mitigation_zones, list) and len(self.mitigation_zones) > 0:
            zonas_relevantes += [
                {'tipo': 'Mitigation', 'high': z['high'], 'low': z['low'], 'timeframe': z['timeframe']} for z in self.mitigation_zones
            ]

        precio_actual = float(self.data_close[0])
        zona_tocada = None
        for zona in zonas_relevantes:
            if zona is not None and 'low' in zona and 'high' in zona and zona['low'] <= precio_actual <= zona['high']:
                zona_tocada = zona
                break

        if zona_tocada:
            # Buscar gatillo en M5
            gatillo = False
            razon = ""
            # 1. Mitigation Block o Breaker Block en M5
            if hasattr(self, 'mitigation_zones') and any(z['timeframe'] == 'M5' for z in self.mitigation_zones):
                gatillo = True
                razon = "Mitigation Block en M5"
            if hasattr(self, 'breaker_blocks') and any(z['timeframe'] == 'M5' for z in self.breaker_blocks):
                gatillo = True
                razon = "Breaker Block en M5"
            # 2. Barrido de liquidez local (mínimo/máximo barrido en últimas 3 velas)
            if len(self.data_close) > 3:
                min_local = min(self.data_low.get(size=3))
                max_local = max(self.data_high.get(size=3))
                if float(self.data_low[0]) < min_local:
                    gatillo = True
                    razon = "Barrido de liquidez local (mínimo)"
                if float(self.data_high[0]) > max_local:
                    gatillo = True
                    razon = "Barrido de liquidez local (máximo)"
            # 3. Patrón de reversa en VWAP (ejemplo: cierre por encima/debajo de VWAP tras tocar zona)
            vwap_m5 = smc.vwap(self._get_df().iloc[-20:])
            df_m5 = self._get_df().iloc[-20:]
            patrones_vwap = [
                (self._vwap_bounce(df_m5, vwap_m5), "VWAP Bounce"),
                (self._vwap_break_retest(df_m5, vwap_m5), "VWAP Break Retest"),
                (self._vwap_reclaim(df_m5, vwap_m5), "VWAP Reclaim"),
                (self._vwap_extrema(df_m5, vwap_m5), "VWAP Extrema"),
            ]
            for detectado, nombre in patrones_vwap:
                if detectado:
                    gatillo = True
                    razon = nombre
                    break
            # 4. Micro FVG en M5
            if self.fvg is not None and len(self.fvg) > 0:
                ult_fvg = self.fvg.iloc[-1]
                if not pd.isna(ult_fvg['FVG']) and ult_fvg['low'] <= precio_actual <= ult_fvg['high']:
                    gatillo = True
                    razon = "Micro FVG en M5"

            # Si hay gatillo, ejecutar entrada
            if gatillo and not self.position:
                if zona_tocada['tipo'] in ['OB', 'Mitigation', 'Breaker']:
                    # Compra si la zona es alcista, venta si es bajista
                    if precio_actual <= zona_tocada['low'] + (zona_tocada['high'] - zona_tocada['low'])/2:
                        # Compra
                        sl = zona_tocada['low'] - (zona_tocada['high'] - zona_tocada['low']) * 0.2
                        tp = self._get_tp1_buy(precio_actual)
                        size = self.broker.get_cash() / precio_actual
                        self.buy(size=size)
                        self.sl_order = self.sell(exectype=bt.Order.Stop, price=sl, size=size)
                        self.tp1_order = self.sell(exectype=bt.Order.Limit, price=tp, size=size)
                        print(f"Compra por mitigación en zona {zona_tocada['tipo']} {zona_tocada['timeframe']} | SL: {sl} | TP: {tp}")
                    else:
                        # Venta
                        sl = zona_tocada['high'] + (zona_tocada['high'] - zona_tocada['low']) * 0.2
                        tp = self._get_tp1_sell(precio_actual)
                        size = self.broker.get_cash() / precio_actual
                        self.sell(size=size)
                        self.sl_order = self.buy(exectype=bt.Order.Stop, price=sl, size=size)
                        self.tp1_order = self.buy(exectype=bt.Order.Limit, price=tp, size=size)
                        print(f"Venta por mitigación en zona {zona_tocada['tipo']} {zona_tocada['timeframe']} | SL: {sl} | TP: {tp}")

    def _get_df(self):
        # Construye un DataFrame OHLCV desde los datos de Backtrader
        data = {
            'open': np.array(self.data_open.get(size=len(self.data_open))),
            'high': np.array(self.data_high.get(size=len(self.data_high))),
            'low': np.array(self.data_low.get(size=len(self.data_low))),
            'close': np.array(self.data_close.get(size=len(self.data_close))),
            'volume': np.array(self.datas[0].volume.get(size=len(self.datas[0].volume))),
        }
        # Obtener fechas reales usando el método datetime de Backtrader
        index = pd.Index([self.datas[0].datetime.datetime(i) for i in range(len(self.data_close))])
        df = pd.DataFrame(data, index=index)
        return df

    def _get_last(self, serie):
        # Devuelve el último valor de una Serie, DataFrame o ndarray
        if hasattr(serie, 'iloc'):
            return serie.iloc[-1]
        elif hasattr(serie, '__getitem__'):
            return serie[-1]
        else:
            return serie

    def _update_mitigation_zones_multi_timeframe(self):
        """Actualiza las zonas de mitigación usando Order Blocks de múltiples timeframes"""
        current_price = float(self.data_close[0])
        self.mitigation_zones = []
        
        # Detectar FVGs mitigados en M5
        if self.fvg is not None:
            for i in range(len(self.fvg)):
                if not pd.isna(self.fvg.iloc[i]['FVG']):
                    fvg_val = self.fvg.iloc[i]['FVG']
                    fvg_high = self.fvg.iloc[i]['high']
                    fvg_low = self.fvg.iloc[i]['low']
                    
                    # Si el precio actual está dentro del FVG, está mitigado
                    if fvg_low <= current_price <= fvg_high:
                        self.mitigation_zones.append({
                            'type': 'FVG',
                            'direction': 'bullish' if fvg_val == 1 else 'bearish',
                            'high': fvg_high,
                            'low': fvg_low,
                            'index': i,
                            'timeframe': 'M5'
                        })
        
        # Detectar OBs mitigados en M15
        if hasattr(self, 'ob_15m') and self.ob_15m is not None:
            for i in range(len(self.ob_15m)):
                if not pd.isna(self.ob_15m.iloc[i]['OB']):
                    ob_val = self.ob_15m.iloc[i]['OB']
                    ob_high = self.ob_15m.iloc[i]['Top']
                    ob_low = self.ob_15m.iloc[i]['Bottom']
                    
                    # Si el precio actual está dentro del OB, está mitigado
                    if ob_low <= current_price <= ob_high:
                        self.mitigation_zones.append({
                            'type': 'OB',
                            'direction': 'bullish' if ob_val == 1 else 'bearish',
                            'high': ob_high,
                            'low': ob_low,
                            'index': i,
                            'timeframe': 'M15'
                        })
        
        # Detectar OBs mitigados en 1H
        if hasattr(self, 'ob_1h') and self.ob_1h is not None:
            for i in range(len(self.ob_1h)):
                if not pd.isna(self.ob_1h.iloc[i]['OB']):
                    ob_val = self.ob_1h.iloc[i]['OB']
                    ob_high = self.ob_1h.iloc[i]['Top']
                    ob_low = self.ob_1h.iloc[i]['Bottom']
                    
                    # Si el precio actual está dentro del OB, está mitigado
                    if ob_low <= current_price <= ob_high:
                        self.mitigation_zones.append({
                            'type': 'OB',
                            'direction': 'bullish' if ob_val == 1 else 'bearish',
                            'high': ob_high,
                            'low': ob_low,
                            'index': i,
                            'timeframe': '1H'
                        })
        
        # Detectar OBs mitigados en 4H
        if hasattr(self, 'ob_4h') and self.ob_4h is not None:
            for i in range(len(self.ob_4h)):
                if not pd.isna(self.ob_4h.iloc[i]['OB']):
                    ob_val = self.ob_4h.iloc[i]['OB']
                    ob_high = self.ob_4h.iloc[i]['Top']
                    ob_low = self.ob_4h.iloc[i]['Bottom']
                    
                    # Si el precio actual está dentro del OB, está mitigado
                    if ob_low <= current_price <= ob_high:
                        self.mitigation_zones.append({
                            'type': 'OB',
                            'direction': 'bullish' if ob_val == 1 else 'bearish',
                            'high': ob_high,
                            'low': ob_low,
                            'index': i,
                            'timeframe': '4H'
                        })

    def _update_breaker_blocks_multi_timeframe(self):
        """Actualiza los breaker blocks usando Order Blocks de múltiples timeframes"""
        self.breaker_blocks = []
        
        # Breaker blocks en M15
        if hasattr(self, 'ob_15m') and self.ob_15m is not None:
            # Resamplear el último FVG de 5M para obtener el swing más reciente
            df_5m_last = pd.DataFrame([self.df_5m_cache[-1][1]])
            df_5m_last.index = [self.df_5m_cache[-1][0]]
            df_5m_last.index = pd.to_datetime(df_5m_last.index)

            swing_15m = smc.swing_highs_lows(df_5m_last.resample('15min').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna(), swing_length=self.p.swing_length)
            
            if isinstance(swing_15m, pd.Series):
                swing_15m = swing_15m.to_frame()
            
            for i in range(len(self.ob_15m)):
                if not pd.isna(self.ob_15m.iloc[i]['OB']):
                    ob_val = self.ob_15m.iloc[i]['OB']
                    ob_high = self.ob_15m.iloc[i]['Top']
                    ob_low = self.ob_15m.iloc[i]['Bottom']
                    ob_index = self.ob_15m.index[i]
                    
                    # Buscar si este OB rompió un swing previo
                    for j in range(len(swing_15m)):
                        swing_type = swing_15m.iloc[j]['HighLow']
                        swing_level = swing_15m.iloc[j]['Level']
                        swing_index = swing_15m.index[j]
                        
                        # Si el OB está después del swing y lo rompe
                        if swing_index < ob_index:
                            if (ob_val == 1 and swing_type == 'high' and ob_high > swing_level) or \
                               (ob_val == -1 and swing_type == 'low' and ob_low < swing_level):
                                self.breaker_blocks.append({
                                    'timeframe': 'M15',
                                    'direction': 'bullish' if ob_val == 1 else 'bearish',
                                    'high': ob_high,
                                    'low': ob_low,
                                    'index': i,
                                    'broken_swing': swing_level
                                })
        
        # Breaker blocks en 1H
        if hasattr(self, 'ob_1h') and self.ob_1h is not None:
            # Resamplear el último FVG de 5M para obtener el swing más reciente
            df_5m_last = pd.DataFrame([self.df_5m_cache[-1][1]])
            df_5m_last.index = [self.df_5m_cache[-1][0]]
            df_5m_last.index = pd.to_datetime(df_5m_last.index)

            swing_1h = smc.swing_highs_lows(df_5m_last.resample('1h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna(), swing_length=self.p.swing_length)
            
            if isinstance(swing_1h, pd.Series):
                swing_1h = swing_1h.to_frame()
            
            for i in range(len(self.ob_1h)):
                if not pd.isna(self.ob_1h.iloc[i]['OB']):
                    ob_val = self.ob_1h.iloc[i]['OB']
                    ob_high = self.ob_1h.iloc[i]['Top']
                    ob_low = self.ob_1h.iloc[i]['Bottom']
                    ob_index = self.ob_1h.index[i]
                    
                    # Buscar si este OB rompió un swing previo
                    for j in range(len(swing_1h)):
                        swing_type = swing_1h.iloc[j]['HighLow']
                        swing_level = swing_1h.iloc[j]['Level']
                        swing_index = swing_1h.index[j]
                        
                        # Si el OB está después del swing y lo rompe
                        if swing_index < ob_index:
                            if (ob_val == 1 and swing_type == 'high' and ob_high > swing_level) or \
                               (ob_val == -1 and swing_type == 'low' and ob_low < swing_level):
                                self.breaker_blocks.append({
                                    'timeframe': '1H',
                                    'direction': 'bullish' if ob_val == 1 else 'bearish',
                                    'high': ob_high,
                                    'low': ob_low,
                                    'index': i,
                                    'broken_swing': swing_level
                                })
        
        # Breaker blocks en 4H
        if hasattr(self, 'ob_4h') and self.ob_4h is not None:
            # Resamplear el último FVG de 5M para obtener el swing más reciente
            df_5m_last = pd.DataFrame([self.df_5m_cache[-1][1]])
            df_5m_last.index = [self.df_5m_cache[-1][0]]
            df_5m_last.index = pd.to_datetime(df_5m_last.index)

            swing_4h = smc.swing_highs_lows(df_5m_last.resample('4h').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna(), swing_length=self.p.swing_length)
            
            if isinstance(swing_4h, pd.Series):
                swing_4h = swing_4h.to_frame()
            
            for i in range(len(self.ob_4h)):
                if not pd.isna(self.ob_4h.iloc[i]['OB']):
                    ob_val = self.ob_4h.iloc[i]['OB']
                    ob_high = self.ob_4h.iloc[i]['Top']
                    ob_low = self.ob_4h.iloc[i]['Bottom']
                    ob_index = self.ob_4h.index[i]
                    
                    # Buscar si este OB rompió un swing previo
                    for j in range(len(swing_4h)):
                        swing_type = swing_4h.iloc[j]['HighLow']
                        swing_level = swing_4h.iloc[j]['Level']
                        swing_index = swing_4h.index[j]
                        
                        # Si el OB está después del swing y lo rompe
                        if swing_index < ob_index:
                            if (ob_val == 1 and swing_type == 'high' and ob_high > swing_level) or \
                               (ob_val == -1 and swing_type == 'low' and ob_low < swing_level):
                                self.breaker_blocks.append({
                                    'timeframe': '4H',
                                    'direction': 'bullish' if ob_val == 1 else 'bearish',
                                    'high': ob_high,
                                    'low': ob_low,
                                    'index': i,
                                    'broken_swing': swing_level
                                })

    def _is_in_bullish_mitigation_zone(self):
        """Verifica si el precio está en una zona de mitigación alcista"""
        current_price = float(self.data_close[0])
        for zone in self.mitigation_zones:
            if zone['direction'] == 'bullish' and zone['low'] <= current_price <= zone['high']:
                return True
        return False

    def _is_in_bearish_mitigation_zone(self):
        """Verifica si el precio está en una zona de mitigación bajista"""
        current_price = float(self.data_close[0])
        for zone in self.mitigation_zones:
            if zone['direction'] == 'bearish' and zone['low'] <= current_price <= zone['high']:
                return True
        return False

    def _is_in_bullish_breaker_block(self):
        """Verifica si el precio está en un breaker block alcista"""
        current_price = float(self.data_close[0])
        for block in self.breaker_blocks:
            if block['direction'] == 'bullish' and block['low'] <= current_price <= block['high']:
                return True
        return False

    def _is_in_bearish_breaker_block(self):
        """Verifica si el precio está en un breaker block bajista"""
        current_price = float(self.data_close[0])
        for block in self.breaker_blocks:
            if block['direction'] == 'bearish' and block['low'] <= current_price <= block['high']:
                return True
        return False

    def _is_bullish_confirmation(self):
        # Pin bar o engulfing alcista
        o, h, l, c = self.data_open[0], self.data_high[0], self.data_low[0], self.data_close[0]
        body = abs(c - o)
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        if body < (h - l) * 0.3 and lower_wick > upper_wick * 1.5:
            return True
        # Engulfing alcista
        if len(self.data_close) > 1:
            prev_o, prev_c = self.data_open[-1], self.data_close[-1]
            if c > o and prev_c < prev_o and c > prev_o:
                return True
        return False

    def _is_bearish_confirmation(self):
        # Pin bar o engulfing bajista
        o, h, l, c = self.data_open[0], self.data_high[0], self.data_low[0], self.data_close[0]
        body = abs(c - o)
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        if body < (h - l) * 0.3 and upper_wick > lower_wick * 1.5:
            return True
        # Engulfing bajista
        if len(self.data_close) > 1:
            prev_o, prev_c = self.data_open[-1], self.data_close[-1]
            if c < o and prev_c > prev_o and c < prev_o:
                return True
        return False

    def _is_high_volume(self, window=20):
        # Calcula si el volumen actual es mayor al promedio de las últimas N velas
        if len(self.data_close) < window + 1:
            return False
        vol_array = np.array(self.datas[0].volume.get(size=len(self.datas[0].volume)))
        avg_vol = np.mean(vol_array[-window-1:-1])
        return vol_array[-1] > avg_vol

    def _get_sl_buy(self):
        # SL para compras: buscar el OB alcista más reciente en timeframes superiores
        current_price = float(self.data_close[0])
        best_sl = float(self.data_low[0])  # SL por defecto
        
        # Buscar en 4H primero (más importante)
        if hasattr(self, 'ob_4h') and self.ob_4h is not None and not getattr(self.ob_4h, 'empty', False):
            ob_bullish_4h = self.ob_4h[self.ob_4h['OB'] == 1]
            if hasattr(ob_bullish_4h, 'empty') and not ob_bullish_4h.empty:
                for i in range(len(ob_bullish_4h)):
                    ob_low = ob_bullish_4h.iloc[i]['Bottom'] if hasattr(ob_bullish_4h, 'iloc') else ob_bullish_4h[i]['Bottom']
                    if ob_low < current_price and ob_low > best_sl:
                        best_sl = ob_low
        
        # Buscar en 1H
        if hasattr(self, 'ob_1h') and self.ob_1h is not None and not getattr(self.ob_1h, 'empty', False):
            ob_bullish_1h = self.ob_1h[self.ob_1h['OB'] == 1]
            if hasattr(ob_bullish_1h, 'empty') and not ob_bullish_1h.empty:
                for i in range(len(ob_bullish_1h)):
                    ob_low = ob_bullish_1h.iloc[i]['Bottom'] if hasattr(ob_bullish_1h, 'iloc') else ob_bullish_1h[i]['Bottom']
                    if ob_low < current_price and ob_low > best_sl:
                        best_sl = ob_low
        
        # Buscar en M15
        if hasattr(self, 'ob_15m') and self.ob_15m is not None and not getattr(self.ob_15m, 'empty', False):
            ob_bullish_15m = self.ob_15m[self.ob_15m['OB'] == 1]
            if hasattr(ob_bullish_15m, 'empty') and not ob_bullish_15m.empty:
                for i in range(len(ob_bullish_15m)):
                    ob_low = ob_bullish_15m.iloc[i]['Bottom'] if hasattr(ob_bullish_15m, 'iloc') else ob_bullish_15m[i]['Bottom']
                    if ob_low < current_price and ob_low > best_sl:
                        best_sl = ob_low
        
        return best_sl

    def _get_sl_sell(self):
        # SL para ventas: buscar el OB bajista más reciente en timeframes superiores
        current_price = float(self.data_close[0])
        best_sl = float(self.data_high[0])  # SL por defecto
        
        # Buscar en 4H primero (más importante)
        if hasattr(self, 'ob_4h') and self.ob_4h is not None and not getattr(self.ob_4h, 'empty', False):
            ob_bearish_4h = self.ob_4h[self.ob_4h['OB'] == -1]
            if hasattr(ob_bearish_4h, 'empty') and not ob_bearish_4h.empty:
                for i in range(len(ob_bearish_4h)):
                    ob_high = ob_bearish_4h.iloc[i]['Top'] if hasattr(ob_bearish_4h, 'iloc') else ob_bearish_4h[i]['Top']
                    if ob_high > current_price and ob_high < best_sl:
                        best_sl = ob_high
        
        # Buscar en 1H
        if hasattr(self, 'ob_1h') and self.ob_1h is not None and not getattr(self.ob_1h, 'empty', False):
            ob_bearish_1h = self.ob_1h[self.ob_1h['OB'] == -1]
            if hasattr(ob_bearish_1h, 'empty') and not ob_bearish_1h.empty:
                for i in range(len(ob_bearish_1h)):
                    ob_high = ob_bearish_1h.iloc[i]['Top'] if hasattr(ob_bearish_1h, 'iloc') else ob_bearish_1h[i]['Top']
                    if ob_high > current_price and ob_high < best_sl:
                        best_sl = ob_high
        
        # Buscar en M15
        if hasattr(self, 'ob_15m') and self.ob_15m is not None and not getattr(self.ob_15m, 'empty', False):
            ob_bearish_15m = self.ob_15m[self.ob_15m['OB'] == -1]
            if hasattr(ob_bearish_15m, 'empty') and not ob_bearish_15m.empty:
                for i in range(len(ob_bearish_15m)):
                    ob_high = ob_bearish_15m.iloc[i]['Top'] if hasattr(ob_bearish_15m, 'iloc') else ob_bearish_15m[i]['Top']
                    if ob_high > current_price and ob_high < best_sl:
                        best_sl = ob_high
        
        return best_sl

    def _get_tp1_buy(self, entry_price):
        # TP1 compra: cierre del FVG alcista más cercano o punto medio con swing high
        if self.fvg is not None:
            fvg_bullish = self.fvg[self.fvg['FVG'] == 1]
            if not fvg_bullish.empty:
                return fvg_bullish['close'].iloc[-1]
        # Si no hay FVG, usar punto medio entre entrada y swing high
        if self.swing_highs_lows is not None:
            swing_highs = self.swing_highs_lows[self.swing_highs_lows['type'] == 'high']
            if not swing_highs.empty:
                swing_high = swing_highs['high'].iloc[-1]
                return (entry_price + swing_high) / 2
        return entry_price * 1.01

    def _get_tp2_buy(self):
        # TP2 compra: siguiente swing high relevante
        if self.swing_highs_lows is not None:
            swing_highs = self.swing_highs_lows[self.swing_highs_lows['type'] == 'high']
            if not swing_highs.empty:
                return swing_highs['high'].iloc[-1]
        return float(self.data_high[0])

    def _get_tp1_sell(self, entry_price):
        # TP1 venta: cierre del FVG bajista más cercano o punto medio con swing low
        if self.fvg is not None:
            fvg_bearish = self.fvg[self.fvg['FVG'] == -1]
            if not fvg_bearish.empty:
                return fvg_bearish['close'].iloc[-1]
        # Si no hay FVG, usar punto medio entre entrada y swing low
        if self.swing_highs_lows is not None:
            swing_lows = self.swing_highs_lows[self.swing_highs_lows['type'] == 'low']
            if not swing_lows.empty:
                swing_low = swing_lows['low'].iloc[-1]
                return (entry_price + swing_low) / 2
        return entry_price * 0.99

    def _get_tp2_sell(self):
        # TP2 venta: siguiente swing low relevante
        if self.swing_highs_lows is not None:
            swing_lows = self.swing_highs_lows[self.swing_highs_lows['type'] == 'low']
            if not swing_lows.empty:
                return swing_lows['low'].iloc[-1]
        return float(self.data_low[0])

    def _vwap_bounce(self, df, vwap):
        """
        Detecta si el precio cierra cerca del VWAP (rebote simple).
        Retorna True si el cierre de la última vela está a menos de 0.0005 del VWAP.
        """
        if len(df) == 0 or len(vwap) == 0:
            return False
        close = df['close'].iloc[-1]
        vwap_val = vwap.iloc[-1]
        return abs(close - vwap_val) < 0.0005

    def _vwap_break_retest(self, df, vwap):
        """
        Detecta si el precio rompió el VWAP y luego lo retesteó.
        Retorna True si en la penúltima vela el precio estaba de un lado del VWAP y en la última lo retestea (cerca del VWAP).
        """
        if len(df) < 2 or len(vwap) < 2:
            return False
        close_prev = df['close'].iloc[-2]
        close_now = df['close'].iloc[-1]
        vwap_prev = vwap.iloc[-2]
        vwap_now = vwap.iloc[-1]
        # Rompió de abajo hacia arriba y retestea desde arriba
        if close_prev < vwap_prev and close_now > vwap_now and abs(close_now - vwap_now) < 0.0005:
            return True
        # Rompió de arriba hacia abajo y retestea desde abajo
        if close_prev > vwap_prev and close_now < vwap_now and abs(close_now - vwap_now) < 0.0005:
            return True
        return False

    def _vwap_reclaim(self, df, vwap):
        """
        Detecta si el precio ha recuperado el VWAP después de estar por debajo (o por encima) durante varias velas.
        Retorna True si en las últimas 3 velas el precio estuvo por debajo (o por encima) y ahora cruza el VWAP.
        """
        if len(df) < 4 or len(vwap) < 4:
            return False
        closes = df['close'].iloc[-4:]
        vwaps = vwap.iloc[-4:]
        # Recuperación alcista: 3 cierres bajo VWAP y el último cierra arriba
        if all(closes[:-1] < vwaps[:-1]) and closes.iloc[-1] > vwaps.iloc[-1]:
            return True
        # Recuperación bajista: 3 cierres sobre VWAP y el último cierra abajo
        if all(closes[:-1] > vwaps[:-1]) and closes.iloc[-1] < vwaps.iloc[-1]:
            return True
        return False

    def _vwap_extrema(self, df, vwap):
        """
        Detecta si el precio se aleja de forma extrema del VWAP (sobrecompra/sobreventa respecto al VWAP).
        Retorna True si el cierre está a más de 2 desviaciones estándar del VWAP en las últimas 20 velas.
        """
        if len(df) < 20 or len(vwap) < 20:
            return False
        closes = df['close'].iloc[-20:]
        vwaps = vwap.iloc[-20:]
        desv = (closes - vwaps).std()
        diff = abs(closes.iloc[-1] - vwaps.iloc[-1])
        return diff > 2 * desv

    def notify_order(self, order):
        # Cancelar el SL y TPs si se cierra la posición
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if self.sl_order is not None:
                self.cancel(self.sl_order)
                self.sl_order = None
            if self.tp1_order is not None:
                self.cancel(self.tp1_order)
                self.tp1_order = None
            if self.tp2_order is not None:
                self.cancel(self.tp2_order)
                self.tp2_order = None 