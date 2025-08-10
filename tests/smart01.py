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

# Importar paquetes asumiendo ejecución como módulo (python -m tests.smart01)
from smartmoneyconcepts.smc import smc
from estrategia.momentum_smc_strategy_lib import MomentumSMCStrategyLib

class TradingSignalVisualizer:
    """
    Visualizador de señales de trading basado en MomentumSMCStrategyLib
    """
    def __init__(self):
        self.strategy_lib = MomentumSMCStrategyLib()
        self.signals = []
        self.entry_points = []
        self.stop_losses = []
        self.take_profits = []
        self.cached_indicators = None
    
    def calculate_signals(self, df):
        """
        Calcular señales de trading usando la librería MomentumSMCStrategyLib
        y almacenar los indicadores precalculados para su reutilización
        """
        # Precalcular indicadores una sola vez
        self.cached_indicators = self.strategy_lib.precalculate_indicators(df)
        
        # Usar la librería para analizar todas las estrategias
        signals = self.strategy_lib.analyze_all_strategies(df)
        
        # Obtener resumen de señales
        summary = self.strategy_lib.get_signal_summary(df)
        print(f"📊 Resumen de señales:")
        print(f"   Total: {summary['total_signals']}")
        print(f"   Por estrategia: {summary['by_strategy']}")
        print(f"   Por confianza: {summary['by_confidence']}")
        
        return signals
    
    def get_cached_indicators(self):
        """
        Obtener los indicadores precalculados
        """
        return self.cached_indicators

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
            
            # Si es una señal de Order Block + Fibonacci, mostrar niveles Fibonacci
            if signal['strategy'] == 'Order Block + Fibonacci' and 'ob_info' in signal:
                ob_info = signal['ob_info']
                
                # Obtener el rango del movimiento
                if signal['type'] == 'BUY':
                    swing_high = ob_info['top']
                    swing_low = ob_info['bottom']
                else:
                    swing_high = ob_info['bottom']
                    swing_low = ob_info['top']
                
                price_range = swing_high - swing_low
                
                # Niveles Fibonacci comunes
                fib_levels = {
                    '0%': 0,
                    '23.6%': 0.236,
                    '38.2%': 0.382,
                    '50%': 0.5,
                    '61.8%': 0.618,
                    '78.6%': 0.786,
                    '100%': 1
                }
                
                # Dibujar líneas Fibonacci
                for level_name, fib_ratio in fib_levels.items():
                    fib_price = swing_low + (price_range * fib_ratio)
                    
                    # Línea horizontal
                    fig.add_shape(
                        type="line",
                        x0=signal['timestamp'],
                        y0=fib_price,
                        x1=window_df.index[-1],
                        y1=fib_price,
                        line=dict(
                            color="gold",
                            width=1,
                            dash="dot",
                        ),
                        opacity=0.5,
                        row=1, col=1
                    )
                    
                    # Etiqueta del nivel
                    fig.add_annotation(
                        x=signal['timestamp'],
                        y=fib_price,
                        text=f"Fib {level_name}",
                        showarrow=False,
                        xanchor="right",
                        font=dict(size=8, color="gold"),
                        row=1, col=1
                    )
                
                # Resaltar el nivel actual de retroceso
                current_retracement = ob_info['retracement'] * 100
                retracement_text = f"Retroceso actual: {current_retracement:.1f}%"
                
                fig.add_annotation(
                    x=signal['timestamp'],
                    y=signal['price'],
                    text=retracement_text,
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="gold",
                    font=dict(size=10, color="gold"),
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor="gold",
                    borderwidth=1,
                    row=1, col=1
                )
            
            # Agregar anotación con confianza y detalles
            strategy_short = signal['strategy'].replace(' + ', '+')[:15]
            annotation_text = f"{'🔼' if signal['type'] == 'BUY' else '🔽'} {strategy_short}\n{confidence_text}"
            
            # Agregar información adicional si está disponible
            if 'ob_info' in signal:
                ob_info = signal['ob_info']
                if ob_info.get('divergencia_rsi'):
                    annotation_text += "\n↗️ Div. RSI"
                if ob_info.get('histograma_mejorando'):
                    annotation_text += "\n📈 MACD+"
                if ob_info.get('confirmacion_1h'):
                    annotation_text += "\n✅ 1H"
            
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


