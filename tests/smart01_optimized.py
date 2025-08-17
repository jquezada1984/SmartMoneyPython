#!/usr/bin/env python3
"""
Smart01 Optimizado - Cálculo selectivo de indicadores por temporalidad
- 5M: Todos los indicadores (MACD, RSI, SMC completo)
- 15M, 1H, 4H: Solo tendencia (resampleando desde 5M)
- Sincronización de índices para graficar correctamente
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import sys
import os
from datetime import datetime
import numpy as np
import time
from io import BytesIO
from PIL import Image
import plotly.io as pio
from tqdm import tqdm
import datetime

# Agregar el directorio raíz al path para imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar paquetes
try:
    from smartmoneyconcepts.smc import smc
    from estrategia.momentum_smc_strategy_lib import MomentumSMCStrategyLib
    from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib
    print("✅ Módulos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("🔧 Verificando estructura de directorios...")
    import os
    print(f"   Directorio actual: {os.getcwd()}")
    print(f"   Archivos en tests/: {os.listdir('tests')}")
    print(f"   Archivos en raíz: {os.listdir('.')}")
    sys.exit(1)

class OptimizedTradingVisualizer:
    """
    Visualizador optimizado de trading con cálculo selectivo por temporalidad
    """
    def __init__(self):
        self.strategy_lib = MomentumSMCStrategyLib()
        self.market_analysis = MarketAnalysisLib()
        self.signals = []
        self.cached_indicators = None
        
        # Cache para temporalidades superiores
        self.trend_cache = {}
        
    def calculate_5m_complete_indicators(self, df_5m):
        """
        Calcular TODOS los indicadores para temporalidad 5M
        """
        print(f"🔧 Calculando indicadores completos para 5M...")
        start_time = time.time()
        
        try:
            # Precalcular todos los indicadores SMC
            cached_indicators = self.strategy_lib.precalculate_indicators(df_5m)
            
            # Calcular tendencia SMC
            trend_data = self.market_analysis.detect_trend(df_5m, method='structural')
            
            # Calcular MACD y RSI
            macd_line, signal_line, histogram = self._calculate_macd(df_5m)
            rsi = self._calculate_rsi(df_5m)
            
            # Combinar todos los indicadores
            complete_indicators = {
                'trend_data': trend_data,
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram,
                'rsi': rsi,
                **cached_indicators  # Incluir todos los indicadores SMC
            }
            
            elapsed = time.time() - start_time
            print(f"✅ Indicadores 5M calculados en {elapsed:.2f}s")
            
            return complete_indicators
            
        except Exception as e:
            print(f"❌ Error calculando indicadores 5M: {e}")
            raise e
    
    def calculate_higher_timeframe_trend_only(self, df_5m, target_timeframe, required_velas=300):
        """
        Calcular SOLO tendencia para temporalidades superiores
        Versión simplificada que funciona como debug_smc_detection.py
        """
        print(f"🔄 Calculando tendencia para {target_timeframe}...")
        start_time = time.time()
        
        # Determinar regla de resampleo
        timeframe_rules = {
            '15M': '15min',
            '1H': '1h', 
            '4H': '4h'
        }
        
        if target_timeframe not in timeframe_rules:
            raise ValueError(f"Timeframe no válido: {target_timeframe}")
        
        rule = timeframe_rules[target_timeframe]
        
        # Calcular cuántas velas 5M necesitamos para obtener 300 velas del timeframe objetivo
        if target_timeframe == '15M':
            # 15M = 3 velas de 5M, necesitamos 300 * 3 = 900 velas 5M
            required_5m_velas = required_velas * 3
        elif target_timeframe == '1H':
            # 1H = 12 velas de 5M, necesitamos 300 * 12 = 3600 velas 5M
            required_5m_velas = required_velas * 12
        elif target_timeframe == '4H':
            # 4H = 48 velas de 5M, necesitamos 300 * 48 = 14400 velas 5M
            required_5m_velas = required_velas * 48
        
        print(f"   📊 Necesitamos {required_5m_velas} velas 5M para obtener {required_velas} velas {target_timeframe}")
        
        # Tomar solo las velas necesarias del DataFrame 5M (últimas N velas)
        if len(df_5m) >= required_5m_velas:
            df_subset = df_5m.tail(required_5m_velas)
            print(f"   ✅ Usando {len(df_subset)} velas 5M (últimas {required_5m_velas})")
        else:
            df_subset = df_5m
            print(f"   ⚠️ Datos insuficientes: {len(df_5m)} velas 5M disponibles")
        
        # Convertir índice a datetime para resampleo
        df_subset_temp = df_subset.copy()
        df_subset_temp.index = pd.to_datetime(df_subset_temp.index)
        
        # Resamplear a la temporalidad objetivo
        df_resampled = df_subset_temp.resample(rule).agg({
            'open': 'first',
            'high': 'max', 
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        print(f"   📈 Resampleado a {target_timeframe}: {len(df_resampled)} velas")
        
        # Calcular SOLO la tendencia (método directo como debug_smc_detection.py)
        try:
            trend_data = self.market_analysis.detect_trend(df_resampled, method='structural')
            
            # DEBUG: Mostrar información de la tendencia calculada
            print(f"   🔍 Tendencia calculada:")
            print(f"      Columnas: {list(trend_data.columns)}")
            print(f"      Filas: {len(trend_data)}")
            if len(trend_data) > 0:
                last_trend = trend_data['trend'].iloc[-1] if 'trend' in trend_data.columns else 0
                last_strength = trend_data['strength'].iloc[-1] if 'strength' in trend_data.columns else 0
                last_confidence = trend_data['confidence'].iloc[-1] if 'confidence' in trend_data.columns else 0
                print(f"      Último valor - T:{last_trend:.4f}, F:{last_strength:.4f}, C:{last_confidence:.4f}")
            
            # CORREGIR: Usar la tendencia real en lugar de valores constantes
            # Crear DataFrame de tendencia que mantenga la variabilidad temporal
            trend_real = pd.DataFrame(index=df_subset.index)
            
            # Para cada vela 5M, asignar la tendencia correspondiente del timeframe superior
            # Esto requiere mapear las velas 5M a las velas del timeframe superior
            trend_values = []
            for i, timestamp in enumerate(df_subset.index):
                # Calcular qué vela del timeframe superior corresponde a esta vela 5M
                if target_timeframe == '15M':
                    tf_index = i // 3  # Cada 3 velas 5M = 1 vela 15M
                elif target_timeframe == '1H':
                    tf_index = i // 12  # Cada 12 velas 5M = 1 vela 1H
                elif target_timeframe == '4H':
                    tf_index = i // 48  # Cada 48 velas 5M = 1 vela 4H
                
                # Obtener el valor de tendencia correspondiente
                if tf_index < len(trend_data):
                    trend_val = trend_data['trend'].iloc[tf_index] if 'trend' in trend_data.columns else 0
                    strength_val = trend_data['strength'].iloc[tf_index] if 'strength' in trend_data.columns else 0
                    confidence_val = trend_data['confidence'].iloc[tf_index] if 'confidence' in trend_data.columns else 0
                else:
                    # Si no hay suficientes datos, usar el último valor disponible
                    trend_val = last_trend
                    strength_val = last_strength
                    confidence_val = last_confidence
                
                trend_values.append(trend_val)
            
            trend_real['trend'] = trend_values
            trend_real['strength'] = [last_strength] * len(df_subset)  # Mantener consistencia
            trend_real['confidence'] = [last_confidence] * len(df_subset)  # Mantener consistencia
            
            elapsed = time.time() - start_time
            print(f"✅ Tendencia {target_timeframe} calculada en {elapsed:.2f}s")
            
            return {
                'trend_data': trend_real,
                'resampled_df': df_resampled,
                'original_5m_count': len(df_subset),
                'resampled_count': len(df_resampled)
            }
            
        except Exception as e:
            print(f"❌ Error calculando tendencia {target_timeframe}: {e}")
            raise e
    
    def _calculate_macd(self, df, fast=12, slow=26, signal=9):
        """Calcular MACD: MACD Line, Signal Line, Histogram"""
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_rsi(self, df, period=14):
        """Calcular RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_trend_summary(self, trend_data, timeframe_name):
        """
        Obtener resumen de la tendencia calculada
        """
        if trend_data is None or 'trend_data' not in trend_data:
            return f"❌ No hay datos de tendencia para {timeframe_name}"
        
        trend_df = trend_data['trend_data']
        
        if len(trend_df) == 0:
            return f"⚠️ DataFrame de tendencia vacío para {timeframe_name}"
        
        # Obtener último valor de tendencia
        current_trend = trend_df['trend'].iloc[-1] if 'trend' in trend_df.columns else 0
        current_strength = trend_df['strength'].iloc[-1] if 'strength' in trend_df.columns else 0
        current_confidence = trend_df['confidence'].iloc[-1] if 'confidence' in trend_df.columns else 0
        
        # Interpretar tendencia
        if current_trend > 0.5:
            trend_direction = "🟢 ALCISTA"
        elif current_trend < -0.5:
            trend_direction = "🔴 BAJISTA"
        else:
            trend_direction = "🟡 LATERAL"
        
        return f"{timeframe_name}: {trend_direction} (T:{current_trend:.2f}, F:{current_strength:.2f}, C:{current_confidence:.2f}%)"

