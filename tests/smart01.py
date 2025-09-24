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

# Importar paquetes asumiendo ejecución como módulo (python -m tests.smart01)
from smartmoneyconcepts.smc import smc
from smartmoneyconcepts.market_analysis_lib import MarketAnalysisLib



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

def calculate_hybrid_trend(df, timeframe_name, market_analysis_lib):
    """
    Calcular tendencia usando Smart Money Concepts (SMC) desde market_analysis_lib
    Simplificado para devolver solo -1 (bajista), 0 (lateral), 1 (alcista)
    
    Parámetros:
    df: DataFrame del timeframe actual
    timeframe_name: Nombre del timeframe (ej: '15M', '1H', '4H')
    market_analysis_lib: Instancia de MarketAnalysisLib
    """
    try:
        # Usar la función detect_trend de market_analysis_lib con método 'structural'
        trend_result = market_analysis_lib.detect_trend(df, method='structural')
        
        # Obtener el valor de tendencia actual (última vela)
        current_trend = trend_result['trend'].iloc[-1]
        
        # Convertir a valores claros -1, 0, 1 según especificación del usuario
        if current_trend > 0.5:
            final_trend = 1  # ALCISTA
        elif current_trend < -0.5:
            final_trend = -1  # BAJISTA
        else:
            final_trend = 0  # LATERAL
        
        print(f"DEBUG {timeframe_name}: SMC detectó tendencia: {final_trend}")
        print(f"   📊 Analizando {len(df)} velas con método 'structural' (HH+HL, LL+LH, BOS, CHoCH)")
        
        # Crear DataFrame de tendencia simplificado
        trend_data = pd.DataFrame({
            'trend': [final_trend] * len(df)
        }, index=df.index)
        
        return trend_data
        
    except Exception as e:
        print(f"Error calculando tendencia SMC para {timeframe_name}: {e}")
        # Retornar tendencia neutral en caso de error
        neutral_trend = pd.DataFrame({
            'trend': [0] * len(df)
        }, index=df.index)
        return neutral_trend