def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calcular MACD: MACD Line, Signal Line, Histogram"""
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_rsi(df, period=14):
    """Calcular RSI"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def add_trend_indicator(fig, df, trend_data, window_df):
    """
    Agregar indicador de tendencia con múltiples opciones de visualización
    """
    # Obtener el valor de tendencia actual
    current_trend = trend_data['trend'].iloc[-1]
    
    if pd.isna(current_trend):
        return fig
    
    # Ya no agregamos líneas ni anotaciones en el gráfico principal
    # Solo mantenemos el subplot de tendencia
    
    return fig

def add_FVG(fig, df, fvg_data):
    window_size = len(df)
    
    # Asegurarse de que fvg_data use los mismos índices que df
    fvg_data = fvg_data.reset_index(drop=True)
    
    for i in range(len(fvg_data)):
        if not pd.isna(fvg_data["FVG"].iloc[i]):
            # Asegurarse de que x1 no exceda el tamaño de la ventana
            x1 = min(
                int(fvg_data["MitigatedIndex"].iloc[i])
                if fvg_data["MitigatedIndex"].iloc[i] != 0
                else window_size - 1,
                window_size - 1
            )
            
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=fvg_data["Top"].iloc[i],
                x1=df.index[x1],
                y1=fvg_data["Bottom"].iloc[i],
                line=dict(width=0),
                fillcolor="yellow",
                opacity=0.2,
            )
            
            # Calcular punto medio asegurándose de no exceder los límites
            mid_x = min(round((i + x1) / 2), window_size - 1)
            mid_y = (fvg_data["Top"].iloc[i] + fvg_data["Bottom"].iloc[i]) / 2
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="FVG",
                    textposition="middle center",
                    textfont=dict(color='rgba(255, 255, 255, 0.4)', size=8),
                )
            )
    return fig


def add_swing_highs_lows(fig, df, swing_highs_lows_data):
    window_size = len(df)
    
    # Asegurarse de que swing_highs_lows_data use los mismos índices que df
    swing_highs_lows_data = swing_highs_lows_data.reset_index(drop=True)
    
    indexs = []
    level = []
    for i in range(len(swing_highs_lows_data)):
        if not pd.isna(swing_highs_lows_data["HighLow"].iloc[i]):
            if i < window_size:  # Solo agregar puntos dentro de la ventana
                indexs.append(i)
                level.append(swing_highs_lows_data["Level"].iloc[i])

    # Dibujar líneas en el gráfico
    for i in range(len(indexs) - 1):
        if indexs[i] < window_size and indexs[i + 1] < window_size:  # Verificar que ambos puntos estén en la ventana
            fig.add_trace(
                go.Scatter(
                    x=[df.index[indexs[i]], df.index[indexs[i + 1]]],
                    y=[level[i], level[i + 1]],
                    mode="lines",
                    line=dict(
                        color=(
                            "rgba(0, 128, 0, 0.2)"
                            if swing_highs_lows_data["HighLow"].iloc[indexs[i]] == -1
                            else "rgba(255, 0, 0, 0.2)"
                        ),
                    ),
                )
            )

    return fig


def add_bos_choch(fig, df, bos_choch_data):
    window_size = len(df)
    
    # Asegurarse de que bos_choch_data use los mismos índices que df
    bos_choch_data = bos_choch_data.reset_index(drop=True)
    
    for i in range(len(bos_choch_data)):
        if i >= window_size:
            break
            
        # Procesar BOS
        if not pd.isna(bos_choch_data["BOS"].iloc[i]):
            broken_idx = min(int(bos_choch_data["BrokenIndex"].iloc[i]), window_size - 1)
            mid_x = min(round((i + broken_idx) / 2), window_size - 1)
            mid_y = bos_choch_data["Level"].iloc[i]
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[broken_idx]],
                    y=[bos_choch_data["Level"].iloc[i], bos_choch_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 165, 0, 0.2)",
                    ),
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="BOS",
                    textposition="top center" if bos_choch_data["BOS"].iloc[i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                )
            )
            
        # Procesar CHOCH
        if not pd.isna(bos_choch_data["CHOCH"].iloc[i]):
            broken_idx = min(int(bos_choch_data["BrokenIndex"].iloc[i]), window_size - 1)
            mid_x = min(round((i + broken_idx) / 2), window_size - 1)
            mid_y = bos_choch_data["Level"].iloc[i]
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[broken_idx]],
                    y=[bos_choch_data["Level"].iloc[i], bos_choch_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(
                        color="rgba(0, 0, 255, 0.2)",
                    ),
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="CHOCH",
                    textposition="top center" if bos_choch_data["CHOCH"].iloc[i] == 1 else "bottom center",
                    textfont=dict(color="rgba(0, 0, 255, 0.4)", size=8),
                )
            )

    return fig