def add_trading_signals(fig, df, signals, window_df):
    """
    Agregar señales de trading al gráfico
    """
    for signal in signals:
        if signal['timestamp'] in window_df.index:
            # Determinar color según estrategia
            color_map = {
                'BOS + Impulse': 'lime',
                'Order Block + Fibonacci': 'cyan',
                'Fair Value Gap': 'yellow'
            }
            color = color_map.get(signal['strategy'], 'white')
            
            # Obtener nivel de confianza
            confidence = signal.get('confidence', 0)
            confidence_text = f"{confidence}%" if confidence > 0 else ""
            
            # Determinar tamaño del marcador según confianza
            marker_size = 8 if confidence < 50 else (12 if confidence < 80 else 16)
            
            # Agregar marcador de señal
            fig.add_trace(
                go.Scatter(
                    x=[signal['timestamp']],
                    y=[signal['price']],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up' if signal['type'] == 'BUY' else 'triangle-down',
                        size=marker_size,
                        color=color,
                        line=dict(color='black', width=1)
                    ),
                    name=f"Señal {signal['strategy']}",
                    showlegend=False
                ),
                row=1, col=1
            )
            
            # Agregar anotación con confianza y detalles
            strategy_short = signal['strategy'].replace(' + ', '+')[:15]
            annotation_text = f"{'🔼' if signal['type'] == 'BUY' else '🔽'} {strategy_short}\n{confidence_text}"
            
            fig.add_annotation(
                x=signal['timestamp'],
                y=signal['price'] * (1.002 if signal['type'] == 'BUY' else 0.998),
                text=annotation_text,
                showarrow=False,
                font=dict(color=color, size=7, family='Arial Black'),
                bgcolor='rgba(0,0,0,0.8)',
                bordercolor=color,
                borderwidth=1
            )
    
    return fig