def analyze_simple_price_trend(window_df):
    """
    Análisis simple de tendencia basado en precio cuando no hay estructura SMC clara
    """
    if len(window_df) < 10:
        return 0
    
    # Calcular cambio de precio en las últimas 10 velas
    recent_prices = window_df['close'].tail(10)
    price_change = recent_prices.iloc[-1] - recent_prices.iloc[0]
    price_change_pct = (price_change / recent_prices.iloc[0]) * 100
    
    # Calcular medias móviles simples
    ma_short = window_df['close'].rolling(window=5).mean()
    ma_long = window_df['close'].rolling(window=10).mean()
    
    # Determinar tendencia por precios
    if (ma_short.iloc[-1] > ma_long.iloc[-1] and price_change_pct > 0.1):
        return 1  # Alcista
    elif (ma_short.iloc[-1] < ma_long.iloc[-1] and price_change_pct < -0.1):
        return -1  # Bajista
    else:
        return 0  # Lateral



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
    # Usar el archivo CSV exportado de MT5 con datos de 5 minutos (40,000 velas)
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
    
    # Para 5 minutos: tomar las últimas 500 velas para tener más contexto
    df_5m = df.tail(500)
    
    # Para 15 minutos: agregar 3 velas de 5M para crear 1 vela de 15M
    # Tomamos las últimas 1500 velas para tener más contexto (500 velas de 15M)
    df_extended = df.tail(1500)
    
    # Crear DataFrame de 15M agregando cada 3 velas de 5M de manera manual
    df_15m = pd.DataFrame()
    
    # Agregar cada 3 velas de 5M para crear 1 vela de 15M
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    volume_prices = []
    time_index = []
    
    for i in range(0, len(df_extended), 3):
        if i + 2 < len(df_extended):  # Asegurar que tenemos 3 velas
            # Open: primera vela del grupo
            open_prices.append(df_extended['open'].iloc[i])
            # High: máximo de las 3 velas
            high_prices.append(df_extended['high'].iloc[i:i+3].max())
            # Low: mínimo de las 3 velas
            low_prices.append(df_extended['low'].iloc[i:i+3].min())
            # Close: última vela del grupo
            close_prices.append(df_extended['close'].iloc[i+2])
            # Volume: suma de las 3 velas
            volume_prices.append(df_extended['volume'].iloc[i:i+3].sum())
            # Time: tiempo de la primera vela del grupo
            time_index.append(df_extended.index[i])
    
    df_15m['open'] = open_prices
    df_15m['high'] = high_prices
    df_15m['low'] = low_prices
    df_15m['close'] = close_prices
    df_15m['volume'] = volume_prices
    df_15m.index = time_index
    
    # Tomar las últimas 500 velas de 15M para tener más contexto
    df_15m = df_15m.tail(500)
    
    # Para 1 hora: agregar 12 velas de 5M para crear 1 vela de 1H
    # Tomamos las últimas 6000 velas para tener más contexto (500 velas de 1H)
    df_extended_1h = df.tail(6000)
    
    # Crear DataFrame de 1H agregando cada 12 velas de 5M
    df_1h = pd.DataFrame()
    open_prices_1h = []
    high_prices_1h = []
    low_prices_1h = []
    close_prices_1h = []
    volume_prices_1h = []
    time_index_1h = []
    
    for i in range(0, len(df_extended_1h), 12):
        if i + 11 < len(df_extended_1h):  # Asegurar que tenemos 12 velas
            # Open: primera vela del grupo
            open_prices_1h.append(df_extended_1h['open'].iloc[i])
            # High: máximo de las 12 velas
            high_prices_1h.append(df_extended_1h['high'].iloc[i:i+12].max())
            # Low: mínimo de las 12 velas
            low_prices_1h.append(df_extended_1h['low'].iloc[i:i+12].min())
            # Close: última vela del grupo
            close_prices_1h.append(df_extended_1h['close'].iloc[i+11])
            # Volume: suma de las 12 velas
            volume_prices_1h.append(df_extended_1h['volume'].iloc[i:i+12].sum())
            # Time: tiempo de la primera vela del grupo
            time_index_1h.append(df_extended_1h.index[i])
    
    df_1h['open'] = open_prices_1h
    df_1h['high'] = high_prices_1h
    df_1h['low'] = low_prices_1h
    df_1h['close'] = close_prices_1h
    df_1h['volume'] = volume_prices_1h
    df_1h.index = time_index_1h
    
    # Tomar las últimas 500 velas de 1H
    df_1h = df_1h.tail(500)
    
    # Para 4 horas: agregar 48 velas de 5M para crear 1 vela de 4H
    # Tomamos las últimas 24000 velas para tener más contexto (500 velas de 4H)
    df_extended_4h = df.tail(24000)
    
    # Crear DataFrame de 4H agregando cada 48 velas de 5M
    df_4h = pd.DataFrame()
    open_prices_4h = []
    high_prices_4h = []
    low_prices_4h = []
    close_prices_4h = []
    volume_prices_4h = []
    time_index_4h = []
    
    for i in range(0, len(df_extended_4h), 48):
        if i + 47 < len(df_extended_4h):  # Asegurar que tenemos 48 velas
            # Open: primera vela del grupo
            open_prices_4h.append(df_extended_4h['open'].iloc[i])
            # High: máximo de las 48 velas
            high_prices_4h.append(df_extended_4h['high'].iloc[i:i+48].max())
            # Low: mínimo de las 48 velas
            low_prices_4h.append(df_extended_4h['low'].iloc[i:i+48].min())
            # Close: última vela del grupo
            close_prices_4h.append(df_extended_4h['close'].iloc[i+47])
            # Volume: suma de las 48 velas
            volume_prices_4h.append(df_extended_4h['volume'].iloc[i:i+48].sum())
            # Time: tiempo de la primera vela del grupo
            time_index_4h.append(df_extended_4h.index[i])
    
    df_4h['open'] = open_prices_4h
    df_4h['high'] = high_prices_4h
    df_4h['low'] = low_prices_4h
    df_4h['close'] = close_prices_4h
    df_4h['volume'] = volume_prices_4h
    df_4h.index = time_index_4h
    
    # Tomar las últimas 500 velas de 4H
    df_4h = df_4h.tail(500)
    
    print(f"📊 Datos cargados desde: {csv_path}")
    print(f"   📈 Total de velas en CSV: {len(df)}")
    print(f"   📈 Velas seleccionadas para 5M: {len(df_5m)} (últimas 500)")
    print(f"   📈 Velas seleccionadas para 15M: {len(df_15m)} (últimas 500)")
    print(f"   📈 Velas seleccionadas para 1H: {len(df_1h)} (últimas 500)")
    print(f"   📈 Velas seleccionadas para 4H: {len(df_4h)} (últimas 500)")
    print(f"   ⏰ Timeframes: 5 minutos (datos principales), 15M, 1H y 4H (agregados)")
    print(f"   📅 Rango 5M: {df_5m.index[0]} a {df_5m.index[-1]}")
    print(f"   📅 Rango 15M: {df_15m.index[0]} a {df_15m.index[-1]}")
    print(f"   📅 Rango 1H: {df_1h.index[0]} a {df_1h.index[-1]}")
    print(f"   📅 Rango 4H: {df_4h.index[0]} a {df_4h.index[-1]}")
    print(f"   💡 Análisis múltiple: 5M (visualización) + 15M, 1H, 4H (tendencias)")
    
    return df_5m, df_15m, df_1h, df_4h, df  # Retornar datos de todos los timeframes y CSV completo


df_5m, df_15m, df_1h, df_4h, df = import_data()

# Inicializar MarketAnalysisLib para detección de tendencias SMC
market_analysis = MarketAnalysisLib()

start_time = datetime.datetime.now()
print(f"🚀 INICIO DEL SCRIPT: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📊 Datos 5M cargados: {len(df_5m)} filas")
print(f"📊 Datos 15M cargados: {len(df_15m)} filas")
print(f"📊 Datos 1H cargados: {len(df_1h)} filas")
print(f"📊 Datos 4H cargados: {len(df_4h)} filas")
print(f"📅 Rango 5M: {df_5m.index[0]} a {df_5m.index[-1]}")
print(f"📅 Rango 15M: {df_15m.index[0]} a {df_15m.index[-1]}")
print(f"📅 Rango 1H: {df_1h.index[0]} a {df_1h.index[-1]}")
print(f"📅 Rango 4H: {df_4h.index[0]} a {df_4h.index[-1]}")
print("=" * 80)





# DICCIONARIO GLOBAL para mantener CONTINUIDAD TEMPORAL de tendencias
# Cada vela mantiene su tendencia histórica
global_trend_history = {}

# Importar la estrategia ICC real (misma que usa prueba_icc.py)
try:
    from estrategia.icc import ICCStrategy as SmartMoneyICCStrategy
    print("✅ Estrategia ICC importada exitosamente")
except ImportError as e:
    print(f"❌ Error importando estrategia ICC: {e}")
    SmartMoneyICCStrategy = None