def add_OB(fig, df, ob_data):
    def format_volume(volume):
        if volume >= 1e12:
            return f"{volume / 1e12:.3f}T"
        elif volume >= 1e9:
            return f"{volume / 1e9:.3f}B"
        elif volume >= 1e6:
            return f"{volume / 1e6:.3f}M"
        elif volume >= 1e3:
            return f"{volume / 1e3:.3f}k"
        else:
            return f"{volume:.2f}"

    window_size = len(df)
    
    # Asegurarse de que ob_data use los mismos índices que df
    ob_data = ob_data.reset_index(drop=True)

    for i in range(len(ob_data)):
        if i >= window_size:
            break
            
        # Procesar Order Blocks alcistas
        if ob_data["OB"].iloc[i] == 1:
            # Asegurarse de que x1 no exceda el tamaño de la ventana
            x1 = min(
                int(ob_data["MitigatedIndex"].iloc[i]) if ob_data["MitigatedIndex"].iloc[i] != 0 else window_size - 1,
                window_size - 1
            )
            
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_data["Bottom"].iloc[i],
                x1=df.index[x1],
                y1=ob_data["Top"].iloc[i],
                line=dict(color="Purple"),
                fillcolor="Purple",
                opacity=0.2,
                name="Bullish OB",
                legendgroup="bullish ob",
                showlegend=True,
            )

            # Calcular x_center asegurándose de no exceder los límites
            if ob_data["MitigatedIndex"].iloc[i] > 0:
                mid_point = min(int(i + (ob_data["MitigatedIndex"].iloc[i] - i) / 2), window_size - 1)
            else:
                mid_point = min(int(i + (window_size - i) / 2), window_size - 1)
            x_center = df.index[mid_point]

            y_center = (ob_data["Bottom"].iloc[i] + ob_data["Top"].iloc[i]) / 2
            volume_text = format_volume(ob_data["OBVolume"].iloc[i])
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"].iloc[i]}%)'

            fig.add_annotation(
                x=x_center,
                y=y_center,
                xref="x",
                yref="y",
                align="center",
                text=annotation_text,
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
        
        # Procesar Order Blocks bajistas
        elif ob_data["OB"].iloc[i] == -1:
            # Asegurarse de que x1 no exceda el tamaño de la ventana
            x1 = min(
                int(ob_data["MitigatedIndex"].iloc[i]) if ob_data["MitigatedIndex"].iloc[i] != 0 else window_size - 1,
                window_size - 1
            )
            
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_data["Bottom"].iloc[i],
                x1=df.index[x1],
                y1=ob_data["Top"].iloc[i],
                line=dict(color="Purple"),
                fillcolor="Purple",
                opacity=0.2,
                name="Bearish OB",
                legendgroup="bearish ob",
                showlegend=True,
            )

            # Calcular x_center asegurándose de no exceder los límites
            if ob_data["MitigatedIndex"].iloc[i] > 0:
                mid_point = min(int(i + (ob_data["MitigatedIndex"].iloc[i] - i) / 2), window_size - 1)
            else:
                mid_point = min(int(i + (window_size - i) / 2), window_size - 1)
            x_center = df.index[mid_point]

            y_center = (ob_data["Bottom"].iloc[i] + ob_data["Top"].iloc[i]) / 2
            volume_text = format_volume(ob_data["OBVolume"].iloc[i])
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"].iloc[i]}%)'

            fig.add_annotation(
                x=x_center,
                y=y_center,
                xref="x",
                yref="y",
                align="center",
                text=annotation_text,
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
    return fig


def add_liquidity(fig, df, liquidity_data):
    window_size = len(df)
    
    # Asegurarse de que liquidity_data use los mismos índices que df
    liquidity_data = liquidity_data.reset_index(drop=True)
    
    for i in range(len(liquidity_data)):
        if i >= window_size:
            break
            
        # Procesar niveles de liquidez
        if not pd.isna(liquidity_data["Liquidity"].iloc[i]):
            end_idx = min(int(liquidity_data["End"].iloc[i]), window_size - 1)
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[end_idx]],
                    y=[liquidity_data["Level"].iloc[i], liquidity_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 165, 0, 0.2)",
                    ),
                )
            )
            
            mid_x = min(round((i + end_idx) / 2), window_size - 1)
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[liquidity_data["Level"].iloc[i]],
                    mode="text",
                    text="Liquidity",
                    textposition="top center" if liquidity_data["Liquidity"].iloc[i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                )
            )
        
        # Procesar liquidez barrida
        if (not pd.isna(liquidity_data["Swept"].iloc[i]) and 
            liquidity_data["Swept"].iloc[i] != 0):
            
            end_idx = min(int(liquidity_data["End"].iloc[i]), window_size - 1)
            swept_idx = min(int(liquidity_data["Swept"].iloc[i]), window_size - 1)
            
            # Determinar el nivel de precio para el punto barrido
            swept_price = (
                df["high"].iloc[swept_idx]
                if liquidity_data["Liquidity"].iloc[i] == 1
                else df["low"].iloc[swept_idx]
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[end_idx], df.index[swept_idx]],
                    y=[liquidity_data["Level"].iloc[i], swept_price],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 0, 0, 0.2)",
                    ),
                )
            )
            
            # Calcular punto medio para la anotación
            mid_x = min(round((end_idx + swept_idx) / 2), window_size - 1)
            mid_y = (liquidity_data["Level"].iloc[i] + swept_price) / 2
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="Liquidity Swept",
                    textposition="top center" if liquidity_data["Liquidity"].iloc[i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 0, 0, 0.4)", size=8),
                )
            )
    return fig


