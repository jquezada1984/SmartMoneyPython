import pandas as pd
import plotly.graph_objects as go
import sys
import os
from binance.client import Client
from datetime import datetime
import numpy as np
import time
import imageio
from io import BytesIO
from PIL import Image
from tqdm import tqdm

sys.path.append(os.path.abspath("../"))
from smartmoneyconcepts.smc import smc

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    Calcula MACD (Moving Average Convergence Divergence)
    
    parámetros:
    df: DataFrame - datos OHLC
    fast: int - período EMA rápida
    slow: int - período EMA lenta
    signal: int - período EMA señal
    
    retorna:
    DataFrame con MACD, Signal, Histogram
    """
    # Calcular EMAs
    ema_fast = df['close'].ewm(span=fast).mean()
    ema_slow = df['close'].ewm(span=slow).mean()
    
    # MACD línea
    macd_line = ema_fast - ema_slow
    
    # Línea de señal
    signal_line = macd_line.ewm(span=signal).mean()
    
    # Histograma
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'MACD': macd_line,
        'Signal': signal_line,
        'Histogram': histogram
    })

def calculate_rsi(df, period=14):
    """
    Calcula RSI (Relative Strength Index)
    
    parámetros:
    df: DataFrame - datos OHLC
    period: int - período para el cálculo
    
    retorna:
    Series con valores RSI
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def add_FVG(fig, df, fvg_data):
    for i in range(len(fvg_data["FVG"])):
        if not np.isnan(fvg_data["FVG"][i]):
            x1 = int(
                fvg_data["MitigatedIndex"][i]
                if fvg_data["MitigatedIndex"][i] != 0
                else len(df) - 1
            )
            fig.add_shape(
                # filled Rectangle
                type="rect",
                x0=df.index[i],
                y0=fvg_data["Top"][i],
                x1=df.index[x1],
                y1=fvg_data["Bottom"][i],
                line=dict(
                    width=0,
                ),
                fillcolor="yellow",
                opacity=0.2,
                xref="x",
                yref="y"
            )
            mid_x = round((i + x1) / 2)
            mid_y = (fvg_data["Top"][i] + fvg_data["Bottom"][i]) / 2
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="FVG",
                    textposition="middle center",
                    textfont=dict(color='rgba(255, 255, 255, 0.4)', size=8),
                ),
                row=1, col=1
            )
    return fig


def add_swing_highs_lows(fig, df, swing_highs_lows_data):
    indexs = []
    level = []
    for i in range(len(swing_highs_lows_data)):
        if not np.isnan(swing_highs_lows_data["HighLow"][i]):
            indexs.append(i)
            level.append(swing_highs_lows_data["Level"][i])

    # plot these lines on a graph
    for i in range(len(indexs) - 1):
        fig.add_trace(
            go.Scatter(
                x=[df.index[indexs[i]], df.index[indexs[i + 1]]],
                y=[level[i], level[i + 1]],
                mode="lines",
                line=dict(
                    color=(
                        "rgba(0, 128, 0, 0.2)"
                        if swing_highs_lows_data["HighLow"][indexs[i]] == -1
                        else "rgba(255, 0, 0, 0.2)"
                    ),
                ),
            ),
            row=1, col=1
        )

    return fig