# Función para detectar señales de trading usando la misma lógica que prueba_icc.py
def detect_trading_signals_icc(window_df, df_1h, df_4h):
    """
    Detectar señales de compra y venta usando la misma lógica que prueba_icc.py
    Utiliza SmartMoney ICC Strategy
    """
    signals = []
    
    if SmartMoneyICCStrategy is None:
        return signals
    
    try:
        # Inicializar la estrategia ICC con los mismos parámetros que prueba_icc.py
        smartmoney_icc = SmartMoneyICCStrategy(
            risk_reward_min=1.0,  # R:R mínimo 1:1
            ob_lookback=50,
            fvg_lookback=30,
            swing_length=20
        )
        print(f"🔍 ICC Strategy inicializada correctamente")
        
        # Filtrar datos de múltiples timeframes hasta el tiempo actual
        current_time_str = window_df.index[-1]  # String format
        current_time_dt = pd.to_datetime(current_time_str)  # Convertir a datetime para comparar
        
        # Asegurar que los índices de df_1h y df_4h sean Timestamp
        df_1h_copy = df_1h.copy() if df_1h is not None else pd.DataFrame()
        df_4h_copy = df_4h.copy() if df_4h is not None else pd.DataFrame()
        
        if not df_1h_copy.empty:
            if not isinstance(df_1h_copy.index, pd.DatetimeIndex):
                df_1h_copy.index = pd.to_datetime(df_1h_copy.index)
        
        if not df_4h_copy.empty:
            if not isinstance(df_4h_copy.index, pd.DatetimeIndex):
                df_4h_copy.index = pd.to_datetime(df_4h_copy.index)
        
        # Filtrar datos H1 y H4 hasta el tiempo actual
        df_1h_filtered = df_1h_copy[df_1h_copy.index <= current_time_dt] if not df_1h_copy.empty else pd.DataFrame()
        df_4h_filtered = df_4h_copy[df_4h_copy.index <= current_time_dt] if not df_4h_copy.empty else pd.DataFrame()
        
        # Convertir los índices filtrados a string para la estrategia ICC
        if not df_1h_filtered.empty:
            df_1h_filtered = df_1h_filtered.copy()
            df_1h_filtered.index = df_1h_filtered.index.strftime("%Y-%m-%d %H:%M:%S")
        if not df_4h_filtered.empty:
            df_4h_filtered = df_4h_filtered.copy()
            df_4h_filtered.index = df_4h_filtered.index.strftime("%Y-%m-%d %H:%M:%S")
        
        # Usar la misma función que prueba_icc.py
        print(f"🔍 Analizando señales ICC - Window: {len(window_df)}, H1: {len(df_1h_filtered)}, H4: {len(df_4h_filtered)}")
        icc_signals = smartmoney_icc.scan_for_icc_signals(window_df, df_1h_filtered, df_4h_filtered)
        
        if icc_signals:
            print(f"🎯 Señales ICC encontradas: {len(icc_signals)}")
            for signal in icc_signals:
                direction = signal['direction']
                entry_price = signal['entry_price']
                
                # Convertir a formato compatible con smart01.py
                if direction == 'LONG':
                    signals.append({
                        'type': 'COMPRA',
                        'price': entry_price,
                        'reason': f'ICC SmartMoney LONG @ {entry_price:.5f}',
                        'direction': direction,
                        'entry_price': entry_price,
                        'risk_management': signal.get('risk_management', {})
                    })
                elif direction == 'SHORT':
                    signals.append({
                        'type': 'VENTA',
                        'price': entry_price,
                        'reason': f'ICC SmartMoney SHORT @ {entry_price:.5f}',
                        'direction': direction,
                        'entry_price': entry_price,
                        'risk_management': signal.get('risk_management', {})
                    })
    
    except Exception as e:
        print(f"⚠️ Error en detección ICC: {e}")
        import traceback
        traceback.print_exc()
    
    return signals

print("✅ Sistema de detección de señales ICC implementado (misma lógica que prueba_icc.py)")

frames_dir = "frames_png"
if os.path.exists(frames_dir):
    import shutil
    shutil.rmtree(frames_dir)
os.makedirs(frames_dir)

window = 100  # Ventana de visualización (últimas 100 velas)
# Generar frames desde la vela 100 en adelante para tener más PNGs
total_frames_to_generate = len(df_5m) - window  # Generar desde vela 100 hasta el final
# Iniciar desde la vela 100 (window)
start_pos = window

print(f"🎬 Generando frames PNG desde vela {start_pos} hasta {len(df_5m)}")
print(f"📊 Total de frames a generar: {total_frames_to_generate}")
print(f"🔍 Ventana de visualización: {window} velas por frame")
print(f"🔍 Datos totales disponibles: {len(df_5m)} velas para análisis SMC")
print(f"🔍 Análisis extendido: {window + 50} velas para indicadores técnicos")
print(f"🔍 Verificando cálculos de tendencia múltiple: 5M (visualización) + 15M, 1H, 4H (tendencias)")

print(f"🔄 Iniciando generación de frames...")
print(f"   📊 Posiciones a procesar: {start_pos} a {len(df_5m)}")
print(f"   ⏰ Total de frames: {total_frames_to_generate}")
print(f"   🔍 Cada frame analiza {len(df_5m)} velas pero visualiza solo {window} velas")

