[![PyPI](https://img.shields.io/pypi/v/smartmoneyconcepts.svg?style=flat-square)](https://pypi.org/project/smartmoneyconcepts/)
[![Downloads](https://pepy.tech/badge/smartmoneyconcepts/month)](https://pepy.tech/project/smartmoneyconcepts/month)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Bitcoin Donate](https://badgen.net/badge/Bitcoin/Donate/F19537?icon=bitcoin)](https://blockstream.info/address/bc1petss2mlqyjsajyzhu06wzl667v0f8svc0hnpqjj2d32frtx77g4sg5s0pg)

<p align="center">
  <img src="https://github.com//smart-money-concepts/blob/f0c0fc28cc290cdd9dfcc6a6ac246ed1d59061be/tests/test.gif" alt="Gráfico de Velas Mostrando Indicadores"/>
</p>

# Smart Money Concepts (smc)

El Indicador Python de Smart Money Concepts es una herramienta financiera sofisticada desarrollada para traders e inversores para obtener información sobre el sentimiento del mercado, tendencias y posibles reversiones. Este indicador está inspirado en los conceptos de Inner Circle Trader (ICT) como Order blocks, Liquidity, Fair Value Gap, Swing Highs and Lows, Break of Structure, Change of Character, y más. Por favor, echa un vistazo y contribuye al proyecto.

## Instalación

```bash
pip install smartmoneyconcepts
```

## Uso

```python
from smartmoneyconcepts import smc
```

Prepara los datos para usar con smc:

smc espera un DataFrame OHLC correctamente formateado, con nombres de columnas en minúsculas: ["open", "high", "low", "close"] y ["volume"] para indicadores que esperan entrada OHLCV.

## Indicadores

### Fair Value Gap (FVG)

```python
smc.fvg(ohlc, join_consecutive=False)
```

Un fair value gap es cuando el máximo anterior es menor que el mínimo siguiente si la vela actual es alcista.
O cuando el mínimo anterior es mayor que el máximo siguiente si la vela actual es bajista.

parámetros:<br>
join_consecutive: bool - si hay múltiples FVG consecutivos, se fusionarán en uno usando el máximo más alto y el mínimo más bajo<br>

retorna:<br>
FVG = 1 si fair value gap alcista, -1 si fair value gap bajista<br>
Top = el tope del fair value gap<br>
Bottom = el fondo del fair value gap<br>
MitigatedIndex = el índice de la vela que mitigó el fair value gap<br>

### Swing Highs and Lows

```python
smc.swing_highs_lows(ohlc, swing_length = 50)
```

Un swing high es cuando el máximo actual es el máximo más alto de la cantidad swing_length de velas antes y después.
Un swing low es cuando el mínimo actual es el mínimo más bajo de la cantidad swing_length de velas antes y después.

parámetros:<br>
swing_length: int - la cantidad de velas para mirar hacia atrás y hacia adelante para determinar el swing high o low<br>

retorna:<br>
HighLow = 1 si swing high, -1 si swing low<br>
Level = el nivel del swing high o low<br>

### Break of Structure (BOS) & Change of Character (CHoCH)

```python
smc.bos_choch(ohlc, swing_highs_lows, close_break = True)
```

Estos son ambos indicaciones de cambio en la estructura del mercado

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>
close_break: bool - si es True entonces la ruptura de estructura se mitigará basándose en el cierre de la vela, de lo contrario será el high/low.<br>

retorna:<br>
BOS = 1 si ruptura de estructura alcista, -1 si ruptura de estructura bajista<br>
CHOCH = 1 si cambio de carácter alcista, -1 si cambio de carácter bajista<br>
Level = el nivel de la ruptura de estructura o cambio de carácter<br>
BrokenIndex = el índice de la vela que rompió el nivel<br>

### Order Blocks (OB)

```python
smc.ob(ohlc, swing_highs_lows, close_mitigation = False)
```

Este método detecta order blocks cuando existe una alta cantidad de órdenes de mercado en un rango de precios.

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>
close_mitigation: bool - si es True entonces el order block se mitigará basándose en el cierre de la vela, de lo contrario será el high/low.

retorna:<br>
OB = 1 si order block alcista, -1 si order block bajista<br>
Top = tope del order block<br>
Bottom = fondo del order block<br>
OBVolume = volumen + 2 últimos volúmenes<br>
Percentage = fuerza del order block (min(highVolume, lowVolume)/max(highVolume,lowVolume))<br>


### Liquidity

```python
smc.liquidity(ohlc, swing_highs_lows, range_percent = 0.01)
```

Liquidez es cuando hay múltiples máximos dentro de un pequeño rango entre sí.
o múltiples mínimos dentro de un pequeño rango entre sí.

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>
range_percent: float - el porcentaje del rango para determinar la liquidez<br>

retorna:<br>
Liquidity = 1 si liquidez alcista, -1 si liquidez bajista<br>
Level = el nivel de la liquidez<br>
End = el índice del último nivel de liquidez<br>
Swept = el índice de la vela que barrió la liquidez<br>

### Previous High And Low

```python
smc.previous_high_low(ohlc, time_frame = "1D")
```

Este método retorna el máximo y mínimo anterior del marco de tiempo dado.

parámetros:<br>
time_frame: str - el marco de tiempo para obtener el máximo y mínimo anterior 15m, 1H, 4H, 1D, 1W, 1M<br>

retorna:<br>
PreviousHigh = el máximo anterior<br>
PreviousLow = el mínimo anterior<br>
BrokenHigh = 1 una vez que el precio ha roto el máximo anterior del timeframe, 0 en caso contrario<br>
BrokenLow = 1 una vez que el precio ha roto el mínimo anterior del timeframe, 0 en caso contrario<br>

### Sessions

```python
smc.sessions(ohlc, session, start_time, end_time, time_zone = "UTC")
```

Este método retorna qué velas están dentro de la sesión especificada

parámetros:<br>
session: str - la sesión que quieres verificar (Sydney, Tokyo, London, New York, Asian kill zone, London open kill zone, New York kill zone, london close kill zone, Custom)<br>
start_time: str - la hora de inicio de la sesión en formato "HH:MM" solo requerido para sesión personalizada.<br>
end_time: str - la hora de fin de la sesión en formato "HH:MM" solo requerido para sesión personalizada.<br>
time_zone: str - la zona horaria de las velas puede estar en formato "UTC+0" o "GMT+0"<br>

retorna:<br>
Active = 1 si la vela está dentro de la sesión, 0 si no<br>
High = el punto más alto de la sesión<br>
Low = el punto más bajo de la sesión<br>

### Retracements

```python
smc.retracements(ohlc, swing_highs_lows)
```

Este método retorna el porcentaje de un retroceso desde el swing high o low

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>

retorna:<br>
Direction = 1 si retroceso alcista, -1 si retroceso bajista<br>
CurrentRetracement% = el porcentaje de retroceso actual desde el swing high o low<br>
DeepestRetracement% = el porcentaje de retroceso más profundo desde el swing high o low<br>

### Equal Highs/Lows

```python
smc.equal_highs_lows(ohlc, swing_highs_lows, tolerance=0.0001)
```

Este método identifica niveles donde hay múltiples swing highs o swing lows en el mismo precio,
indicando zonas de resistencia o soporte significativas.

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>
tolerance: float - la tolerancia para considerar que dos niveles son iguales (por defecto 0.0001)<br>

retorna:<br>
EqualLevel = 1 si equal highs, -1 si equal lows, 0 si no hay equal level<br>
Level = el nivel del equal high o low<br>
Count = el número de veces que se ha tocado este nivel<br>
FirstIndex = el índice de la primera vez que se tocó este nivel<br>
LastIndex = el índice de la última vez que se tocó este nivel<br>
Strength = la fuerza del nivel basada en el número de toques y la distancia temporal<br>

### Premium/Discount Zones

```python
smc.premium_discount_zones(ohlc, swing_highs_lows, lookback_period=50)
```

Este método identifica zonas donde el precio está considerado "caro" (premium) o "barato" (discount)
basándose en rangos de swing importantes. Las zonas se calculan usando el 50% del rango como punto de referencia.

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>
lookback_period: int - el número de velas hacia atrás para buscar el swing más relevante<br>

retorna:<br>
Zone = 1 si zona premium, -1 si zona discount, 0 si en el medio del rango<br>
RangeHigh = el swing high del rango de referencia<br>
RangeLow = el swing low del rango de referencia<br>
MidPoint = el punto medio (50%) del rango<br>
DistanceFromMid = la distancia porcentual desde el punto medio<br>
RangeStrength = la fuerza del rango basada en su tamaño y antigüedad<br>

### Trend Indicator (Indicador de Tendencia)

```python
smc.trend_indicator(ohlc, swing_highs_lows, lookback_period=20)
```

Este método combina múltiples elementos de Smart Money Concepts para determinar la dirección de la tendencia:
- Swing highs/lows más recientes
- Break of Structure (BOS)
- Change of Character (CHoCH)
- Fair Value Gaps
- Order Blocks
- Premium/Discount Zones

parámetros:<br>
swing_highs_lows: DataFrame - proporciona el dataframe de la función swing_highs_lows<br>
lookback_period: int - el número de velas hacia atrás para analizar la tendencia<br>

retorna:<br>
Trend = 1 si tendencia alcista, -1 si tendencia bajista, 0 si lateral<br>
Strength = fuerza de la tendencia (0-100)<br>
Confidence = confianza en la señal (0-100)<br>
LastBOS = último Break of Structure detectado<br>
LastCHOCH = último Change of Character detectado<br>
TrendChange = 1 si cambio de tendencia reciente, 0 si no<br>

## Ocultar Mensaje de Crédito

```bash
export SMC_CREDIT=0
```

Este método ocultará el mensaje de crédito cuando importes la biblioteca por primera vez.

## Contribuir

Por favor, siéntete libre de contribuir al proyecto. Creando tus propios indicadores o mejorando los existentes. Si tienes dificultades para encontrar algo que hacer, por favor revisa la pestaña de issues para cambios solicitados.

2. Estudia cómo está implementado.
3. Crea tu rama de características (git checkout -b my-new-feature).
4. Haz commit de tus cambios (git commit -am 'Add some feature').
5. Push a la rama (git push origin my-new-feature).
6. Crea un nuevo Pull Request.

Menos es más – cada pull request debe ser mínimo, enfocándose en una sola función o una pequeña característica. Los cambios grandes y generales no serán fusionados, ya que son más difíciles de revisar y mantener. ¡Manténlo simple y enfocado!

## Descargo de Responsabilidad

Este proyecto es solo para fines educativos. No uses este indicador como único tomador de decisiones para tus operaciones. Siempre usa una gestión de riesgo adecuada y haz tu propia investigación antes de hacer cualquier operación. El autor de este proyecto no es responsable de ninguna pérdida que puedas incurrir. 