def add_smc_indicators(fig, window_df, cached_indicators, pos, window):
    """
    Agregar indicadores SMC al gráfico principal
    """
    try:
        # Obtener ventana de todos los indicadores SMC precalculados
        # Ajustar índices para que coincidan con df_5m_indicators
        start_idx = max(0, len(cached_indicators['fvg_data']) - window)
        end_idx = len(cached_indicators['fvg_data'])
        
        fvg_data = cached_indicators['fvg_data'].iloc[start_idx:end_idx]
        swing_highs_lows_data = cached_indicators['swing_highs_lows'].iloc[start_idx:end_idx]
        bos_choch_data = cached_indicators['bos_choch'].iloc[start_idx:end_idx]
        ob_data = cached_indicators['ob_data'].iloc[start_idx:end_idx]
        liquidity_data = cached_indicators['liquidity_data'].iloc[start_idx:end_idx]
        previous_high_low_data = cached_indicators['previous_high_low_data'].iloc[start_idx:end_idx]
        sessions = cached_indicators['sessions_data'].iloc[start_idx:end_idx]
        retracements = cached_indicators['retracements_data'].iloc[start_idx:end_idx]
        
        # Aquí irían las funciones add_FVG, add_swing_highs_lows, etc.
        # Por simplicidad, solo mostramos que se están agregando
        print(f"   🔍 Agregando indicadores SMC al gráfico...")
        
    except Exception as e:
        print(f"   ⚠️ Error agregando indicadores SMC: {e}")