for pos in tqdm(range(start_pos, len(df_5m)), desc="Generando últimos frames"):
    print(f"\n🎬 Procesando frame {pos}/{len(df_5m)}...")
    
    # Calcular la ventana de análisis extendida para indicadores
    # Necesitamos al menos 50 velas antes para RSI y MACD
    analysis_start = max(0, pos - window - 50)  # 50 velas adicionales para análisis
    analysis_df = df_5m.iloc[analysis_start : pos]  # Datos para calcular indicadores
    
    # Ventana de visualización (últimas 100 velas)
    window_df = df_5m.iloc[pos - window : pos]
    
    # Calcular indicadores básicos con datos extendidos
    if len(analysis_df) >= 26:  # Mínimo para MACD (26 períodos) + RSI (14 períodos)
        macd_line, signal_line, histogram = calculate_macd(analysis_df)
        rsi = calculate_rsi(analysis_df)
        
        # Tomar solo la parte correspondiente a la ventana de visualización
        macd_line = macd_line.tail(len(window_df))
        signal_line = signal_line.tail(len(window_df))
        histogram = histogram.tail(len(window_df))
        rsi = rsi.tail(len(window_df))
        
        print(f"   📊 Análisis: {len(analysis_df)} velas, Visualización: {len(window_df)} velas")
    else:
        # Si no hay suficientes datos, crear indicadores básicos
        macd_line = pd.Series([0] * len(window_df), index=window_df.index)
        signal_line = pd.Series([0] * len(window_df), index=window_df.index)
        histogram = pd.Series([0] * len(window_df), index=window_df.index)
        rsi = pd.Series([50] * len(window_df), index=window_df.index)
    
    # Calcular tendencia usando Smart Money Concepts (SMC) - Estructura del mercado
    # IMPLEMENTAR CONTINUIDAD DE TENDENCIA para evitar cambios abruptos entre frames
    if pos >= 20:  # Necesitamos suficientes datos para identificar estructura
        try:
            # Obtener la tendencia anterior del frame previo si existe
            previous_trend = None
            if pos > start_pos:
                # Buscar la tendencia del frame anterior en el historial global
                previous_frame_pos = pos - 1
                if previous_frame_pos in global_trend_history:
                    previous_trend = global_trend_history[previous_frame_pos]
                    print(f"   🔍 Tendencia anterior del frame {previous_frame_pos}: {previous_trend}")
            
            # Analizar solo las velas hasta la posición actual del frame
            current_df = df_5m.iloc[:pos]  # Solo velas hasta la posición actual
            
            trend_result = market_analysis.detect_trend(current_df, method='structural')
            
            # Obtener el valor de tendencia actual (última vela analizada)
            current_trend = trend_result['trend'].iloc[-1]
            
            # Convertir a valores -1, 0, 1 según especificación del usuario
            if current_trend > 0.5:
                new_trend = 1  # Alcista
            elif current_trend < -0.5:
                new_trend = -1  # Bajista
            else:
                new_trend = 0  # Lateral
            
            # IMPLEMENTAR LÓGICA DE CONTINUIDAD: Solo cambiar tendencia si hay confirmación clara
            if previous_trend is not None:
                # Si hay tendencia anterior, aplicar lógica de continuidad
                if new_trend == previous_trend:
                    # Confirmación: mantener la misma tendencia
                    base_trend = new_trend
                    print(f"   ✅ Confirmación: Manteniendo tendencia {base_trend}")
                elif abs(new_trend - previous_trend) == 2:
                    # Cambio drástico (de -1 a 1 o viceversa): requerir confirmación adicional
                    # Usar análisis de precio para confirmar el cambio
                    price_confirmation = analyze_simple_price_trend(window_df)
                    if price_confirmation == new_trend:
                        base_trend = new_trend
                        print(f"   🔄 Cambio confirmado: {previous_trend} → {base_trend}")
                    else:
                        base_trend = previous_trend
                        print(f"   ⚠️ Cambio no confirmado: Manteniendo tendencia anterior {base_trend}")
                else:
                    # Cambio menor (de 0 a 1/-1 o viceversa): permitir cambio gradual
                    base_trend = new_trend
                    print(f"   🔄 Cambio gradual: {previous_trend} → {base_trend}")
            else:
                # Primer frame: usar la tendencia detectada
                base_trend = new_trend
                print(f"   🆕 Primer frame: Estableciendo tendencia {base_trend}")
            
            print(f"   🔍 SMC detectó: Tendencia={new_trend}, Aplicando: {base_trend}")
            print(f"   📊 Analizando {len(current_df)} velas hasta posición {pos} con método 'structural'")
            print(f"   📊 Última vela analizada: {current_df.index[-1]}")
            
        except Exception as e:
            print(f"   ⚠️ Error en SMC, usando análisis simple: {e}")
            # Fallback a análisis simple si SMC falla
            base_trend = analyze_simple_price_trend(window_df)
    else:
        base_trend = 0
    
    # Crear tendencia con CONTINUIDAD TEMPORAL usando diccionario global
    # Almacenar la tendencia por posición de frame, no por vela individual
    
    trend_values = []
    
    # Almacenar la tendencia actual en el historial global por posición de frame
    global_trend_history[pos] = base_trend
    
    # Aplicar la misma tendencia a todas las velas del frame actual
    for i, candle_index in enumerate(window_df.index):
        trend_values.append(base_trend)
    
    trend_data = pd.DataFrame({'trend': trend_values}, index=window_df.index)
    
    # Debug: mostrar tendencia SMC actual
    print(f"   🔍 SMC detectó: Tendencia={base_trend}")
    print(f"   📊 Aplicando tendencia {base_trend} a todas las velas del frame actual")
    print(f"   📊 Historial global: {len(global_trend_history)} frames analizados")
    
    # Crear subplots: Candlesticks (67%), MACD (17%), RSI (16%)
    fig = sp.make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.67, 0.17, 0.16],
        subplot_titles=('', 'MACD', 'RSI')
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

    # Agregar indicador de tendencia de 5M directamente en el gráfico de velas
    current_trend = trend_data['trend'].iloc[-1] if len(trend_data) > 0 else 0
    
    # Determinar el tipo de tendencia basado en el valor
    if current_trend > 0.3:
        trend_type_5m = "5M:ALCISTA"
        trend_color_5m = "lime"
    elif current_trend < -0.3:
        trend_type_5m = "5M:BAJISTA"
        trend_color_5m = "red"
    else:
        trend_type_5m = "5M:LATERAL"
        trend_color_5m = "gray"
    
    # Agregar anotación de tendencia 5M en la parte inferior izquierda del gráfico
    fig.add_annotation(
        x=window_df.index[0],
        y=window_df['low'].min(),
        text=trend_type_5m,
        showarrow=False,
        font=dict(size=12, color=trend_color_5m, weight='bold'),
        bgcolor="rgba(0,0,0,0.8)",
        bordercolor=trend_color_5m,
        borderwidth=1,
        xanchor="left",
        yanchor="bottom",
        xshift=10,
        yshift=-80
    )
    
    # Agregar indicador de tendencia de 15M en la parte inferior derecha del gráfico
    # Calcular tendencia de 15M basada en los datos agregados
    try:
        # Encontrar la posición correspondiente en los datos de 15M
        current_time = window_df.index[-1]
        # Buscar la vela de 15M más cercana
        closest_15m_idx = None
        for i, time_15m in enumerate(df_15m.index):
            if pd.to_datetime(time_15m) >= pd.to_datetime(current_time):
                closest_15m_idx = i
                break
        
        if closest_15m_idx is not None and closest_15m_idx < len(df_15m):
            # Analizar tendencia de 15M usando las velas hasta la posición actual
            current_df_15m = df_15m.iloc[:closest_15m_idx + 1]
            if len(current_df_15m) >= 20:
                trend_result_15m = market_analysis.detect_trend(current_df_15m, method='structural')
                current_trend_15m = trend_result_15m['trend'].iloc[-1]
                
                # Determinar el tipo de tendencia de 15M
                if current_trend_15m > 0.5:
                    trend_type_15m = "15M:ALCISTA"
                    trend_color_15m = "cyan"
                elif current_trend_15m < -0.5:
                    trend_type_15m = "15M:BAJISTA"
                    trend_color_15m = "magenta"
                else:
                    trend_type_15m = "15M:LATERAL"
                    trend_color_15m = "gray"
                
                # Agregar anotación de tendencia 15M debajo de la de 5M en la parte izquierda
                # NOTA: trend_type_15m puede ser actualizado con sufijo _ALCISTA/_BAJISTA
                fig.add_annotation(
                    x=window_df.index[0],
                    y=window_df['low'].min(),
                    text=trend_type_15m,
                    showarrow=False,
                    font=dict(size=12, color=trend_color_15m, weight='bold'),
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor=trend_color_15m,
                    borderwidth=1,
                    xanchor="left",
                    yanchor="bottom",
                    xshift=10,
                    yshift=-100
                )
                
                print(f"   🔍 15M detectó: Tendencia={current_trend_15m:.2f} → {trend_type_15m}")
            else:
                trend_type_15m = "15M:NA"
                print(f"   ⚠️ Insuficientes datos para 15M: {len(current_df_15m)} velas")
        else:
            trend_type_15m = "15M:NA"
            print(f"   ⚠️ No se pudo mapear tiempo 5M a 15M")
             
    except Exception as e:
        print(f"   ⚠️ Error calculando tendencia 15M: {e}")
        trend_type_15m = "15M:ERROR"
     
    # Calcular tendencia de 1H
    try:
        # Encontrar la posición correspondiente en los datos de 1H
        current_time = window_df.index[-1]
        # Buscar la vela de 1H más cercana
        closest_1h_idx = None
        for i, time_1h in enumerate(df_1h.index):
            if pd.to_datetime(time_1h) >= pd.to_datetime(current_time):
                closest_1h_idx = i
                break
        
        if closest_1h_idx is not None and closest_1h_idx < len(df_1h):
            # Analizar tendencia de 1H usando las velas hasta la posición actual
            current_df_1h = df_1h.iloc[:closest_1h_idx + 1]
            if len(current_df_1h) >= 20:
                trend_result_1h = market_analysis.detect_trend(current_df_1h, method='structural')
                current_trend_1h = trend_result_1h['trend'].iloc[-1]
                
                # Determinar el tipo de tendencia de 1H
                if current_trend_1h > 0.5:
                    trend_type_1h = "1H:ALCISTA"
                    trend_color_1h = "blue"
                elif current_trend_1h < -0.5:
                    trend_type_1h = "1H:BAJISTA"
                    trend_color_1h = "purple"
                else:
                    trend_type_1h = "1H:LATERAL"
                    trend_color_1h = "gray"
                
                # Agregar anotación de tendencia 1H debajo de la de 15M
                # NOTA: trend_type_1h puede ser actualizado con sufijo _ALCISTA/_BAJISTA
                fig.add_annotation(
                    x=window_df.index[0],
                    y=window_df['low'].min(),
                    text=trend_type_1h,
                    showarrow=False,
                    font=dict(size=12, color=trend_color_1h, weight='bold'),
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor=trend_color_1h,
                    borderwidth=1,
                    xanchor="left",
                    yanchor="bottom",
                    xshift=10,
                    yshift=-120
                )
                
                print(f"   🔍 1H detectó: Tendencia={current_trend_1h:.2f} → {trend_type_1h}")
            else:
                trend_type_1h = "1H:NA"
                print(f"   ⚠️ Insuficientes datos para 1H: {len(current_df_1h)} velas")
        else:
            trend_type_1h = "1H:NA"
            print(f"   ⚠️ No se pudo mapear tiempo 5M a 1H")
            
    except Exception as e:
        print(f"   ⚠️ Error calculando tendencia 1H: {e}")
        trend_type_1h = "1H:ERROR"
     
    # Calcular tendencia de 4H
    try:
        # Encontrar la posición correspondiente en los datos de 4H
        current_time = window_df.index[-1]
        # Buscar la vela de 4H más cercana
        closest_4h_idx = None
        for i, time_4h in enumerate(df_4h.index):
            if pd.to_datetime(time_4h) >= pd.to_datetime(current_time):
                closest_4h_idx = i
                break
        
        if closest_4h_idx is not None and closest_4h_idx < len(df_4h):
            # Analizar tendencia de 4H usando las velas hasta la posición actual
            current_df_4h = df_4h.iloc[:closest_4h_idx + 1]
            if len(current_df_4h) >= 20:
                trend_result_4h = market_analysis.detect_trend(current_df_4h, method='structural')
                current_trend_4h = trend_result_4h['trend'].iloc[-1]
                
                # Determinar el tipo de tendencia de 4H
                if current_trend_4h > 0.5:
                    trend_type_4h = "4H:ALCISTA"
                    trend_color_4h = "darkblue"
                elif current_trend_4h < -0.5:
                    trend_type_4h = "4H:BAJISTA"
                    trend_color_4h = "darkred"
                else:
                    trend_type_4h = "4H:LATERAL"
                    trend_color_4h = "gray"
                
                # Agregar anotación de tendencia 4H debajo de la de 1H
                # NOTA: trend_type_4h puede ser actualizado con sufijo _ALCISTA/_BAJISTA
                fig.add_annotation(
                    x=window_df.index[0],
                    y=window_df['low'].min(),
                    text=trend_type_4h,
                    showarrow=False,
                    font=dict(size=12, color=trend_color_4h, weight='bold'),
                    bgcolor="rgba(0,0,0,0.8)",
                    bordercolor=trend_color_4h,
                    borderwidth=1,
                    xanchor="left",
                    yanchor="bottom",
                    xshift=10,
                    yshift=-140
                )
                
                print(f"   🔍 4H detectó: Tendencia={current_trend_4h:.2f} → {trend_type_4h}")
            else:
                trend_type_4h = "4H:NA"
                print(f"   ⚠️ Insuficientes datos para 4H: {len(current_df_4h)} velas")
        else:
            trend_type_4h = "4H:NA"
            print(f"   ⚠️ No se pudo mapear tiempo 5M a 4H")
            
    except Exception as e:
        print(f"   ⚠️ Error calculando tendencia 4H: {e}")
        trend_type_4h = "4H:ERROR"
    
    # MEJORA: Verificar si las tendencias de 15M, 1H y 4H son idénticas y agregar sufijos
    try:
        # Solo procesar si tenemos tendencias válidas (no NA ni ERROR)
        valid_trends = []
        if 'trend_type_15m' in locals() and not trend_type_15m.endswith(('NA', 'ERROR')):
            valid_trends.append(('15M', trend_type_15m, current_trend_15m))
        if 'trend_type_1h' in locals() and not trend_type_1h.endswith(('NA', 'ERROR')):
            valid_trends.append(('1H', trend_type_1h, current_trend_1h))
        if 'trend_type_4h' in locals() and not trend_type_4h.endswith(('NA', 'ERROR')):
            valid_trends.append(('4H', trend_type_4h, current_trend_4h))
        
        # Verificar si hay al menos 2 tendencias válidas para comparar
        if len(valid_trends) >= 2:
            # Extraer solo los valores de tendencia (-1, 0, 1)
            trend_values = [trend[2] for trend in valid_trends]
            
            # Verificar si todas las tendencias son iguales y no son laterales (0)
            if len(set(trend_values)) == 1 and trend_values[0] != 0:
                # Todas las tendencias son idénticas y no son laterales
                if trend_values[0] > 0:
                    # Todas son alcistas
                    suffix = "_ALCISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son ALCISTAS → Agregando sufijo {suffix}")
                else:
                    # Todas son bajistas
                    suffix = "_BAJISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son BAJISTAS → Agregando sufijo {suffix}")
                
                # Aplicar sufijo a todas las tendencias válidas
                for timeframe, trend_type, trend_value in valid_trends:
                    if timeframe == '15M':
                        trend_type_15m = trend_type + suffix
                    elif timeframe == '1H':
                        trend_type_1h = trend_type + suffix
                    elif timeframe == '4H':
                        trend_type_4h = trend_type + suffix
            else:
                print(f"   📊 Tendencias mixtas: 15M={trend_values[0] if len(trend_values) > 0 else 'N/A'}, 1H={trend_values[1] if len(trend_values) > 1 else 'N/A'}, 4H={trend_values[2] if len(trend_values) > 2 else 'N/A'}")
        else:
            print(f"   ⚠️ Insuficientes tendencias válidas para comparar: {len(valid_trends)}")
            
    except Exception as e:
        print(f"   ⚠️ Error en análisis de confirmación múltiple: {e}")
    
    # Agregar indicadores SMC al gráfico principal
    # Crear datos simulados para los indicadores SMC (en un caso real vendrían de tu análisis)
    fvg_data = pd.DataFrame({
        'FVG': [1 if i % 20 == 0 else np.nan for i in range(len(window_df))],
        'Top': window_df['high'] * 1.001,
        'Bottom': window_df['low'] * 0.999,
        'MitigatedIndex': [i + 10 if i % 20 == 0 else 0 for i in range(len(window_df))]
    }, index=window_df.index)
    
    # Crear datos para swing highs/lows
    swing_highs_levels = []
    for i in range(len(window_df)):
        if i % 15 == 0:
            swing_highs_levels.append(window_df['high'].iloc[i])
        elif i % 15 == 7:
            swing_highs_levels.append(window_df['low'].iloc[i])
        else:
            swing_highs_levels.append(np.nan)
    
    swing_highs_lows_data = pd.DataFrame({
        'HighLow': [1 if i % 15 == 0 else (-1 if i % 15 == 7 else np.nan) for i in range(len(window_df))],
        'Level': swing_highs_levels
    }, index=window_df.index)
    
    # Crear datos para BOS/CHOCH
    bos_choch_levels = []
    for i in range(len(window_df)):
        if i % 25 == 0:
            bos_choch_levels.append(window_df['high'].iloc[i])
        elif i % 25 == 12:
            bos_choch_levels.append(window_df['low'].iloc[i])
        else:
            bos_choch_levels.append(np.nan)
    
    bos_choch_data = pd.DataFrame({
        'BOS': [1 if i % 25 == 0 else np.nan for i in range(len(window_df))],
        'CHOCH': [1 if i % 25 == 12 else np.nan for i in range(len(window_df))],
        'Level': bos_choch_levels,
        'BrokenIndex': [i + 8 if i % 25 == 0 or i % 25 == 12 else 0 for i in range(len(window_df))]
    }, index=window_df.index)
    
    ob_data = pd.DataFrame({
        'OB': [1 if i % 30 == 0 else (-1 if i % 30 == 15 else np.nan) for i in range(len(window_df))],
        'Top': window_df['high'] * 1.002,
        'Bottom': window_df['low'] * 0.998,
        'MitigatedIndex': [i + 12 if i % 30 == 0 or i % 30 == 15 else 0 for i in range(len(window_df))],
        'OBVolume': [1000000 + i * 10000 for i in range(len(window_df))],
        'Percentage': [85 + i % 10 for i in range(len(window_df))]
    }, index=window_df.index)
    
    # Crear datos para liquidez
    liquidity_levels = []
    for i in range(len(window_df)):
        if i % 18 == 0:
            liquidity_levels.append(window_df['high'].iloc[i] * 1.001)
        else:
            liquidity_levels.append(np.nan)
    
    liquidity_data = pd.DataFrame({
        'Liquidity': [1 if i % 18 == 0 else np.nan for i in range(len(window_df))],
        'Level': liquidity_levels,
        'End': [i + 6 if i % 18 == 0 else 0 for i in range(len(window_df))],
        'Swept': [i + 3 if i % 18 == 0 else 0 for i in range(len(window_df))]
    }, index=window_df.index)
    
    # Crear datos para máximos y mínimos previos
    prev_high_levels = []
    prev_low_levels = []
    for i in range(len(window_df)):
        if i % 22 == 0:
            prev_high_levels.append(window_df['high'].max())
        else:
            prev_high_levels.append(np.nan)
        
        if i % 22 == 11:
            prev_low_levels.append(window_df['low'].min())
        else:
            prev_low_levels.append(np.nan)
    
    previous_high_low_data = pd.DataFrame({
        'PreviousHigh': prev_high_levels,
        'PreviousLow': prev_low_levels
    }, index=window_df.index)
    
    sessions = pd.DataFrame({
        'Active': [1 if i % 40 == 0 else 0 for i in range(len(window_df))],
        'High': window_df['high'] * 1.003,
        'Low': window_df['low'] * 0.997
    }, index=window_df.index)
    
    retracements = pd.DataFrame({
        'Direction': [1 if i % 35 == 0 else (-1 if i % 35 == 17 else 0) for i in range(len(window_df))],
        'CurrentRetracement%': [23.6 + i % 20 for i in range(len(window_df))],
        'DeepestRetracement%': [38.2 + i % 30 for i in range(len(window_df))]
    }, index=window_df.index)
    
    # Dibujar todos los indicadores SMC
    add_FVG(fig, window_df, fvg_data)
    add_swing_highs_lows(fig, window_df, swing_highs_lows_data)
    add_bos_choch(fig, window_df, bos_choch_data)
    add_OB(fig, window_df, ob_data)
    add_liquidity(fig, window_df, liquidity_data)
    add_previous_high_low(fig, window_df, previous_high_low_data)
    add_sessions(fig, window_df, sessions)
    add_retracements(fig, window_df, retracements)
    

    
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
        margin=dict(l=0, r=0, b=50, t=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(12, 14, 18, 1)",
        font=dict(color="white"),
        width=800,
        height=600  # Altura para 3 subplots
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
    
    # MEJORA: Renombrar archivo según confirmación múltiple de tendencias Y señales de trading
    base_filename = f"frame_{pos:04d}"
    
    # Detectar señales de trading usando la misma lógica que prueba_icc.py
    trading_signals = detect_trading_signals_icc(window_df, df_1h, df_4h)
    
    # Verificar si hay confirmación múltiple para renombrar el archivo
    file_suffix = ""
    try:
        # Solo procesar si tenemos tendencias válidas (no NA ni ERROR)
        valid_trends = []
        if 'trend_type_15m' in locals() and not trend_type_15m.endswith(('NA', 'ERROR')):
            valid_trends.append(('15M', trend_type_15m, current_trend_15m))
        if 'trend_type_1h' in locals() and not trend_type_1h.endswith(('NA', 'ERROR')):
            valid_trends.append(('1H', trend_type_1h, current_trend_1h))
        if 'trend_type_4h' in locals() and not trend_type_4h.endswith(('NA', 'ERROR')):
            valid_trends.append(('4H', trend_type_4h, current_trend_4h))
        
        # PRIORIDAD 1: Señales de trading
        if trading_signals:
            for signal in trading_signals:
                if signal['type'] == 'COMPRA':
                    file_suffix = "_COMPRA"
                    print(f"   🎯 SEÑAL DE COMPRA DETECTADA: {signal['reason']} → Archivo: {base_filename}{file_suffix}.png")
                    break
                elif signal['type'] == 'VENTA':
                    file_suffix = "_VENTA"
                    print(f"   🎯 SEÑAL DE VENTA DETECTADA: {signal['reason']} → Archivo: {base_filename}{file_suffix}.png")
                    break
        
        # PRIORIDAD 2: Confirmación múltiple de tendencias (solo si no hay señales de trading)
        elif len(valid_trends) >= 2:
            # Extraer solo los valores de tendencia (-1, 0, 1)
            trend_values = [trend[2] for trend in valid_trends]
            
            # Verificar si todas las tendencias son iguales y no son laterales (0)
            if len(set(trend_values)) == 1 and trend_values[0] != 0:
                # Todas las tendencias son idénticas y no son laterales
                if trend_values[0] > 0:
                    # Todas son alcistas
                    file_suffix = "_ALCISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son ALCISTAS → Archivo: {base_filename}{file_suffix}.png")
                else:
                    # Todas son bajistas
                    file_suffix = "_BAJISTA"
                    print(f"   🎯 CONFIRMACIÓN MÚLTIPLE: Todas las tendencias son BAJISTAS → Archivo: {base_filename}{file_suffix}.png")
            else:
                print(f"   📊 Tendencias mixtas: No hay confirmación múltiple para renombrar archivo")
        else:
            print(f"   ⚠️ Insuficientes tendencias válidas para confirmación múltiple: {len(valid_trends)}")
            
    except Exception as e:
        print(f"   ⚠️ Error en análisis de confirmación múltiple para renombrar: {e}")
    
    # Crear nombre final del archivo
    frame_filename = f"{frames_dir}/{base_filename}{file_suffix}.png"
    
    # Guardar frame como PNG
    try:
        fig.write_image(frame_filename, width=800, height=600)
        
        # Mostrar información consolidada del frame
        current_trend = trend_data['trend'].iloc[-1] if len(trend_data) > 0 else 0
        print(f"✅ Frame {pos} guardado: {frame_filename}")
        print(f"   📊 Resumen del frame:")
        print(f"      • 5M: Tendencia: {current_trend:.2f}")
        print(f"      • 15M: Tendencia: {trend_type_15m if 'trend_type_15m' in locals() else 'N/A'}")
        print(f"      • 1H: Tendencia: {trend_type_1h if 'trend_type_1h' in locals() else 'N/A'}")
        print(f"      • 4H: Tendencia: {trend_type_4h if 'trend_type_4h' in locals() else 'N/A'}")
        
        print(f"   🎯 Progreso: {pos - start_pos + 1}/{len(df_5m) - start_pos} frames completados")
        
    except Exception as e:
        print(f"❌ Frame en posición {pos} falló: {e}")
        print(f"   🔄 Continuando con el siguiente frame...")

