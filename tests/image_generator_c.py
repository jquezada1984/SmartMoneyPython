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
# FUNCIONES DE CÁLCULO DE INDICADORES TÉCNICOS
# ============================================================================

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

# ============================================================================
# FUNCIONES PARA AGREGAR INDICADORES SMC AL GRÁFICO
# ============================================================================

def add_FVG(fig, df, fvg_data):
    """Agregar Fair Value Gaps al gráfico"""
    if fvg_data is None or fvg_data.empty:
        return fig
        
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
        
    window_size = len(df)
    
    # Asegurarse de que ob_data use los mismos índices que df
    ob_data = ob_data.reset_index(drop=True)
    
    for i in range(len(ob_data)):
        if i >= window_size:
            break
            
        if not pd.isna(ob_data["OB"].iloc[i]):
            # Obtener información del Order Block
            ob_type = ob_data["Type"].iloc[i] if "Type" in ob_data.columns else "Unknown"
            ob_level = ob_data["Level"].iloc[i] if "Level" in ob_data.columns else 0
            
            # Determinar color basado en el tipo
            if ob_type == "Bullish" or ob_type == "BULLISH":
                color = "rgba(0, 255, 0, 0.3)"  # Verde para alcista
                text_color = "lime"
            elif ob_type == "Bearish" or ob_type == "BEARISH":
                color = "rgba(255, 0, 0, 0.3)"  # Rojo para bajista
                text_color = "red"
            else:
                color = "rgba(255, 255, 0, 0.3)"  # Amarillo para desconocido
                text_color = "yellow"
            
            # Agregar rectángulo del Order Block
            fig.add_shape(
                type="rect",
                x0=df.index[i],
                y0=ob_level - 0.0005,  # Altura del OB
                x1=df.index[min(i + 5, window_size - 1)],  # Ancho del OB
                y1=ob_level + 0.0005,
                line=dict(width=1, color=text_color),
                fillcolor=color,
                opacity=0.5,
            )
            
            # Agregar etiqueta
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i]],
                    y=[ob_level],
                    mode="text",
                    text="OB",
                    textposition="middle center",
                    textfont=dict(color=text_color, size=8, weight='bold'),
                )
            )
    
    return fig

def add_liquidity(fig, df, liquidity_data):
    """Agregar niveles de liquidez al gráfico"""
    if liquidity_data is None or liquidity_data.empty:
        return fig
        
    window_size = len(df)
    
    # Asegurarse de que liquidity_data use los mismos índices que df
    liquidity_data = liquidity_data.reset_index(drop=True)
    
    for i in range(len(liquidity_data)):
        if i >= window_size:
            break
            
        if not pd.isna(liquidity_data["Liquidity"].iloc[i]):
            level = liquidity_data["Level"].iloc[i]
            liquidity_type = liquidity_data["Type"].iloc[i] if "Type" in liquidity_data.columns else "Unknown"
            
            # Determinar color basado en el tipo
            if liquidity_type == "High" or liquidity_type == "HIGH":
                color = "rgba(255, 0, 255, 0.8)"  # Magenta para alta liquidez
                text = "LIQ+"
            elif liquidity_type == "Low" or liquidity_type == "LOW":
                color = "rgba(255, 165, 0, 0.8)"  # Naranja para baja liquidez
                text = "LIQ-"
            else:
                color = "rgba(128, 128, 128, 0.8)"  # Gris para desconocido
                text = "LIQ"
            
            # Agregar línea horizontal de liquidez
            fig.add_hline(
                y=level,
                line_dash="dot",
                line_color=color,
                opacity=0.7,
                line_width=2
            )
            
            # Agregar etiqueta
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i]],
                    y=[level],
                    mode="text",
                    text=text,
                    textposition="middle right",
                    textfont=dict(color=color, size=10, weight='bold'),
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