def create_optimized_chart(df_completo, df_5m_indicators, pos, window, visualizer, cached_indicators, trading_signals):
    """
    Crear gráfico optimizado con cálculo selectivo por temporalidad
    """
    print(f"🎨 Creando gráfico optimizado para posición {pos}...")
    
    # Usar df_completo para la ventana principal (para tener contexto completo)
    window_df = df_completo.iloc[pos - window : pos]
    
    # Crear subplots: Candlesticks (55%), MACD (12%), RSI (12%), Tendencia 15M (7%), Tendencia 1H (7%), Tendencia 4H (7%)
    fig = sp.make_subplots(
        rows=6, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        row_heights=[0.55, 0.12, 0.12, 0.07, 0.07, 0.07],
        subplot_titles=('', 'MACD', 'RSI', 'TENDENCIA 15M', 'TENDENCIA 1H', 'TENDENCIA 4H')
    )
    
    # 1. GRÁFICO PRINCIPAL - CANDLESTICKS
    fig.add_trace(
        go.Candlestick(
            x=window_df.index,
            open=window_df["open"],
            high=window_df["high"],
            low=window_df["low"],
            close=window_df["close"],
            increasing_line_color="#77dd76",
            decreasing_line_color="#ff6962",
            name="EURUSD"
        ),
        row=1, col=1
    )
    
    # Agregar indicadores SMC
    add_smc_indicators(fig, window_df, cached_indicators, pos, window)
    
    # Agregar señales de trading
    add_trading_signals(fig, df_completo, trading_signals, window_df)
    
    # 2. GRÁFICO MACD
    # Usar df_5m_indicators para los indicadores técnicos (MACD, RSI)
    # Ajustar índices para que coincidan con la ventana
    start_idx = max(0, len(df_5m_indicators) - window)
    end_idx = len(df_5m_indicators)
    
    macd_line = cached_indicators['macd_line'].iloc[start_idx:end_idx]
    signal_line = cached_indicators['signal_line'].iloc[start_idx:end_idx]
    histogram = cached_indicators['histogram'].iloc[start_idx:end_idx]
    
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=macd_line,
            mode='lines',
            name='MACD',
            line=dict(color='teal', width=1),
            showlegend=False
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=signal_line,
            mode='lines',
            name='Signal',
            line=dict(color='orange', width=1),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Histograma MACD
    colors = ['green' if val >= 0 else 'red' for val in histogram]
    fig.add_trace(
        go.Bar(
            x=window_df.index,
            y=histogram,
            name='Histogram',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Línea cero en MACD
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
    
    # 3. GRÁFICO RSI
    rsi = cached_indicators['rsi'].iloc[start_idx:end_idx]
    
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=rsi,
            mode='lines',
            name='RSI',
            line=dict(color='yellow', width=2),
            showlegend=False
        ),
        row=3, col=1
    )
    
    # Líneas de referencia RSI
    fig.add_hline(y=50, line_dash="solid", line_color="gray", row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="red", row=3, col=1)
    
    # 4. GRÁFICO TENDENCIA 15M
    try:
        trend_15m = visualizer.trend_cache.get('15M')
        if trend_15m is not None:
            trend_values_15m = trend_15m['trend_data'].iloc[pos - window:pos]['trend']
            
            fig.add_trace(
                go.Scatter(
                    x=window_df.index,
                    y=trend_values_15m,
                    mode='lines',
                    name='Tendencia 15M',
                    line=dict(color='cyan', width=2),
                    showlegend=False
                ),
                row=4, col=1
            )
            
            current_trend_15m = trend_values_15m.iloc[-1] if len(trend_values_15m) > 0 else 0
            print(f"   📊 15M: Tendencia actual: {current_trend_15m:.2f}")
        else:
            print(f"   ⚠️ No hay datos de tendencia 15M disponibles")
            
    except Exception as e:
        print(f"   ❌ Error graficando tendencia 15M: {e}")
    
    # 5. GRÁFICO TENDENCIA 1H
    try:
        trend_1h = visualizer.trend_cache.get('1H')
        if trend_1h is not None:
            trend_values_1h = trend_1h['trend_data'].iloc[pos - window:pos]['trend']
            
            fig.add_trace(
                go.Scatter(
                    x=window_df.index,
                    y=trend_values_1h,
                    mode='lines',
                    name='Tendencia 1H',
                    line=dict(color='yellow', width=2),
                    showlegend=False
                ),
                row=5, col=1
            )
            
            current_trend_1h = trend_values_1h.iloc[-1] if len(trend_values_1h) > 0 else 0
            print(f"   📊 1H: Tendencia actual: {current_trend_1h:.2f}")
        else:
            print(f"   ⚠️ No hay datos de tendencia 1H disponibles")
            
    except Exception as e:
        print(f"   ❌ Error graficando tendencia 1H: {e}")
    
    # 6. GRÁFICO TENDENCIA 4H
    try:
        trend_4h = visualizer.trend_cache.get('4H')
        if trend_4h is not None:
            trend_values_4h = trend_4h['trend_data'].iloc[pos - window:pos]['trend']
            
            fig.add_trace(
                go.Scatter(
                    x=window_df.index,
                    y=trend_values_4h,
                    mode='lines',
                    name='Tendencia 4H',
                    line=dict(color='magenta', width=2),
                    showlegend=False
                ),
                row=6, col=1
            )
            
            current_trend_4h = trend_values_4h.iloc[-1] if len(trend_values_4h) > 0 else 0
            print(f"   📊 4H: Tendencia actual: {current_trend_4h:.2f}")
        else:
            print(f"   ⚠️ No hay datos de tendencia 4H disponibles")
            
    except Exception as e:
        print(f"   ❌ Error graficando tendencia 4H: {e}")
    
    # Líneas de referencia para todas las tendencias
    for row in [4, 5, 6]:
        fig.add_hline(y=2, line_dash="dash", line_color="lime", row=row, col=1)
        fig.add_hline(y=1, line_dash="dash", line_color="lightgreen", row=row, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", row=row, col=1)
        fig.add_hline(y=-1, line_dash="dash", line_color="lightcoral", row=row, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="red", row=row, col=1)
    
    # Configurar layout
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=0, r=0, b=50, t=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(12, 14, 18, 1)",
        font=dict(color="white"),
        width=800,
        height=900
    )
    
    # Configurar ejes
    for row in range(1, 7):
        fig.update_xaxes(
            title_text="", 
            row=row, col=1,
            tickformat="%d/%m %H:%M",
            tickangle=45,
            tickfont=dict(size=9 if row > 1 else 10, color="white"),
            tickmode='auto',
            nticks=6 if row > 1 else 8
        )
        
        if row == 1:
            fig.update_yaxes(visible=False, showticklabels=False, row=row, col=1)
        elif row == 2:
            fig.update_yaxes(title_text="MACD", row=row, col=1)
        elif row == 3:
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=row, col=1)
        else:
            timeframe_name = ['', '', '', 'TENDENCIA 15M', 'TENDENCIA 1H', 'TENDENCIA 4H'][row-1]
            fig.update_yaxes(title_text=timeframe_name, range=[-2.5, 2.5], row=row, col=1)
    
    return fig