end_time = datetime.datetime.now()
print(f"✅ Frames PNG con CANDLESTICKS, MACD y RSI guardados en: {frames_dir}/")
print(f"📊 Total de frames generados: {len(df_5m) - start_pos}")
print(f"⏱️ Tiempo total de ejecución: {end_time - start_time}")
print("=" * 80)

# Resumen del análisis simplificado
print(f"\n🔍 RESUMEN DEL ANÁLISIS SIMPLIFICADO:")
print(f"   📅 Frames analizados: {start_pos} a {len(df_5m)} (últimos {len(df_5m) - start_pos} frames)")
print(f"   ⏰ Ventana de análisis: {window} velas por frame")
print(f"   📊 Temporalidad procesada:")
print(f"      • 5M: Últimas 500 velas del CSV (datos principales para visualización)")
print(f"      • 15M: Últimas 500 velas agregadas (datos para análisis de tendencia)")
print(f"      • 1H: Últimas 500 velas agregadas (datos para análisis de tendencia)")
print(f"      • 4H: Últimas 500 velas agregadas (datos para análisis de tendencia)")
print(f"      • Visualización: Últimas 100 velas por frame (5M)")
print(f"   🎯 Cada frame incluye:")
print(f"      • Candlesticks principales con indicadores SMC (datos 5M)")
print(f"      • Tendencia 5M en esquina inferior izquierda")
print(f"      • Tendencia 15M debajo de 5M")
print(f"      • Tendencia 1H debajo de 15M")
print(f"      • Tendencia 4H debajo de 1H")
print(f"      • MACD y RSI en paneles separados")
print(f"      • Indicadores SMC (FVG, Order Blocks, Swing Points)")
print(f"   📈 Lógica SMC implementada:")
print(f"      • Análisis múltiple: 5M (visualización) + 15M, 1H, 4H (tendencias)")
print(f"      • 5M: market_analysis_lib.detect_trend('structural') para estructura")
print(f"      • 15M, 1H, 4H: market_analysis_lib.detect_trend('structural') para tendencias")
print(f"      • Indicadores técnicos estándar (MACD, RSI)")
print(f"      • Fallback a análisis simple si SMC falla")