#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMAGE GENERATOR C - LIBRERÍA REUTILIZABLE PARA GENERACIÓN DE IMÁGENES SMC
==========================================================================

Esta librería está basada en smart01.py y proporciona funciones para generar
imágenes de gráficos con indicadores SmartMoney Concepts (SMC) de manera
modular y reutilizable.

Funciones principales:
- generate_smc_chart: Genera gráfico completo con candlesticks, MACD, RSI y SMC
- add_FVG: Agrega Fair Value Gaps al gráfico
- add_swing_highs_lows: Agrega Swing Highs/Lows al gráfico
- add_bos_choch: Agrega Break of Structure/Change of Character al gráfico
- add_OB: Agrega Order Blocks al gráfico
- add_liquidity: Agrega niveles de liquidez al gráfico
- add_trend_analysis: Agrega análisis de tendencias al gráfico
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import numpy as np
from datetime import datetime
import os

# ============================================================================
# FUNCIONES PARA CALCULAR INDICADORES TÉCNICOS
# ============================================================================

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    Calcular MACD (Moving Average Convergence Divergence)
    
    Parámetros:
    -----------
    df : DataFrame
        DataFrame con datos OHLCV
    fast_period : int
        Período para la media móvil rápida
    slow_period : int
        Período para la media móvil lenta
    signal_period : int
        Período para la línea de señal
    
    Retorna:
    --------
    tuple
        (macd_line, signal_line, histogram)
    """
    close = df['close']
    
    # Calcular medias móviles exponenciales
    ema_fast = close.ewm(span=fast_period).mean()
    ema_slow = close.ewm(span=slow_period).mean()
    
    # Calcular MACD
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_rsi(df, period=14):
    """
    Calcular RSI (Relative Strength Index)
    
    Parámetros:
    -----------
    df : DataFrame
        DataFrame con datos OHLCV
    period : int
        Período para el cálculo del RSI
    
    Retorna:
    --------
    pandas.Series
        Serie con valores de RSI
    """
    close = df['close']
    delta = close.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi




# ============================================================================
# FUNCIONES PARA AGREGAR INDICADORES SMC AL GRÁFICO
# ============================================================================

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

def add_swing_highs_lows(fig, df, swing_data):
    """Agregar Swing Highs/Lows al gráfico"""
    if swing_data is None or swing_data.empty:
        return fig
        
    window_size = len(df)
    
    # Asegurarse de que swing_data use los mismos índices que df
    swing_data = swing_data.reset_index(drop=True)
    
    indexs = []
    level = []
    for i in range(len(swing_data)):
        if not pd.isna(swing_data["HighLow"].iloc[i]):
            if i < window_size:  # Solo agregar puntos dentro de la ventana
                indexs.append(i)
                level.append(swing_data["Level"].iloc[i])

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
                            if swing_data["HighLow"].iloc[indexs[i]] == -1
                            else "rgba(255, 0, 0, 0.2)"
                        ),
                    ),
                )
            )

    return fig

def add_bos_choch(fig, df, bos_choch_data):
    """Agregar Break of Structure/Change of Character al gráfico"""
    if bos_choch_data is None or bos_choch_data.empty:
        return fig
        
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
                    line=dict(color="rgba(255, 0, 0, 0.8)", width=2),
                    name="BOS"
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="BOS",
                    textposition="middle center",
                    textfont=dict(color='red', size=10, weight='bold'),
                )
            )
        
        # Procesar CHOCH
        if not pd.isna(bos_choch_data["CHOCH"].iloc[i]):
            choch_idx = min(int(bos_choch_data["ChoCHIndex"].iloc[i]), window_size - 1)
            mid_x = min(round((i + choch_idx) / 2), window_size - 1)
            mid_y = bos_choch_data["Level"].iloc[i]
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[choch_idx]],
                    y=[bos_choch_data["Level"].iloc[i], bos_choch_data["Level"].iloc[i]],
                    mode="lines",
                    line=dict(color="rgba(0, 0, 255, 0.8)", width=2),
                    name="CHOCH"
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="CHOCH",
                    textposition="middle center",
                    textfont=dict(color='blue', size=10, weight='bold'),
                )
            )
    
    return fig

def add_OB(fig, df, ob_data):
    """Agregar Order Blocks al gráfico"""
    if ob_data is None or ob_data.empty:
        return fig
    
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
    
    # Asegurarse de que ob_data use los mismos índices que df - EXACTAMENTE como smart01.py
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
                opacity=0.2
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
                showarrow=False
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
                opacity=0.2
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
                showarrow=False
            )
    
    return fig

def add_liquidity(fig, df, liquidity_data):
    """Agregar niveles de liquidez al gráfico - EXACTAMENTE como smart01.py"""
    if liquidity_data is None or liquidity_data.empty:
        return fig
        
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
                    showlegend=False
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
                    showlegend=False
                )
            )
        
        # Procesar liquidez barrida
        if not pd.isna(liquidity_data["Swept"].iloc[i]) and liquidity_data["Swept"].iloc[i] != 0:
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
                    showlegend=False
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
                    showlegend=False
                )
            )
    
    return fig

def add_trend_analysis(fig, df, trends_data):
    """Agregar análisis de tendencias al gráfico"""
    if trends_data is None:
        return fig
        
    # Agregar información de tendencias en la esquina superior derecha
    h1_trend = trends_data.get('h1_trend', 'N/A')
    h4_trend = trends_data.get('h4_trend', 'N/A')
    overall_bias = trends_data.get('overall_bias', 'N/A')
    
    # Crear texto de tendencias
    trend_text = f"H1: {h1_trend}<br>H4: {h4_trend}<br>Bias: {overall_bias}"
    
    # Determinar color basado en el sesgo general
    if overall_bias == 'ALCISTA':
        color = "lime"
    elif overall_bias == 'BAJISTA':
        color = "red"
    else:
        color = "gray"
    
    # Agregar anotación de tendencias
    fig.add_annotation(
        x=df.index[-1],
        y=df['high'].max(),
        text=trend_text,
        showarrow=False,
        font=dict(size=10, color=color, weight='bold'),
        bgcolor="rgba(0,0,0,0.8)",
        bordercolor=color,
        borderwidth=1,
        xanchor="right",
        yanchor="top",
        xshift=-10,
        yshift=-10
    )
    
    return fig

# ============================================================================
# FUNCIÓN PRINCIPAL PARA GENERAR GRÁFICOS COMPLETOS
# ============================================================================



def add_previous_high_low(fig, df, previous_high_low_data):
    window_size = len(df)
    
    # Verificar si el DataFrame está vacío o no tiene las columnas necesarias
    if previous_high_low_data.empty or 'PreviousHigh' not in previous_high_low_data.columns or 'PreviousLow' not in previous_high_low_data.columns:
        return fig  # Retornar sin agregar nada si no hay datos
    
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



def generate_smc_chart(
    df,
    macd_line,
    signal_line,
    histogram,
    rsi,
    current_trend,
    current_trend_15m,
    current_trend_1h,
    current_trend_4h,
    fvg_data,
    swing_highs_lows_data,
    bos_choch_data,
    ob_data,
    liquidity_data,
    previous_high_low_data,
    sessions,
    retracements,
    frame_filename
):
    """
    Genera un gráfico completo con indicadores SMC, MACD, RSI y señales ICC
    
    Parámetros:
    -----------
    df : DataFrame
        Datos OHLCV con índice datetime
    smc_data : dict, opcional
        Diccionario con datos SMC (order_blocks, fvg_data, swing_data, etc.)
    icc_signals : list, opcional
        Lista de señales ICC para mostrar en el gráfico
    signal_type : str
        Tipo de señal para el título
    title : str
        Título del gráfico
    width : int
        Ancho de la imagen
    height : int
        Alto de la imagen
    save_path : str, opcional
        Ruta donde guardar la imagen (si no se especifica, no se guarda)
    
    Retorna:
    --------
    plotly.graph_objects.Figure
        Figura de Plotly con el gráfico completo
    """
    
    if df is None or df.empty:
        raise ValueError("DataFrame no puede ser None o vacío")
    
   
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
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color="#77dd76",
            decreasing_line_color="#ff6962",
            name="EURUSD"
        )
    )
    
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
    # Agregar anotación de tendencia 5M en la parte inferior izquierda del gráfico
    fig.add_annotation(
        x=df.index[0],
        y=df['low'].min(),
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

    # NOTA: trend_type_15m puede ser actualizado con sufijo _ALCISTA/_BAJISTA
    fig.add_annotation(
        x=df.index[0],
        y=df['low'].min(),
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
    

    fig.add_annotation(
                    x=df.index[0],
                    y=df['low'].min(),
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


    fig.add_annotation(
                    x=df.index[0],
                    y=df['low'].min(),
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

    add_FVG(fig, df, fvg_data)
    add_swing_highs_lows(fig, df, swing_highs_lows_data)
    add_bos_choch(fig, df, bos_choch_data)
    add_OB(fig,df, ob_data)
    add_liquidity(fig,df, liquidity_data)
    add_previous_high_low(fig,df, previous_high_low_data)
    add_sessions(fig,df, sessions)
    add_retracements(fig,df, retracements)

        # 2. GRÁFICO MACD
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=macd_line,
            mode='lines',
            name='MACD',
            line=dict(color='teal', width=1),
            showlegend=False
        ),row=2, col=1
    )
      
    fig.add_trace(
        go.Scatter(
            x=df.index,
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
            x=df.index,
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
            x=df.index,
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
    
    # Intentar guardar la imagen con manejo de errores de Kaleido
    try:
        fig.write_image(frame_filename, width=800, height=600)
        print(f"   ✅ Imagen guardada exitosamente: {frame_filename}")
    except Exception as kaleido_error:
        print(f"   ⚠️ Error de Kaleido al guardar imagen: {kaleido_error}")
        print(f"   🔄 Intentando método alternativo...")
        
        # Método alternativo: guardar como HTML
        try:
            html_filename = frame_filename.replace('.png', '.html')
            fig.write_html(html_filename)
            print(f"   ✅ Imagen guardada como HTML: {html_filename}")
        except Exception as html_error:
            print(f"   ❌ Error guardando como HTML: {html_error}")
            print(f"   💡 Sugerencia: Instalar/actualizar kaleido: pip install -U kaleido")


# ============================================================================
# FUNCIÓN DE CONVENIENCIA PARA GENERAR IMÁGENES ICC
# ============================================================================

def add_sessions(fig, df, sessions):
    window_size = len(df)
    
    # Verificar si el DataFrame está vacío o no tiene las columnas necesarias
    if sessions.empty or 'Active' not in sessions.columns or 'Low' not in sessions.columns or 'High' not in sessions.columns:
        return fig  # Retornar sin agregar nada si no hay datos
    
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
    
    # Verificar si el DataFrame está vacío o no tiene las columnas necesarias
    if retracements.empty or 'Direction' not in retracements.columns:
        return fig  # Retornar sin agregar nada si no hay datos
    
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

def generate_icc_image(
    data_buffer,
    icc_signals,
    smc_data=None,
    signal_type="ICC",
    save_dir="frames_png"
):
    """
    Función de conveniencia para generar imágenes ICC específicamente
    
    Parámetros:
    -----------
    data_buffer : list
        Lista de velas con datos OHLCV
    icc_signals : list
        Lista de señales ICC
    smc_data : dict, opcional
        Datos SMC para mostrar en el gráfico
    signal_type : str
        Tipo de señal
    save_dir : str
        Directorio donde guardar la imagen
    
    Retorna:
    --------
    str
        Nombre del archivo generado o None si falla
    """
    
    try:
        # Convertir buffer a DataFrame
        df = pd.DataFrame(data_buffer)
        df.set_index('datetime', inplace=True)
        
        # Crear nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        direction = icc_signals[0].get('direction', 'UNKNOWN') if icc_signals else 'UNKNOWN'
        filename = f"ICC_Signal_{timestamp}_{direction}.png"
        save_path = os.path.join(save_dir, filename)
        
        # Calcular indicadores técnicos
        macd_line, signal_line, histogram = calculate_macd(df)
        rsi = calculate_rsi(df)
        
        # Extraer datos SMC del diccionario
        if smc_data:
            print(f"   🔍 Extrayendo datos SMC para visualización...")
            print(f"   📊 Contenido de smc_data: {list(smc_data.keys())}")
            
            # Extraer datos individuales
            fvg_data = smc_data.get('fvg_data', pd.DataFrame())
            swing_highs_lows_data = smc_data.get('swing_data', pd.DataFrame())
            bos_choch_data = smc_data.get('bos_choch_data', pd.DataFrame())
            ob_data = smc_data.get('order_blocks', pd.DataFrame())
            liquidity_data = pd.DataFrame()  # No disponible en smc_data actual
            previous_high_low_data = pd.DataFrame()  # No disponible en smc_data actual
            
            # Extraer tendencias y convertir a valores numéricos
            trends = smc_data.get('trends', {})
            
            # Función para convertir string de tendencia a número
            def trend_to_number(trend_str):
                if trend_str == 'ALCISTA':
                    return 1.0
                elif trend_str == 'BAJISTA':
                    return -1.0
                elif trend_str == 'LATERAL':
                    return 0.0
                else:
                    return 0.0  # Default para 'N/A' o valores desconocidos
            
            current_trend = trend_to_number(trends.get('overall_bias', 'N/A'))
            current_trend_15m = 0.0  # No disponible en smc_data actual
            current_trend_1h = trend_to_number(trends.get('h1_trend', 'N/A'))
            current_trend_4h = trend_to_number(trends.get('h4_trend', 'N/A'))
            
            print(f"   📊 Datos SMC extraídos para visualización:")
            print(f"      • Order Blocks: {len(ob_data) if not ob_data.empty else 0}")
            print(f"      • Fair Value Gaps: {len(fvg_data) if not fvg_data.empty else 0}")
            print(f"      • Swing Points: {len(swing_highs_lows_data) if not swing_highs_lows_data.empty else 0}")
            print(f"      • BOS/CHOCH: {len(bos_choch_data) if not bos_choch_data.empty else 0}")
            print(f"      • Tendencias H1: {current_trend_1h}")
            print(f"      • Tendencias H4: {current_trend_4h}")
        else:
            print(f"   ❌ No se recibieron datos SMC")
            # Datos vacíos por defecto
            fvg_data = pd.DataFrame()
            swing_highs_lows_data = pd.DataFrame()
            bos_choch_data = pd.DataFrame()
            ob_data = pd.DataFrame()
            liquidity_data = pd.DataFrame()
            previous_high_low_data = pd.DataFrame()
            current_trend = 0.0  # LATERAL
            current_trend_15m = 0.0  # LATERAL
            current_trend_1h = 0.0  # LATERAL
            current_trend_4h = 0.0  # LATERAL
        
        # Datos adicionales requeridos por generate_smc_chart
        sessions = pd.DataFrame()  # No disponible
        retracements = pd.DataFrame()  # No disponible
        
        # Generar gráfico usando la función original
        fig = generate_smc_chart(
            df=df,
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=histogram,
            rsi=rsi,
            current_trend=current_trend,
            current_trend_15m=current_trend_15m,
            current_trend_1h=current_trend_1h,
            current_trend_4h=current_trend_4h,
            fvg_data=fvg_data,
            swing_highs_lows_data=swing_highs_lows_data,
            bos_choch_data=bos_choch_data,
            ob_data=ob_data,
            liquidity_data=liquidity_data,
            previous_high_low_data=previous_high_low_data,
            sessions=sessions,
            retracements=retracements,
            frame_filename=save_path
        )
        
        return filename
        
    except Exception as e:
        print(f"   ❌ Error generando imagen ICC: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# FUNCIÓN DE COMPATIBILIDAD CON image_generator.py
# ============================================================================

def generate_signal_image(data_buffer, icc_signals, smc_data=None, signal_type="ICC"):
    """
    Función de compatibilidad con image_generator.py existente
    
    Esta función mantiene la misma interfaz que image_generator.py
    pero usa la nueva implementación basada en smart01.py
    """
    
    return generate_icc_image(
        data_buffer=data_buffer,
        icc_signals=icc_signals,
        smc_data=smc_data,
        signal_type=signal_type
    )

# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("🚀 IMAGE GENERATOR C - Librería de generación de imágenes SMC")
    print("=" * 70)
    print("Esta librería proporciona funciones para generar gráficos con")
    print("indicadores SmartMoney Concepts (SMC) de manera modular.")
    print("\nFunciones disponibles:")
    print("  • generate_smc_chart: Gráfico completo con SMC, MACD, RSI")
    print("  • generate_icc_image: Imagen específica para señales ICC")
    print("  • generate_signal_image: Compatibilidad con image_generator.py")
    print("\nPara usar en otros scripts:")
    print("  from image_generator_c import generate_icc_image")
    print("  from image_generator_c import generate_smc_chart")
    print("  from image_generator_c import generate_signal_image")