def add_previous_high_low(fig, df, previous_high_low_data):
    window_size = len(df)
    
    # Asegurarse de que previous_high_low_data use los mismos índices que df
    previous_high_low_data = previous_high_low_data.reset_index(drop=True)
    
    # Obtener series de máximos y mínimos
    high = previous_high_low_data["PreviousHigh"]
    low = previous_high_low_data["PreviousLow"]

    # Procesar máximos previos
    high_levels = []
    high_indexes = []
    for i in range(len(high)):
        if i >= window_size:
            break
        if (not pd.isna(high.iloc[i]) and 
            high.iloc[i] != (high_levels[-1] if high_levels else None)):
            high_levels.append(high.iloc[i])
            high_indexes.append(i)

    # Procesar mínimos previos
    low_levels = [] 
    low_indexes = []
    for i in range(len(low)):
        if i >= window_size:
            break
        if (not pd.isna(low.iloc[i]) and 
            low.iloc[i] != (low_levels[-1] if low_levels else None)):
            low_levels.append(low.iloc[i])
            low_indexes.append(i)

    # Dibujar líneas de máximos previos
    for i in range(len(high_indexes)-1):
        if high_indexes[i] >= window_size or high_indexes[i+1] >= window_size:
            continue
            
        fig.add_trace(
            go.Scatter(
                x=[df.index[high_indexes[i]], df.index[high_indexes[i+1]]],
                y=[high_levels[i], high_levels[i]],
                mode="lines",
                line=dict(
                    color="rgba(255, 255, 255, 0.2)",
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df.index[high_indexes[i+1]]],
                y=[high_levels[i]],
                mode="text",
                text="PH",
                textposition="top center",
                textfont=dict(color="rgba(255, 255, 255, 0.4)", size=8),
            )
        )

    # Dibujar líneas de mínimos previos
    for i in range(len(low_indexes)-1):
        if low_indexes[i] >= window_size or low_indexes[i+1] >= window_size:
            continue
            
        fig.add_trace(
            go.Scatter(
                x=[df.index[low_indexes[i]], df.index[low_indexes[i+1]]],
                y=[low_levels[i], low_levels[i]],
                mode="lines",
                line=dict(
                    color="rgba(255, 255, 255, 0.2)",
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df.index[low_indexes[i+1]]],
                y=[low_levels[i]],
                mode="text",
                text="PL",
                textposition="bottom center",
                textfont=dict(color="rgba(255, 255, 255, 0.4)", size=8),
            )
        )

    return fig


def add_sessions(fig, df, sessions):
    window_size = len(df)
    
    # Asegurarse de que sessions use los mismos índices que df
    sessions = sessions.reset_index(drop=True)
    
    for i in range(len(sessions) - 1):
        if i >= window_size - 1:  # -1 porque necesitamos i+1 para el x1
            break
            
        if sessions["Active"].iloc[i] == 1:
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=sessions["Low"].iloc[i],
                x1=df.index[i + 1],
                y1=sessions["High"].iloc[i],
                line=dict(width=0),
                fillcolor="#16866E",
                opacity=0.2,
            )
    return fig