def add_bos_choch(fig, df, bos_choch_data):
    for i in range(len(bos_choch_data["BOS"])):
        if not np.isnan(bos_choch_data["BOS"][i]):
            # add a label to this line
            mid_x = round((i + int(bos_choch_data["BrokenIndex"][i])) / 2)
            mid_y = bos_choch_data["Level"][i]
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[int(bos_choch_data["BrokenIndex"][i])]],
                    y=[bos_choch_data["Level"][i], bos_choch_data["Level"][i]],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 165, 0, 0.2)",
                    ),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="BOS",
                    textposition="top center" if bos_choch_data["BOS"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                ),
                row=1, col=1
            )
        if not np.isnan(bos_choch_data["CHOCH"][i]):
            # add a label to this line
            mid_x = round((i + int(bos_choch_data["BrokenIndex"][i])) / 2)
            mid_y = bos_choch_data["Level"][i]
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[int(bos_choch_data["BrokenIndex"][i])]],
                    y=[bos_choch_data["Level"][i], bos_choch_data["Level"][i]],
                    mode="lines",
                    line=dict(
                        color="rgba(0, 0, 255, 0.2)",
                    ),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="CHOCH",
                    textposition="top center" if bos_choch_data["CHOCH"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(0, 0, 255, 0.4)", size=8),
                ),
                row=1, col=1
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

    for i in range(len(ob_data["OB"])):
        if ob_data["OB"][i] == 1:
            x1 = int(
                ob_data["MitigatedIndex"][i]
                if ob_data["MitigatedIndex"][i] != 0
                else len(df) - 1
            )
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_data["Bottom"][i],
                x1=df.index[x1],
                y1=ob_data["Top"][i],
                line=dict(color="Purple"),
                fillcolor="Purple",
                opacity=0.2,
                name="Bullish OB",
                legendgroup="bullish ob",
                showlegend=True,
            )

            if ob_data["MitigatedIndex"][i] > 0:
                x_center = df.index[int(i + (ob_data["MitigatedIndex"][i] - i) / 2)]
            else:
                x_center = df.index[int(i + (len(df) - i) / 2)]

            y_center = (ob_data["Bottom"][i] + ob_data["Top"][i]) / 2
            volume_text = format_volume(ob_data["OBVolume"][i])
            # Add annotation text
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"][i]}%)'

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

    for i in range(len(ob_data["OB"])):
        if ob_data["OB"][i] == -1:
            x1 = int(
                ob_data["MitigatedIndex"][i]
                if ob_data["MitigatedIndex"][i] != 0
                else len(df) - 1
            )
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_data["Bottom"][i],
                x1=df.index[x1],
                y1=ob_data["Top"][i],
                line=dict(color="Purple"),
                fillcolor="Purple",
                opacity=0.2,
                name="Bearish OB",
                legendgroup="bearish ob",
                showlegend=True,
            )

            if ob_data["MitigatedIndex"][i] > 0:
                x_center = df.index[int(i + (ob_data["MitigatedIndex"][i] - i) / 2)]
            else:
                x_center = df.index[int(i + (len(df) - i) / 2)]

            y_center = (ob_data["Bottom"][i] + ob_data["Top"][i]) / 2
            volume_text = format_volume(ob_data["OBVolume"][i])
            # Add annotation text
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"][i]}%)'

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
    # draw a line horizontally for each liquidity level
    for i in range(len(liquidity_data["Liquidity"])):
        if not np.isnan(liquidity_data["Liquidity"][i]):
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[int(liquidity_data["End"][i])]],
                    y=[liquidity_data["Level"][i], liquidity_data["Level"][i]],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 165, 0, 0.2)",
                    ),
                ),
                row=1, col=1
            )
            mid_x = round((i + int(liquidity_data["End"][i])) / 2)
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[liquidity_data["Level"][i]],
                    mode="text",
                    text="Liquidity",
                    textposition="top center" if liquidity_data["Liquidity"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                ),
                row=1, col=1
            )
        if liquidity_data["Swept"][i] != 0 and not np.isnan(liquidity_data["Swept"][i]):
            # draw a red line between the end and the swept point
            fig.add_trace(
                go.Scatter(
                    x=[
                        df.index[int(liquidity_data["End"][i])],
                        df.index[int(liquidity_data["Swept"][i])],
                    ],
                    y=[
                        liquidity_data["Level"][i],
                        (
                            df["high"].iloc[int(liquidity_data["Swept"][i])]
                            if liquidity_data["Liquidity"][i] == 1
                            else df["low"].iloc[int(liquidity_data["Swept"][i])]
                        ),
                    ],
                    mode="lines",
                    line=dict(
                        color="rgba(255, 0, 0, 0.2)",
                    ),
                ),
                row=1, col=1
            )
            mid_x = round((i + int(liquidity_data["Swept"][i])) / 2)
            mid_y = (
                liquidity_data["Level"][i]
                + (
                    df["high"].iloc[int(liquidity_data["Swept"][i])]
                    if liquidity_data["Liquidity"][i] == 1
                    else df["low"].iloc[int(liquidity_data["Swept"][i])]
                )
            ) / 2
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="Liquidity Swept",
                    textposition="top center" if liquidity_data["Liquidity"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 0, 0, 0.4)", size=8),
                ),
                row=1, col=1
            )
    return fig


def add_previous_high_low(fig, df, previous_high_low_data):
    high = previous_high_low_data["PreviousHigh"]
    low = previous_high_low_data["PreviousLow"]

    # create a list of all the different high levels and their indexes
    high_levels = []
    high_indexes = []
    for i in range(len(high)):
        if not np.isnan(high[i]) and high[i] != (high_levels[-1] if len(high_levels) > 0 else None):
            high_levels.append(high[i])
            high_indexes.append(i)

    low_levels = [] 
    low_indexes = []
    for i in range(len(low)):
        if not np.isnan(low[i]) and low[i] != (low_levels[-1] if len(low_levels) > 0 else None):
            low_levels.append(low[i])
            low_indexes.append(i)

    # plot these lines on a graph
    for i in range(len(high_indexes)-1):
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

    for i in range(len(low_indexes)-1):
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
    for i in range(len(sessions["Active"])-1):
        if sessions["Active"][i] == 1:
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=sessions["Low"][i],
                x1=df.index[i + 1],
                y1=sessions["High"][i],
                line=dict(
                    width=0,
                ),
                fillcolor="#16866E",
                opacity=0.2,
            )
    return fig