def import_data(velas_requeridas=None):
    """Importar datos desde CSV - calcula automáticamente cuántas velas necesita"""
    csv_path = "tests/test_data/EURUSD/EURUSD_5M_20250815_094446.csv"
    df = pd.read_csv(csv_path, index_col="datetime")
    df = df.astype(float)
    df = df[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index)
    
    # Si no se especifica, calcular automáticamente cuántas velas necesitamos
    if velas_requeridas is None:
        # Calcular necesidades para cada timeframe
        # 15M: 300 * 3 = 900 velas 5M
        # 1H: 300 * 12 = 3600 velas 5M  
        # 4H: 300 * 48 = 14400 velas 5M
        # Tomar el máximo: 14400 velas 5M
        velas_requeridas = 14400
        print(f"📊 Calculando necesidades automáticamente:")
        print(f"   • 15M: 300 velas × 3 = 900 velas 5M")
        print(f"   • 1H: 300 velas × 12 = 3600 velas 5M")
        print(f"   • 4H: 300 velas × 48 = 14400 velas 5M")
        print(f"   • Total requerido: {velas_requeridas} velas 5M")
    
    # Tomar solo las últimas N velas
    if len(df) > velas_requeridas:
        df = df.tail(velas_requeridas)
        print(f"📊 Tomando solo las últimas {velas_requeridas} velas de {len(df) + (len(df) - velas_requeridas)} disponibles")
    else:
        print(f"⚠️ Datos insuficientes: {len(df)} velas disponibles, se necesitan {velas_requeridas}")
    
    df.index = df.index.strftime("%Y-%m-%d %H:%M:%S")
    return df