def add_retracements(fig, df, retracements):
    window_size = len(df)
    
    # Asegurarse de que retracements use los mismos índices que df
    retracements = retracements.reset_index(drop=True)
    
    for i in range(len(retracements)):
        if i >= window_size:
            break
            
        next_direction = (
            retracements["Direction"].iloc[i + 1]
            if i < len(retracements) - 1
            else 0
        )
        current_direction = retracements["Direction"].iloc[i]
        
        # Verificar condiciones para mostrar el retroceso
        if (
            (next_direction != current_direction or i == len(retracements) - 1) and
            current_direction != 0 and
            (next_direction if i < len(retracements) - 1 else current_direction) != 0
        ):
            # Determinar la posición Y basada en la dirección
            y_position = (
                df["high"].iloc[i]
                if current_direction == -1
                else df["low"].iloc[i]
            )
            
            # Agregar anotación con porcentajes de retroceso
            fig.add_annotation(
                x=df.index[i],
                y=y_position,
                xref="x",
                yref="y",
                text=(
                    f"C:{retracements['CurrentRetracement%'].iloc[i]}%<br>"
                    f"D:{retracements['DeepestRetracement%'].iloc[i]}%"
                ),
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
    return fig


# get the data
def import_data():
    # Reemplaza la función import_data y la carga de df por esto:
    csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
    """Importa datos desde CSV - procesados igual que los datos de Binance"""
    # Leer el CSV desde el directorio raíz
    df = pd.read_csv(csv_path, index_col="datetime")
    
    # Convertir todas las columnas a float (igual que en Binance)
    df = df.astype(float)    
    # Asegurar que las columnas estén en el orden correcto
    df = df[["open", "high", "low", "close", "volume"]]    
    # Convertir el índice a datetime y luego a string con formato específico (igual que Binance)
    df.index = pd.to_datetime(df.index)
    df.index = df.index.strftime("%Y-%m-%d %H:%M:%S")    
    # Tomar las últimas 500 filas (igual que en Binance)
    df = df.iloc[-120:]
    
    return df


df = import_data()
df = df.iloc[-500:]

# Inicializar visualizador de señales de trading
signal_visualizer = TradingSignalVisualizer()
print("🔍 Calculando señales de trading...")
trading_signals = signal_visualizer.calculate_signals(df)
print(f"✅ Encontradas {len(trading_signals)} señales de trading")

frames_dir = "frames_png"
if os.path.exists(frames_dir):
    import shutil
    shutil.rmtree(frames_dir)
os.makedirs(frames_dir)

window = 100
print(f"🎬 Generando {len(df) - window} frames PNG con MACD, RSI, TENDENCIA y SEÑALES DE TRADING...")

for pos in tqdm(range(window, len(df)), desc="Generando frames"):
    window_df = df.iloc[pos - window : pos]
    
    # Obtener indicadores precalculados
    cached_indicators = signal_visualizer.get_cached_indicators()
    
    # Obtener ventana de indicadores básicos
    macd_line = cached_indicators['macd_line'].iloc[pos - window:pos]
    signal_line = cached_indicators['signal_line'].iloc[pos - window:pos]
    histogram = cached_indicators['histogram'].iloc[pos - window:pos]
    rsi = cached_indicators['rsi'].iloc[pos - window:pos]
    
    # Crear subplots: Candlesticks (60%), MACD (15%), RSI (15%), Tendencia (10%)
    fig = sp.make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,  # Aumentar más el espaciado vertical entre subplots
        row_heights=[0.60, 0.15, 0.15, 0.10],  # Reducir candlesticks y aumentar tendencia
        subplot_titles=('', 'MACD', 'RSI', 'TENDENCIA')
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

    # Obtener ventana de todos los indicadores SMC precalculados
    fvg_data = cached_indicators['fvg_data'].iloc[pos - window:pos]
    swing_highs_lows_data = cached_indicators['swing_highs_lows'].iloc[pos - window:pos]
    bos_choch_data = cached_indicators['bos_choch'].iloc[pos - window:pos]
    ob_data = cached_indicators['ob_data'].iloc[pos - window:pos]
    liquidity_data = cached_indicators['liquidity_data'].iloc[pos - window:pos]
    previous_high_low_data = cached_indicators['previous_high_low_data'].iloc[pos - window:pos]
    sessions = cached_indicators['sessions_data'].iloc[pos - window:pos]
    retracements = cached_indicators['retracements_data'].iloc[pos - window:pos]
    trend_data = cached_indicators['trend_data'].iloc[pos - window:pos]
    
    # Agregar indicadores SMC al gráfico principal
    add_FVG(fig, window_df, fvg_data)
    add_swing_highs_lows(fig, window_df, swing_highs_lows_data)
    add_bos_choch(fig, window_df, bos_choch_data)
    add_OB(fig, window_df, ob_data)
    add_liquidity(fig, window_df, liquidity_data)
    add_previous_high_low(fig, window_df, previous_high_low_data)
    add_sessions(fig, window_df, sessions)
    add_retracements(fig, window_df, retracements)
    add_trend_indicator(fig, df, trend_data, window_df)
    
    # Agregar señales de trading
    add_trading_signals(fig, df, trading_signals, window_df)
    
    # 2. GRÁFICO MACD
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

    # Configurar layout
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=0, r=0, b=50, t=0),  # Aumentar margen inferior para etiquetas del eje X
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(12, 14, 18, 1)",
        font=dict(color="white"),
        width=800,
        height=700
    )
    
    # Configurar ejes
    fig.update_xaxes(
        visible=True, 
        showticklabels=True, 
        row=1, col=1,
        tickformat="%d/%m %H:%M",
        tickangle=45,
        tickfont=dict(size=10, color="white"),
        tickmode='auto',
        nticks=8
    )
    fig.update_yaxes(visible=False, showticklabels=False, row=1, col=1)
    
    # Configurar ejes MACD
    fig.update_xaxes(
        title_text="", 
        row=2, col=1,
        tickformat="%d/%m %H:%M",
        tickangle=45,
        tickfont=dict(size=9, color="white"),
        tickmode='auto',
        nticks=6
    )
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    
    # Configurar ejes RSI
    fig.update_xaxes(
        title_text="", 
        row=3, col=1,
        tickformat="%d/%m %H:%M",
        tickangle=45,
        tickfont=dict(size=9, color="white"),
        tickmode='auto',
        nticks=6
    )
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
    
    # 4. GRÁFICO TENDENCIA - Línea continua como RSI
    # Obtener todos los valores de tendencia para la ventana actual
    trend_values = trend_data['trend'].iloc[-len(window_df):]
    
    # Crear línea de tendencia continua
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=trend_values,
            mode='lines',
            name='Tendencia',
            line=dict(color='cyan', width=2),
            showlegend=False
        ),
        row=4, col=1
    )
    
    # Líneas de referencia para tendencia
    fig.add_hline(y=2, line_dash="dash", line_color="lime", row=4, col=1)  # Alcista fuerte
    fig.add_hline(y=1, line_dash="dash", line_color="lightgreen", row=4, col=1)  # Alcista
    fig.add_hline(y=0, line_dash="solid", line_color="gray", row=4, col=1)  # Lateral
    fig.add_hline(y=-1, line_dash="dash", line_color="lightcoral", row=4, col=1)  # Bajista
    fig.add_hline(y=-2, line_dash="dash", line_color="red", row=4, col=1)  # Bajista fuerte
    
    # Configurar ejes Tendencia
    fig.update_xaxes(
        title_text="", 
        row=4, col=1,
        tickformat="%d/%m %H:%M",
        tickangle=45,
        tickfont=dict(size=9, color="white"),
        tickmode='auto',
        nticks=6
    )
    fig.update_yaxes(title_text="TENDENCIA", range=[-2.5, 2.5], row=4, col=1)
    
    # Guardar frame como PNG
    try:
        frame_filename = f"{frames_dir}/frame_{pos:04d}.png"
        fig.write_image(frame_filename, width=800, height=700)
    except Exception as e:
        print(f"[WARNING] Frame en posición {pos} falló: {e}")

print(f"✅ Frames PNG con MACD, RSI, TENDENCIA y SEÑALES DE TRADING guardados en: {frames_dir}/")
print(f"📊 Total de frames generados: {len(df) - window}")
print(f"🎯 Señales de trading encontradas: {len(trading_signals)}")

# Mostrar detalles de las señales
if trading_signals:
    print(f"\n📈 Detalles de señales:")
    for i, signal in enumerate(trading_signals[:5]):  # Mostrar solo las primeras 5
        confidence = signal.get('confidence', 0)
        print(f"   {i+1}. {signal['strategy']} - Confianza: {confidence}% - Precio: {signal['price']:.5f}")
    if len(trading_signals) > 5:
        print(f"   ... y {len(trading_signals) - 5} señales más")
else:
    print(f"⚠️ No se encontraron señales de trading en los datos proporcionados") 