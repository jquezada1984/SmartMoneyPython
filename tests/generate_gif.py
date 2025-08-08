import pandas as pd
import plotly.graph_objects as go
import sys
import os
from datetime import datetime
import numpy as np
import time
import imageio
from io import BytesIO
from PIL import Image
from tqdm import tqdm

sys.path.append(os.path.abspath("../"))
from smartmoneyconcepts.smc import smc

def add_FVG(fig, df, fvg_data):
    for i in range(len(fvg_data["FVG"])):
        if not np.isnan(fvg_data["FVG"][i]):
            x1 = int(
                fvg_data["MitigatedIndex"][i]
                if fvg_data["MitigatedIndex"][i] != 0
                else len(df) - 1
            )
            # En lugar de shape, usar líneas para crear el rectángulo
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[x1], df.index[x1], df.index[i], df.index[i]],
                    y=[fvg_data["Top"][i], fvg_data["Top"][i], fvg_data["Bottom"][i], fvg_data["Bottom"][i], fvg_data["Top"][i]],
                    mode="lines",
                    line=dict(color="yellow", width=4),
                    name="FVG",
                    showlegend=False,
                )
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
                )
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
            )
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
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="BOS",
                    textposition="top center" if bos_choch_data["BOS"][i] == 1 else "bottom center",
                    textfont=dict(color="rgba(255, 165, 0, 0.4)", size=8),
                )
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
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[df.index[mid_x]],
                    y=[mid_y],
                    mode="text",
                    text="CHOCH",
                    textposition="top center" if bos_choch_data["CHOCH"][i] == 1 else "bottom center",
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

    for i in range(len(ob_data["OB"])):
        if ob_data["OB"][i] == 1:
            x1 = int(
                ob_data["MitigatedIndex"][i]
                if ob_data["MitigatedIndex"][i] != 0
                else len(df) - 1
            )
            # En lugar de shape, usar líneas para crear el rectángulo
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[x1], df.index[x1], df.index[i], df.index[i]],
                    y=[ob_data["Bottom"][i], ob_data["Bottom"][i], ob_data["Top"][i], ob_data["Top"][i], ob_data["Bottom"][i]],
                    mode="lines",
                    line=dict(color="Purple", width=4),
                name="Bullish OB",
                    showlegend=False,
                )
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
            # En lugar de shape, usar líneas para crear el rectángulo
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[x1], df.index[x1], df.index[i], df.index[i]],
                    y=[ob_data["Bottom"][i], ob_data["Bottom"][i], ob_data["Top"][i], ob_data["Top"][i], ob_data["Bottom"][i]],
                    mode="lines",
                    line=dict(color="Purple", width=4),
                name="Bearish OB",
                    showlegend=False,
                )
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
                )
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
                )
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
                )
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
                )
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
            # En lugar de shape, usar líneas para crear el rectángulo
            fig.add_trace(
                go.Scatter(
                    x=[df.index[i], df.index[i + 1], df.index[i + 1], df.index[i], df.index[i]],
                    y=[sessions["Low"][i], sessions["Low"][i], sessions["High"][i], sessions["High"][i], sessions["Low"][i]],
                    mode="lines",
                    line=dict(color="#16866E", width=3),
                    name="Session",
                    showlegend=False,
                )
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


# get the data
def import_data(csv_path):
    """
    Importa datos desde CSV
    """
    try:
        print(f"📊 Importando datos desde {csv_path}...")
        df = pd.read_csv(csv_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        
        # Asegurar que las columnas numéricas sean float
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Eliminar filas con valores NaN
        df = df.dropna()
        
        print(f"✅ Datos importados: {len(df)} registros")
        print(f"📈 Rango de fechas: {df.index[0]} a {df.index[-1]}")
        return df
    except Exception as e:
        print(f"❌ Error al importar datos: {e}")
        return None


# Importar datos desde CSV
csv_path = r"C:\Proyectos\SmartMoneyPython\tests\test_data\EURUSD\EURUSD_15M_20250806_091313.csv"
df = import_data(csv_path)
if df is None:
    print("❌ No se pudieron importar los datos. Saliendo...")
    exit(1)

def fig_to_buffer(fig):
    try:
        fig_bytes = fig.to_image(format="png", width=500, height=300)
        fig_buffer = BytesIO(fig_bytes)
        fig_image = Image.open(fig_buffer)
        return fig_image  # Retornar la imagen PIL directamente
    except Exception as e:
        print(f"⚠️ Error al generar frame: {e}")
        # Crear una imagen en blanco como fallback
        blank_image = Image.new('RGB', (500, 300), color='black')
        return blank_image


# Crear carpeta para frames si no existe
import os
frames_dir = "frames_png"
if not os.path.exists(frames_dir):
    os.makedirs(frames_dir)

window = 100
print(f"🎬 Preparando generación de frames PNG con {len(df)} velas (ventana de {window} velas)")
print(f"📈 Se generarán {len(df) - window} frames PNG")
print(f"📁 Los frames se guardarán en: {frames_dir}/")

print("🎨 Generando frames PNG...")
# Para debug, solo generar frame 104
for pos in tqdm(range(104, 105), desc="Generando frames", unit="frame"):
    window_df = df.iloc[pos - window : pos]

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=window_df.index,
                open=window_df["open"],
                high=window_df["high"],
                low=window_df["low"],
                close=window_df["close"],
                increasing_line_color="#77dd76",
                decreasing_line_color="#ff6962",
            )
        ]
    )

    fvg_data = smc.fvg(window_df, join_consecutive=True)
    swing_highs_lows_data = smc.swing_highs_lows(window_df, swing_length=5)
    bos_choch_data = smc.bos_choch(window_df, swing_highs_lows_data)
    ob_data = smc.ob(window_df, swing_highs_lows_data)
    liquidity_data = smc.liquidity(window_df, swing_highs_lows_data)
    previous_high_low_data = smc.previous_high_low(window_df, time_frame="4h")
    sessions = smc.sessions(window_df, session="London")
    retracements = smc.retracements(window_df, swing_highs_lows_data)
    
    # Debug específico para frame 104
    print(f"🔍 Debug Frame {pos}:")
    print(f"   - Order Blocks detectados: {len([x for x in ob_data['OB'] if not np.isnan(x)])}")
    print(f"   - FVG detectados: {len([x for x in fvg_data['FVG'] if not np.isnan(x)])}")
    print(f"   - Sesiones activas: {len([x for x in sessions['Active'] if x == 1])}")
    print(f"   - Swing highs/lows: {len([x for x in swing_highs_lows_data['HighLow'] if not np.isnan(x)])}")
    
    # Debug detallado de FVG
    print(f"\n📊 Debug FVG:")
    for i in range(len(fvg_data["FVG"])):
        if not np.isnan(fvg_data["FVG"][i]):
            x1 = int(fvg_data["MitigatedIndex"][i] if fvg_data["MitigatedIndex"][i] != 0 else len(window_df) - 1)
            print(f"   FVG {i}: x0={window_df.index[i]}, y0={fvg_data['Top'][i]:.5f}, x1={window_df.index[x1]}, y1={fvg_data['Bottom'][i]:.5f}")
            if i >= 2:  # Solo mostrar primeros 3
                break
    
    # Debug detallado de Order Blocks
    print(f"\n🟣 Debug Order Blocks:")
    for i in range(len(ob_data["OB"])):
        if not np.isnan(ob_data["OB"][i]):
            x1 = int(ob_data["MitigatedIndex"][i] if ob_data["MitigatedIndex"][i] != 0 else len(window_df) - 1)
            print(f"   OB {i}: tipo={ob_data['OB'][i]}, x0={window_df.index[i]}, y0={ob_data['Bottom'][i]:.5f}, x1={window_df.index[x1]}, y1={ob_data['Top'][i]:.5f}")
            if i >= 1:  # Solo mostrar primeros 2
                break
    
    # Debug del rango de precios
    print(f"\n💰 Rango de precios en ventana:")
    print(f"   - Precio mínimo: {window_df['low'].min():.5f}")
    print(f"   - Precio máximo: {window_df['high'].max():.5f}")
    print(f"   - Rango total: {window_df['high'].max() - window_df['low'].min():.5f}")

    # PRUEBA DIRECTA: Agregar líneas de prueba para verificar que funcionan
    fig.add_trace(
        go.Scatter(
            x=[window_df.index[10], window_df.index[50]],
            y=[window_df['high'].max(), window_df['high'].max()],
            mode="lines",
            line=dict(color="red", width=5),
            name="TEST LINE",
            showlegend=False,
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=[window_df.index[20], window_df.index[60]],
            y=[window_df['low'].min(), window_df['low'].min()],
            mode="lines",
            line=dict(color="cyan", width=5),
            name="TEST LINE 2",
            showlegend=False,
        )
    )
    
    fig = add_FVG(fig, window_df, fvg_data)
    fig = add_swing_highs_lows(fig, window_df, swing_highs_lows_data)
    fig = add_bos_choch(fig, window_df, bos_choch_data)
    fig = add_OB(fig, window_df, ob_data)
    fig = add_liquidity(fig, window_df, liquidity_data)
    fig = add_previous_high_low(fig, window_df, previous_high_low_data)
    fig = add_sessions(fig, window_df, sessions)
    fig = add_retracements(fig, window_df, retracements)

    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_layout(showlegend=True)  # Mostrar leyenda para debug
    fig.update_layout(margin=dict(l=20, r=20, b=20, t=20))  # Márgenes mínimos pero no cero
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
    fig.update_layout(paper_bgcolor="rgba(12, 14, 18, 1)")
    fig.update_layout(font=dict(color="white"))

    # reduce the size of the image
    fig.update_layout(width=500, height=300)

    # Forzar actualización de la figura para asegurar renderizado
    fig.update_layout(showlegend=False)
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0))

    # Generar frame y guardar como PNG
    frame = fig_to_buffer(fig)
    
    # Guardar frame como PNG
    frame_filename = f"{frames_dir}/frame_{pos:04d}.png"
    frame.save(frame_filename, "PNG")
    
    # Limpiar memoria de la figura
    del fig

print(f"✅ ¡Frames PNG generados exitosamente!")
print(f"📁 Frames guardados en: {frames_dir}/")
print(f"📊 Resumen:")
print(f"   - Frames generados: {len(df) - window}")
print(f"   - Tamaño de imagen: 500x300 píxeles")
print(f"   - Formato: PNG individual")
print(f"   - Nomenclatura: frame_XXXX.png")