def add_retracements(fig, df, retracements):
    for i in range(len(retracements)):
        if (
            (
                (
                    retracements["Direction"].iloc[i + 1]
                    if i < len(retracements) - 1
                    else 0
                )
                != retracements["Direction"].iloc[i]
                or i == len(retracements) - 1
            )
            and retracements["Direction"].iloc[i] != 0
            and (
                retracements["Direction"].iloc[i + 1]
                if i < len(retracements) - 1
                else retracements["Direction"].iloc[i]
            )
            != 0
        ):
            fig.add_annotation(
                x=df.index[i],
                y=(
                    df["high"].iloc[i]
                    if retracements["Direction"].iloc[i] == -1
                    else df["low"].iloc[i]
                ),
                xref="x",
                yref="y",
                text=f"C:{retracements['CurrentRetracement%'].iloc[i]}%<br>D:{retracements['DeepestRetracement%'].iloc[i]}%",
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
    return fig


def add_equal_highs_lows(fig, df, equal_highs_lows_data):
    """
    Agrega visualización de Equal Highs/Lows al gráfico
    """
    # Procesa Equal Highs
    high_indices = np.where(equal_highs_lows_data["EqualLevel"] == 1)[0]
    if len(high_indices) > 0:
        # Agrupa por nivel para evitar duplicados
        levels = {}
        for idx in high_indices:
            level = equal_highs_lows_data["Level"].iloc[idx]
            count = equal_highs_lows_data["Count"].iloc[idx]
            strength = equal_highs_lows_data["Strength"].iloc[idx]
            
            if level not in levels or strength > levels[level]["strength"]:
                levels[level] = {
                    "index": idx,
                    "count": count,
                    "strength": strength
                }
        
        # Dibuja líneas horizontales para cada nivel único
        for level, info in levels.items():
            fig.add_shape(
                type="line",
                x0=df.index[0],
                y0=level,
                x1=df.index[-1],
                y1=level,
                line=dict(
                    color="rgba(255, 165, 0, 0.6)",  # Naranja para equal highs
                    width=2,
                    dash="dash",
                ),
            )
            # Agrega anotación con información
            fig.add_annotation(
                x=df.index[info["index"]],
                y=level,
                xref="x",
                yref="y",
                text=f"EH<br>C:{info['count']}<br>S:{info['strength']:.1f}",
                font=dict(color="rgba(255, 165, 0, 0.8)", size=8),
                showarrow=False,
                bgcolor="rgba(0, 0, 0, 0.5)",
                bordercolor="rgba(255, 165, 0, 0.8)",
                borderwidth=1,
            )
    
    # Procesa Equal Lows
    low_indices = np.where(equal_highs_lows_data["EqualLevel"] == -1)[0]
    if len(low_indices) > 0:
        # Agrupa por nivel para evitar duplicados
        levels = {}
        for idx in low_indices:
            level = equal_highs_lows_data["Level"].iloc[idx]
            count = equal_highs_lows_data["Count"].iloc[idx]
            strength = equal_highs_lows_data["Strength"].iloc[idx]
            
            if level not in levels or strength > levels[level]["strength"]:
                levels[level] = {
                    "index": idx,
                    "count": count,
                    "strength": strength
                }
        
        # Dibuja líneas horizontales para cada nivel único
        for level, info in levels.items():
            fig.add_shape(
                type="line",
                x0=df.index[0],
                y0=level,
                x1=df.index[-1],
                y1=level,
                line=dict(
                    color="rgba(0, 255, 255, 0.6)",  # Cian para equal lows
                    width=2,
                    dash="dash",
                ),
            )
            # Agrega anotación con información
            fig.add_annotation(
                x=df.index[info["index"]],
                y=level,
                xref="x",
                yref="y",
                text=f"EL<br>C:{info['count']}<br>S:{info['strength']:.1f}",
                font=dict(color="rgba(0, 255, 255, 0.8)", size=8),
                showarrow=False,
                bgcolor="rgba(0, 0, 0, 0.5)",
                bordercolor="rgba(0, 255, 255, 0.8)",
                borderwidth=1,
            )
    
    return fig


def add_premium_discount_zones(fig, df, premium_discount_data):
    """
    Agrega visualización de Premium/Discount Zones al gráfico
    """
    # Procesa las zonas premium y discount
    premium_indices = np.where(premium_discount_data["Zone"] == 1)[0]
    discount_indices = np.where(premium_discount_data["Zone"] == -1)[0]
    neutral_indices = np.where(premium_discount_data["Zone"] == 0)[0]
    
    # Dibuja líneas horizontales para los rangos cuando están disponibles
    valid_ranges = premium_discount_data.dropna(subset=["RangeHigh", "RangeLow", "MidPoint"])
    
    if len(valid_ranges) > 0:
        # Usa el rango más reciente para visualización
        latest_range = valid_ranges.iloc[-1]
        
        # Línea del swing high
        fig.add_shape(
            type="line",
            x0=df.index[0],
            y0=latest_range["RangeHigh"],
            x1=df.index[-1],
            y1=latest_range["RangeHigh"],
            line=dict(
                color="rgba(255, 0, 0, 0.4)",  # Rojo para swing high
                width=1,
                dash="dot",
            ),
        )
        
        # Línea del punto medio (50%)
        fig.add_shape(
            type="line",
            x0=df.index[0],
            y0=latest_range["MidPoint"],
            x1=df.index[-1],
            y1=latest_range["MidPoint"],
            line=dict(
                color="rgba(255, 255, 0, 0.6)",  # Amarillo para punto medio
                width=2,
                dash="solid",
            ),
        )
        
        # Línea del swing low
        fig.add_shape(
            type="line",
            x0=df.index[0],
            y0=latest_range["RangeLow"],
            x1=df.index[-1],
            y1=latest_range["RangeLow"],
            line=dict(
                color="rgba(0, 255, 0, 0.4)",  # Verde para swing low
                width=1,
                dash="dot",
            ),
        )
        
        # Agrega anotaciones para las zonas
        fig.add_annotation(
            x=df.index[-1],
            y=latest_range["RangeHigh"],
            xref="x",
            yref="y",
            text="Swing High",
            font=dict(color="rgba(255, 0, 0, 0.8)", size=8),
            showarrow=False,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(255, 0, 0, 0.8)",
            borderwidth=1,
        )
        
        fig.add_annotation(
            x=df.index[-1],
            y=latest_range["MidPoint"],
            xref="x",
            yref="y",
            text="50% (Mid)",
            font=dict(color="rgba(255, 255, 0, 0.8)", size=8),
            showarrow=False,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(255, 255, 0, 0.8)",
            borderwidth=1,
        )
        
        fig.add_annotation(
            x=df.index[-1],
            y=latest_range["RangeLow"],
            xref="x",
            yref="y",
            text="Swing Low",
            font=dict(color="rgba(0, 255, 0, 0.8)", size=8),
            showarrow=False,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(0, 255, 0, 0.8)",
            borderwidth=1,
        )
    
    # Agrega marcadores para las zonas actuales
    if len(premium_indices) > 0:
        latest_premium = premium_indices[-1]
        if latest_premium >= len(df) - 10:  # Solo muestra si es reciente
            fig.add_annotation(
                x=df.index[latest_premium],
                y=df["close"].iloc[latest_premium],
                xref="x",
                yref="y",
                text="PREMIUM",
                font=dict(color="rgba(255, 0, 0, 0.8)", size=10, weight="bold"),
                showarrow=True,
                arrowhead=2,
                arrowcolor="rgba(255, 0, 0, 0.8)",
                bgcolor="rgba(255, 0, 0, 0.2)",
                bordercolor="rgba(255, 0, 0, 0.8)",
                borderwidth=1,
            )
    
    if len(discount_indices) > 0:
        latest_discount = discount_indices[-1]
        if latest_discount >= len(df) - 10:  # Solo muestra si es reciente
            fig.add_annotation(
                x=df.index[latest_discount],
                y=df["close"].iloc[latest_discount],
                xref="x",
                yref="y",
                text="DISCOUNT",
                font=dict(color="rgba(0, 255, 0, 0.8)", size=10, weight="bold"),
                showarrow=True,
                arrowhead=2,
                arrowcolor="rgba(0, 255, 0, 0.8)",
                bgcolor="rgba(0, 255, 0, 0.2)",
                bordercolor="rgba(0, 255, 0, 0.8)",
                borderwidth=1,
            )
    
    return fig


def add_macd_rsi_indicators(fig, df, macd_data, rsi_data):
    """
    Agrega visualización de MACD y RSI en subplots separados como MetaTrader
    
    parámetros:
    fig: Figure - figura de plotly
    df: DataFrame - datos OHLC
    macd_data: DataFrame - datos MACD
    rsi_data: Series - datos RSI
    """
    # Crear figura con subplots separados
    from plotly.subplots import make_subplots
    
    # Crear subplots: gráfico principal (80%), MACD (10%), RSI (10%)
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.15, 0.15],
        subplot_titles=('EURUSD', 'MACD', 'RSI')
    )
    
    # Agregar velas al gráfico principal (row=1)
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color="#77dd76",
            decreasing_line_color="#ff6962",
            name="EURUSD"
        ),
        row=1, col=1
    )
    
    # Agregar MACD al segundo subplot (row=2)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=macd_data['MACD'],
            mode='lines',
            name='MACD',
            line=dict(color='rgba(0, 255, 255, 0.8)', width=1),
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=macd_data['Signal'],
            mode='lines',
            name='Signal',
            line=dict(color='rgba(255, 165, 0, 0.8)', width=1),
        ),
        row=2, col=1
    )
    
    # Histograma MACD
    colors = ['rgba(0, 255, 0, 0.6)' if val >= 0 else 'rgba(255, 0, 0, 0.6)' 
              for val in macd_data['Histogram']]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=macd_data['Histogram'],
            name='Histogram',
            marker_color=colors,
            opacity=0.6,
        ),
        row=2, col=1
    )
    
    # Agregar RSI al tercer subplot (row=3)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=rsi_data,
            mode='lines',
            name='RSI',
            line=dict(color='rgba(255, 255, 0, 0.8)', width=2),
        ),
        row=3, col=1
    )
    
    # Líneas de referencia RSI
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(255, 0, 0, 0.5)", row=3)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 0, 0, 0.5)", row=3)
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(255, 255, 255, 0.3)", row=3)
    
    # Configurar rangos de los subplots
    fig.update_yaxes(title_text="Precio", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
    
    # Ocultar títulos de subplots
    fig.update_annotations(font_size=10)
    
    return fig


# get the data
def import_data(csv_path):
    print(f"📊 Cargando datos desde archivo CSV: {csv_path}")
    
    try:
        # Leer el archivo CSV
        df = pd.read_csv(csv_path)
        print(f"✅ Archivo cargado exitosamente")
        
        # Convertir la columna datetime a índice
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        
        # Asegurar que las columnas numéricas sean float
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Eliminar filas con valores NaN
        df = df.dropna()
        
        print(f"✅ Datos procesados: {len(df)} velas de {df.index[0]} a {df.index[-1]}")
        return df
        
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {csv_path}")
        return None
    except Exception as e:
        print(f"❌ Error al cargar el archivo: {e}")
        return None


# Cargar datos desde el archivo CSV
csv_path = "tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv"
df = import_data(csv_path)

if df is None:
    print("❌ No se pudieron cargar los datos. Saliendo...")
    exit()

# Tomar solo las últimas 500 velas para el GIF
df = df.iloc[-500:]

window = 100
print(f"🎬 Preparando generación de GIF con {len(df)} velas de EURUSD (ventana de {window} velas)")
print(f"📈 Se generarán {len(df) - window} frames para el GIF")
print(f"📊 Símbolo: EURUSD | Timeframe: 5M | Datos: 2025")

def fig_to_buffer(fig):
    fig_bytes = fig.to_image(format="png")
    fig_buffer = BytesIO(fig_bytes)
    fig_image = Image.open(fig_buffer)
    return np.array(fig_image)


gif = []

print("🎨 Generando frames del GIF...")
for pos in tqdm(range(window, len(df)), desc="Generando frames", unit="frame"):
    window_df = df.iloc[pos - window : pos]

    # === CALCULAR INDICADORES TÉCNICOS ===
    # MACD y RSI para visualización
    macd_data = calculate_macd(window_df, fast=12, slow=26, signal=9)
    rsi_data = calculate_rsi(window_df, period=14)
    
    # === CALCULAR SMC ===
    fvg_data = smc.fvg(window_df, join_consecutive=True)
    swing_highs_lows_data = smc.swing_highs_lows(window_df, swing_length=5)
    bos_choch_data = smc.bos_choch(window_df, swing_highs_lows_data)
    ob_data = smc.ob(window_df, swing_highs_lows_data)
    liquidity_data = smc.liquidity(window_df, swing_highs_lows_data)
    previous_high_low_data = smc.previous_high_low(window_df, time_frame="4h")
    sessions = smc.sessions(window_df, session="London")
    retracements = smc.retracements(window_df, swing_highs_lows_data)
    equal_highs_lows_data = smc.equal_highs_lows(window_df, swing_highs_lows_data)
    premium_discount_data = smc.premium_discount_zones(window_df, swing_highs_lows_data)
    
    # === CREAR FIGURA CON SUBPLOTS ===
    # Crear figura con subplots separados
    from plotly.subplots import make_subplots
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.15, 0.15],
        subplot_titles=('EURUSD', 'MACD', 'RSI')
    )
    
    # Agregar velas al gráfico principal (row=1)
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
    
    # Agregar MACD al segundo subplot (row=2)
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=macd_data['MACD'],
            mode='lines',
            name='MACD',
            line=dict(color='rgba(0, 255, 255, 0.8)', width=1),
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=macd_data['Signal'],
            mode='lines',
            name='Signal',
            line=dict(color='rgba(255, 165, 0, 0.8)', width=1),
        ),
        row=2, col=1
    )
    
    # Histograma MACD
    colors = ['rgba(0, 255, 0, 0.6)' if val >= 0 else 'rgba(255, 0, 0, 0.6)' 
              for val in macd_data['Histogram']]
    
    fig.add_trace(
        go.Bar(
            x=window_df.index,
            y=macd_data['Histogram'],
            name='Histogram',
            marker_color=colors,
            opacity=0.6,
        ),
        row=2, col=1
    )
    
    # Agregar RSI al tercer subplot (row=3)
    fig.add_trace(
        go.Scatter(
            x=window_df.index,
            y=rsi_data,
            mode='lines',
            name='RSI',
            line=dict(color='rgba(255, 255, 0, 0.8)', width=2),
        ),
        row=3, col=1
    )
    
    # Líneas de referencia RSI
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(255, 0, 0, 0.5)", row=3)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 0, 0, 0.5)", row=3)
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(255, 255, 255, 0.3)", row=3)
    
    # === AGREGAR SMC AL GRÁFICO PRINCIPAL ===
    # Smart Money Concepts (solo en el gráfico principal - row=1)
    
    # FVG
    for i in range(len(fvg_data["FVG"])):
        if not np.isnan(fvg_data["FVG"][i]):
            x1 = int(fvg_data["MitigatedIndex"][i] if fvg_data["MitigatedIndex"][i] != 0 else len(window_df) - 1)
            fig.add_shape(
                type="rect",
                x0=window_df.index[i], y0=fvg_data["Top"][i],
                x1=window_df.index[x1], y1=fvg_data["Bottom"][i],
                line=dict(width=0),
                fillcolor="yellow", opacity=0.2,
                xref="x", yref="y"
            )
            mid_x = round((i + x1) / 2)
            mid_y = (fvg_data["Top"][i] + fvg_data["Bottom"][i]) / 2
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[mid_x]], y=[mid_y],
                    mode="text", text="FVG",
                    textposition="middle center",
                    textfont=dict(color='rgba(255, 255, 255, 0.4)', size=8),
                ),
                row=1, col=1
            )
    
    # Swing Highs/Lows
    indexs = []
    level = []
    for i in range(len(swing_highs_lows_data)):
        if not np.isnan(swing_highs_lows_data["HighLow"][i]):
            indexs.append(i)
            level.append(swing_highs_lows_data["Level"][i])
    
    for i in range(len(indexs) - 1):
        fig.add_trace(
            go.Scatter(
                x=[window_df.index[indexs[i]], window_df.index[indexs[i + 1]]],
                y=[level[i], level[i + 1]],
                mode="lines",
                line=dict(color="rgba(0, 128, 0, 0.2)" if swing_highs_lows_data["HighLow"][indexs[i]] == -1 else "rgba(255, 0, 0, 0.2)"),
            ),
            row=1, col=1
        )
    
    # BOS/CHOCH
    for i in range(len(bos_choch_data["BOS"])):
        if not np.isnan(bos_choch_data["BOS"][i]):
            mid_x = round((i + int(bos_choch_data["BrokenIndex"][i])) / 2)
            mid_y = bos_choch_data["Level"][i]
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i], window_df.index[int(bos_choch_data["BrokenIndex"][i])]],
                    y=[bos_choch_data["Level"][i], bos_choch_data["Level"][i]],
                    mode="lines",
                    line=dict(color="rgba(255, 165, 0, 0.2)"),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[mid_x]], y=[mid_y],
                    mode="text", text="BOS",
                    textposition="top center" if bos_choch_data["BOS"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                ),
                row=1, col=1
            )
        if not np.isnan(bos_choch_data["CHOCH"][i]):
            mid_x = round((i + int(bos_choch_data["BrokenIndex"][i])) / 2)
            mid_y = bos_choch_data["Level"][i]
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i], window_df.index[int(bos_choch_data["BrokenIndex"][i])]],
                    y=[bos_choch_data["Level"][i], bos_choch_data["Level"][i]],
                    mode="lines",
                    line=dict(color="rgba(0, 0, 255, 0.2)"),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[mid_x]], y=[mid_y],
                    mode="text", text="CHOCH",
                    textposition="top center" if bos_choch_data["CHOCH"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(0, 0, 255, 0.4)", size=8),
                ),
                row=1, col=1
            )
    
    # Order Blocks
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

    for i in range(len(ob_data["OB"])):
        if ob_data["OB"][i] == 1:
            x1 = int(ob_data["MitigatedIndex"][i] if ob_data["MitigatedIndex"][i] != 0 else len(window_df) - 1)
            fig.add_shape(
                type="rect",
                x0=window_df.index[i], y0=ob_data["Bottom"][i],
                x1=window_df.index[x1], y1=ob_data["Top"][i],
                line=dict(color="Purple"), fillcolor="Purple", opacity=0.2,
                xref="x", yref="y"
            )
            
            if ob_data["MitigatedIndex"][i] > 0:
                x_center = window_df.index[int(i + (ob_data["MitigatedIndex"][i] - i) / 2)]
            else:
                x_center = window_df.index[int(i + (len(window_df) - i) / 2)]

            y_center = (ob_data["Bottom"][i] + ob_data["Top"][i]) / 2
            volume_text = format_volume(ob_data["OBVolume"][i])
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"][i]}%)'

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

    for i in range(len(ob_data["OB"])):
        if ob_data["OB"][i] == -1:
            x1 = int(ob_data["MitigatedIndex"][i] if ob_data["MitigatedIndex"][i] != 0 else len(window_df) - 1)
            fig.add_shape(
                type="rect",
                x0=window_df.index[i], y0=ob_data["Bottom"][i],
                x1=window_df.index[x1], y1=ob_data["Top"][i],
                line=dict(color="Purple"), fillcolor="Purple", opacity=0.2,
                xref="x", yref="y"
            )
            
            if ob_data["MitigatedIndex"][i] > 0:
                x_center = window_df.index[int(i + (ob_data["MitigatedIndex"][i] - i) / 2)]
            else:
                x_center = window_df.index[int(i + (len(window_df) - i) / 2)]

            y_center = (ob_data["Bottom"][i] + ob_data["Top"][i]) / 2
            volume_text = format_volume(ob_data["OBVolume"][i])
            annotation_text = f'OB: {volume_text} ({ob_data["Percentage"][i]}%)'

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
    
    # Liquidity
    for i in range(len(liquidity_data["Liquidity"])):
        if not np.isnan(liquidity_data["Liquidity"][i]):
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i]], y=[liquidity_data["Level"][i]],
                    mode="markers",
                    marker=dict(
                        symbol="diamond", size=10,
                        color="rgba(255, 255, 0, 0.8)" if liquidity_data["Liquidity"][i] == 1 else "rgba(255, 0, 0, 0.8)"
                    ),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i]], y=[liquidity_data["Level"][i]],
                    mode="text",
                    text="L" if liquidity_data["Liquidity"][i] == 1 else "L",
                    textposition="top center" if liquidity_data["Liquidity"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 255, 0, 0.8)" if liquidity_data["Liquidity"][i] == 1 else "rgba(255, 0, 0, 0.8)", size=8),
                ),
                row=1, col=1
            )
    
    # Previous High/Low
    for i in range(len(previous_high_low_data["PreviousHigh"])):
        if not np.isnan(previous_high_low_data["PreviousHigh"][i]):
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i]], y=[previous_high_low_data["PreviousHigh"][i]],
                    mode="markers",
                    marker=dict(symbol="circle", size=8, color="rgba(255, 0, 0, 0.8)"),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i]], y=[previous_high_low_data["PreviousHigh"][i]],
                    mode="text", text="PH",
                    textposition="top center",
                    textfont=dict(color="rgba(255, 0, 0, 0.8)", size=8),
                ),
                row=1, col=1
            )
        if not np.isnan(previous_high_low_data["PreviousLow"][i]):
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i]], y=[previous_high_low_data["PreviousLow"][i]],
                    mode="markers",
                    marker=dict(symbol="circle", size=8, color="rgba(0, 255, 0, 0.8)"),
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[i]], y=[previous_high_low_data["PreviousLow"][i]],
                    mode="text", text="PL",
                    textposition="bottom center",
                    textfont=dict(color="rgba(0, 255, 0, 0.8)", size=8),
                ),
                row=1, col=1
            )
    
    # Sessions
    for i in range(len(sessions["Active"])-1):
        if sessions["Active"][i] == 1:
            fig.add_shape(
                type="rect",
                x0=window_df.index[i],
                y0=sessions["Low"][i],
                x1=window_df.index[i + 1],
                y1=sessions["High"][i],
                line=dict(width=0),
                fillcolor="#16866E",
                opacity=0.2,
                xref="x", yref="y"
            )
    
    # Retracements
    for i in range(len(retracements)):
        if (
            (
                (
                    retracements["Direction"].iloc[i + 1]
                    if i < len(retracements) - 1
                    else 0
                )
                != retracements["Direction"].iloc[i]
                or i == len(retracements) - 1
            )
            and retracements["Direction"].iloc[i] != 0
            and (
                retracements["Direction"].iloc[i + 1]
                if i < len(retracements) - 1
                else retracements["Direction"].iloc[i]
            )
            != 0
        ):
            fig.add_annotation(
                x=window_df.index[i],
                y=(
                    window_df["high"].iloc[i]
                    if retracements["Direction"].iloc[i] == -1
                    else window_df["low"].iloc[i]
                ),
                xref="x",
                yref="y",
                text=f"C:{retracements['CurrentRetracement%'].iloc[i]}%<br>D:{retracements['DeepestRetracement%'].iloc[i]}%",
                font=dict(color="rgba(255, 255, 255, 0.4)", size=8),
                showarrow=False,
            )
    
    # Equal Highs/Lows
    # Procesa Equal Highs
    high_indices = np.where(equal_highs_lows_data["EqualLevel"] == 1)[0]
    if len(high_indices) > 0:
        # Agrupa por nivel para evitar duplicados
        levels = {}
        for idx in high_indices:
            level = equal_highs_lows_data["Level"].iloc[idx]
            count = equal_highs_lows_data["Count"].iloc[idx]
            strength = equal_highs_lows_data["Strength"].iloc[idx]
            
            if level not in levels or strength > levels[level]["strength"]:
                levels[level] = {
                    "index": idx,
                    "count": count,
                    "strength": strength
                }
        
        # Dibuja líneas horizontales para cada nivel único
        for level, info in levels.items():
            fig.add_shape(
                type="line",
                x0=window_df.index[0],
                y0=level,
                x1=window_df.index[-1],
                y1=level,
                line=dict(
                    color="rgba(255, 165, 0, 0.6)",  # Naranja para equal highs
                    width=2,
                    dash="dash",
                ),
                xref="x", yref="y"
            )
            # Agrega anotación con información
            fig.add_annotation(
                x=window_df.index[info["index"]],
                y=level,
                xref="x",
                yref="y",
                text=f"EH<br>C:{info['count']}<br>S:{info['strength']:.1f}",
                font=dict(color="rgba(255, 165, 0, 0.8)", size=8),
                showarrow=False,
                bgcolor="rgba(0, 0, 0, 0.5)",
                bordercolor="rgba(255, 165, 0, 0.8)",
                borderwidth=1,
            )
    
    # Procesa Equal Lows
    low_indices = np.where(equal_highs_lows_data["EqualLevel"] == -1)[0]
    if len(low_indices) > 0:
        # Agrupa por nivel para evitar duplicados
        levels = {}
        for idx in low_indices:
            level = equal_highs_lows_data["Level"].iloc[idx]
            count = equal_highs_lows_data["Count"].iloc[idx]
            strength = equal_highs_lows_data["Strength"].iloc[idx]
            
            if level not in levels or strength > levels[level]["strength"]:
                levels[level] = {
                    "index": idx,
                    "count": count,
                    "strength": strength
                }
        
        # Dibuja líneas horizontales para cada nivel único
        for level, info in levels.items():
            fig.add_shape(
                type="line",
                x0=window_df.index[0],
                y0=level,
                x1=window_df.index[-1],
                y1=level,
                line=dict(
                    color="rgba(0, 255, 255, 0.6)",  # Cian para equal lows
                    width=2,
                    dash="dash",
                ),
                xref="x", yref="y"
            )
            # Agrega anotación con información
            fig.add_annotation(
                x=window_df.index[info["index"]],
                y=level,
                xref="x",
                yref="y",
                text=f"EL<br>C:{info['count']}<br>S:{info['strength']:.1f}",
                font=dict(color="rgba(0, 255, 255, 0.8)", size=8),
                showarrow=False,
                bgcolor="rgba(0, 0, 0, 0.5)",
                bordercolor="rgba(0, 255, 255, 0.8)",
                borderwidth=1,
            )
    
    # Premium/Discount Zones
    # Procesa las zonas premium y discount
    premium_indices = np.where(premium_discount_data["Zone"] == 1)[0]
    discount_indices = np.where(premium_discount_data["Zone"] == -1)[0]
    neutral_indices = np.where(premium_discount_data["Zone"] == 0)[0]
    
    # Dibuja líneas horizontales para los rangos cuando están disponibles
    valid_ranges = premium_discount_data.dropna(subset=["RangeHigh", "RangeLow", "MidPoint"])
    
    if len(valid_ranges) > 0:
        # Usa el rango más reciente para visualización
        latest_range = valid_ranges.iloc[-1]
        
        # Línea del swing high
        fig.add_shape(
            type="line",
            x0=window_df.index[0],
            y0=latest_range["RangeHigh"],
            x1=window_df.index[-1],
            y1=latest_range["RangeHigh"],
            line=dict(
                color="rgba(255, 0, 0, 0.4)",  # Rojo para swing high
                width=1,
                dash="dot",
            ),
            xref="x", yref="y"
        )
        
        # Línea del punto medio (50%)
        fig.add_shape(
            type="line",
            x0=window_df.index[0],
            y0=latest_range["MidPoint"],
            x1=window_df.index[-1],
            y1=latest_range["MidPoint"],
            line=dict(
                color="rgba(255, 255, 0, 0.6)",  # Amarillo para punto medio
                width=2,
                dash="solid",
            ),
            xref="x", yref="y"
        )
        
        # Línea del swing low
        fig.add_shape(
            type="line",
            x0=window_df.index[0],
            y0=latest_range["RangeLow"],
            x1=window_df.index[-1],
            y1=latest_range["RangeLow"],
            line=dict(
                color="rgba(0, 255, 0, 0.4)",  # Verde para swing low
                width=1,
                dash="dot",
            ),
            xref="x", yref="y"
        )
        
        # Agrega anotaciones para las zonas
        fig.add_annotation(
            x=window_df.index[-1],
            y=latest_range["RangeHigh"],
            xref="x",
            yref="y",
            text="Swing High",
            font=dict(color="rgba(255, 0, 0, 0.8)", size=8),
            showarrow=False,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(255, 0, 0, 0.8)",
            borderwidth=1,
        )
        
        fig.add_annotation(
            x=window_df.index[-1],
            y=latest_range["MidPoint"],
            xref="x",
            yref="y",
            text="50% (Mid)",
            font=dict(color="rgba(255, 255, 0, 0.8)", size=8),
            showarrow=False,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(255, 255, 0, 0.8)",
            borderwidth=1,
        )
        
        fig.add_annotation(
            x=window_df.index[-1],
            y=latest_range["RangeLow"],
            xref="x",
            yref="y",
            text="Swing Low",
            font=dict(color="rgba(0, 255, 0, 0.8)", size=8),
            showarrow=False,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="rgba(0, 255, 0, 0.8)",
            borderwidth=1,
        )
    
    # Agrega marcadores para las zonas actuales
    if len(premium_indices) > 0:
        for idx in premium_indices:
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[idx]], y=[window_df["high"].iloc[idx]],
                    mode="text", text="PREMIUM",
                    textposition="top center",
                    textfont=dict(color="rgba(255, 0, 0, 0.8)", size=8),
                ),
                row=1, col=1
            )
    
    if len(discount_indices) > 0:
        for idx in discount_indices:
            fig.add_trace(
                go.Scatter(
                    x=[window_df.index[idx]], y=[window_df["low"].iloc[idx]],
                    mode="text", text="DISCOUNT",
                    textposition="bottom center",
                    textfont=dict(color="rgba(0, 255, 0, 0.8)", size=8),
                ),
                row=1, col=1
            )

    # Configurar layout para subplots
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=0, r=0, b=0, t=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(12, 14, 18, 1)",
        font=dict(color="white"),
        width=500, height=400  # Aumentar altura para acomodar subplots
    )
    
    # Configurar ejes para subplots
    fig.update_xaxes(visible=False, showticklabels=False, row=1)
    fig.update_xaxes(visible=False, showticklabels=False, row=2)
    fig.update_xaxes(visible=False, showticklabels=False, row=3)
    
    fig.update_yaxes(visible=False, showticklabels=False, row=1)
    fig.update_yaxes(visible=True, showticklabels=True, row=2)
    fig.update_yaxes(visible=True, showticklabels=True, row=3)
    
    # Configurar rangos de los subplots
    fig.update_yaxes(title_text="Precio", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)

    gif.append(fig_to_buffer(fig))

print(f"💾 Guardando GIF con {len(gif)} frames...")
# save the gif
imageio.mimsave("eurusd_smc_macd_rsi.gif", gif, duration=1)
print("✅ ¡GIF generado exitosamente! Archivo: eurusd_smc_macd_rsi.gif")
print(f"📊 Resumen:")
print(f"   - Símbolo: EURUSD")
print(f"   - Timeframe: 5M")
print(f"   - Frames generados: {len(gif)}")
print(f"   - Duración por frame: 1 segundo")
print(f"   - Duración total: {len(gif)} segundos")
print(f"   - Tamaño de imagen: 500x400 píxeles (con subplots)")
print(f"   - Indicadores incluidos: MACD, RSI, SMC") 