def generate_smc_chart(
    df,
    smc_data=None,
    icc_signals=None,
    signal_type="SMC",
    title="EURUSD - Análisis SMC",
    width=1200,
    height=800,
    save_path=None
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
    
    # Calcular indicadores técnicos
    if len(df) >= 26:
        macd_line, signal_line, histogram = calculate_macd(df)
        rsi = calculate_rsi(df)
    else:
        # Si no hay suficientes datos, crear indicadores básicos
        macd_line = pd.Series([0] * len(df), index=df.index)
        signal_line = pd.Series([0] * len(df), index=df.index)
        histogram = pd.Series([0] * len(df), index=df.index)
        rsi = pd.Series([50] * len(df), index=df.index)
    
    # Crear subplots: Candlesticks (67%), MACD (17%), RSI (16%)
    fig = sp.make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.67, 0.17, 0.16],
        subplot_titles=(title, 'MACD', 'RSI')
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
        ),
        row=1, col=1
    )
    
    # 2. AGREGAR INDICADORES SMC SI ESTÁN DISPONIBLES
    if smc_data:
        print(f"   🔍 Agregando indicadores SMC al gráfico...")
        print(f"   📊 Contenido de smc_data: {list(smc_data.keys())}")
        
        # Agregar Order Blocks
        if 'order_blocks' in smc_data and smc_data['order_blocks'] is not None:
            print(f"   📦 Order Blocks encontrados: {len(smc_data['order_blocks'])} filas")
            if not smc_data['order_blocks'].empty:
                print(f"   📦 Columnas de Order Blocks: {list(smc_data['order_blocks'].columns)}")
                print(f"   📦 Primeras filas de Order Blocks:")
                print(smc_data['order_blocks'].head(3))
            fig = add_OB(fig, df, smc_data['order_blocks'])
            print(f"   ✅ Order Blocks agregados")
        else:
            print(f"   ❌ No se encontraron Order Blocks en smc_data")
        
        # Agregar Fair Value Gaps
        if 'fvg_data' in smc_data and smc_data['fvg_data'] is not None:
            print(f"   🔶 Fair Value Gaps encontrados: {len(smc_data['fvg_data'])} filas")
            fig = add_FVG(fig, df, smc_data['fvg_data'])
            print(f"   ✅ Fair Value Gaps agregados")
        else:
            print(f"   ❌ No se encontraron Fair Value Gaps en smc_data")
        
        # Agregar Swing Highs/Lows
        if 'swing_data' in smc_data and smc_data['swing_data'] is not None:
            print(f"   📈 Swing Points encontrados: {len(smc_data['swing_data'])} filas")
            fig = add_swing_highs_lows(fig, df, smc_data['swing_data'])
            print(f"   ✅ Swing Highs/Lows agregados")
        else:
            print(f"   ❌ No se encontraron Swing Points en smc_data")
        
        # Agregar BOS/CHOCH
        if 'bos_choch_data' in smc_data and smc_data['bos_choch_data'] is not None:
            print(f"   🚀 BOS/CHOCH encontrados: {len(smc_data['bos_choch_data'])} filas")
            fig = add_bos_choch(fig, df, smc_data['bos_choch_data'])
            print(f"   ✅ BOS/CHOCH agregados")
        else:
            print(f"   ❌ No se encontraron BOS/CHOCH en smc_data")
        
        # Agregar Liquidez
        if 'liquidity_data' in smc_data and smc_data['liquidity_data'] is not None:
            print(f"   💧 Liquidez encontrada: {len(smc_data['liquidity_data'])} filas")
            fig = add_liquidity(fig, df, smc_data['liquidity_data'])
            print(f"   ✅ Liquidez agregada")
        else:
            print(f"   ❌ No se encontró Liquidez en smc_data")
        
        # Agregar análisis de tendencias
        if 'trends' in smc_data and smc_data['trends'] is not None:
            print(f"   📊 Tendencias encontradas: {smc_data['trends']}")
            fig = add_trend_analysis(fig, df, smc_data['trends'])
            print(f"   ✅ Análisis de tendencias agregado")
        else:
            print(f"   ❌ No se encontraron Tendencias en smc_data")
    else:
        print(f"   ❌ No se recibieron datos SMC (smc_data es None o vacío)")
    
    # 3. AGREGAR SEÑALES ICC SI ESTÁN DISPONIBLES
    if icc_signals:
        print(f"   🎯 Agregando señales ICC al gráfico...")
        
        for signal in icc_signals:
            direction = signal.get('direction', 'UNKNOWN')
            entry_price = signal.get('entry_price', 0)
            risk_management = signal.get('risk_management', {})
            stop_loss = risk_management.get('stop_loss', 0)
            take_profit = risk_management.get('take_profit', 0)
            
            # Agregar punto de entrada
            color = "green" if direction == "LONG" else "red"
            fig.add_trace(
                go.Scatter(
                    x=[df.index[-1]],
                    y=[entry_price],
                    mode="markers",
                    marker=dict(
                        symbol="diamond",
                        size=12,
                        color=color,
                        line=dict(width=2, color="white")
                    ),
                    name=f"Entrada {direction}"
                )
            )
            
            # Agregar Stop Loss
            if stop_loss > 0:
                fig.add_hline(
                    y=stop_loss,
                    line_dash="dash",
                    line_color="red",
                    opacity=0.8,
                    line_width=2,
                    annotation_text="Stop Loss"
                )
            
            # Agregar Take Profit
            if take_profit > 0:
                fig.add_hline(
                    y=take_profit,
                    line_dash="dash",
                    line_color="green",
                    opacity=0.8,
                    line_width=2,
                    annotation_text="Take Profit"
                )
        
        print(f"   ✅ Señales ICC agregadas al gráfico")
    
    # 4. AGREGAR MACD
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=macd_line,
            mode="lines",
            line=dict(color="blue", width=2),
            name="MACD Line"
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=signal_line,
            mode="lines",
            line=dict(color="red", width=2),
            name="Signal Line"
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=histogram,
            name="Histogram",
            marker_color="gray",
            opacity=0.6
        ),
        row=2, col=1
    )
    
    # 5. AGREGAR RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=rsi,
            mode="lines",
            line=dict(color="purple", width=2),
            name="RSI"
        ),
        row=3, col=1
    )
    
    # Agregar líneas de referencia RSI
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.3, row=3, col=1)
    
    # 6. CONFIGURAR LAYOUT
    fig.update_layout(
        title=title,
        xaxis_title="Fecha/Hora",
        yaxis_title="Precio",
        template="plotly_dark",
        width=width,
        height=height,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 7. CONFIGURAR EJES
    # Ejes principales
    fig.update_xaxes(
        title_text="",
        row=1, col=1,
        tickformat="%d/%m %H:%M",
        tickangle=45,
        tickfont=dict(size=10, color="white"),
        tickmode='auto',
        nticks=8
    )
    fig.update_yaxes(title_text="Precio", row=1, col=1)
    
    # Ejes MACD
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
    
    # Ejes RSI
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
    
    # 8. GUARDAR IMAGEN SI SE ESPECIFICA
    if save_path:
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Guardar imagen
            fig.write_image(save_path, width=width, height=height)
            print(f"   ✅ Imagen guardada exitosamente: {save_path}")
        except Exception as e:
            print(f"   ❌ Error guardando imagen: {e}")
    
    return fig

# ============================================================================
# FUNCIÓN DE CONVENIENCIA PARA GENERAR IMÁGENES ICC
# ============================================================================

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
        
        # Generar título del gráfico
        title = f"EURUSD - Señal {signal_type} con SMC Real + TP Estructural"
        
        # Generar gráfico
        fig = generate_smc_chart(
            df=df,
            smc_data=smc_data,
            icc_signals=icc_signals,
            signal_type=signal_type,
            title=title,
            width=1200,
            height=800,
            save_path=save_path
        )
        
        return filename
        
    except Exception as e:
        print(f"   ❌ Error generando imagen ICC: {e}")
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