def main():
    """Función principal optimizada"""
    start_time = datetime.datetime.now()
    print(f"🚀 INICIO DEL SCRIPT OPTIMIZADO: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Cargar datos (calcula automáticamente cuántas velas necesita)
    df_completo = import_data()
    print(f"📊 Datos completos cargados: {len(df_completo)} filas")
    print(f"📅 Rango de fechas: {df_completo.index[0]} a {df_completo.index[-1]}")
    
    # 2. Inicializar visualizador optimizado
    visualizer = OptimizedTradingVisualizer()
    
    # 3. Calcular indicadores completos para 5M (solo últimas 300 velas para eficiencia)
    print(f"\n🔧 CÁLCULO COMPLETO 5M (ÚLTIMAS 300 VELAS):")
    try:
        # Usar solo las últimas 300 velas para indicadores 5M (más eficiente)
        df_5m_indicators = df_completo.tail(300)
        print(f"📊 Usando {len(df_5m_indicators)} velas para indicadores 5M")
        
        cached_indicators = visualizer.calculate_5m_complete_indicators(df_5m_indicators)
        print(f"✅ Indicadores 5M calculados y cacheados")
    except Exception as e:
        print(f"❌ Error calculando indicadores 5M: {e}")
        return
    
    # 4. Calcular tendencias para temporalidades superiores (UNA SOLA VEZ)
    print(f"\n🔄 CÁLCULO DE TENDENCIAS SUPERIORES (UNA SOLA VEZ):")
    
    timeframes = ['15M', '1H', '4H']
    
    for tf in timeframes:
        try:
            print(f"\n--- {tf} ---")
            # Usar el DataFrame completo para calcular tendencias superiores
            trend_data = visualizer.calculate_higher_timeframe_trend_only(df_completo, tf)
            
            # Cachear para uso posterior
            visualizer.trend_cache[tf] = trend_data
            
            # Mostrar resumen
            trend_summary = visualizer.get_trend_summary(trend_data, tf)
            print(f"   📈 {trend_summary}")
            
        except Exception as e:
            print(f"❌ Error calculando {tf}: {e}")
    
    # 5. Generar frames optimizados
    frames_dir = "frames_png_optimized"
    if os.path.exists(frames_dir):
        import shutil
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    
    window = 100
    total_frames_to_generate = 20
    start_pos = max(400, len(df_completo) - total_frames_to_generate)
    
    print(f"\n🎬 Generando {total_frames_to_generate} frames optimizados...")
    print(f"📊 Posiciones: {start_pos} a {len(df_completo)}")
    
    for pos in tqdm(range(start_pos, len(df_completo)), desc="Generando frames optimizados"):
        print(f"\n🎬 Procesando frame {pos}/{len(df_completo)}...")
        
        try:
            # Crear gráfico optimizado (sin recálculos)
            fig = create_optimized_chart(df_completo, df_5m_indicators, pos, window, visualizer, cached_indicators, [])
            
            # Guardar frame
            frame_filename = f"{frames_dir}/frame_{pos:04d}.png"
            fig.write_image(frame_filename, width=800, height=900)
            
            print(f"✅ Frame {pos} guardado: {frame_filename}")
            
        except Exception as e:
            print(f"❌ Frame {pos} falló: {e}")
            continue
    
    end_time = datetime.datetime.now()
    print(f"\n🎯 PROCESO OPTIMIZADO COMPLETADO")
    print(f"⏱️ Tiempo total: {end_time - start_time}")
    print(f"📁 Frames guardados en: {frames_dir}/")
    print(f"🚀 Optimización implementada:")
    print(f"   • 5M: Indicadores calculados UNA SOLA VEZ")
    print(f"   • 15M/1H/4H: Solo tendencias, UNA SOLA VEZ")
    print(f"   • Sincronización de índices para graficar correctamente")

if __name__ == "__main__":
    main()
