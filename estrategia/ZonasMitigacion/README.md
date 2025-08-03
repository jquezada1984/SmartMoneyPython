# 🎯 Estrategia de Zonas de Mitigación Multi-Timeframe

## 📋 Descripción General

Esta estrategia implementa un enfoque de **Smart Money Concepts (SMC)** que combina análisis de marcos superiores (HTF) con señales precisas en 5 minutos. La estrategia busca identificar zonas institucionales donde el precio puede reaccionar y generar oportunidades de trading de alta probabilidad.

## 🏗️ Arquitectura de la Estrategia

### 📊 PREPARACIÓN HTF (1H)
- **Determina tendencia**: Máximos y mínimos crecientes/decrecientes
- **Marca zonas institucionales**: Order Blocks, FVGs, Liquidity Zones
- **Confirma ruptura**: En 15M (MSS/BOS) para validar estructura HTF

### 🎯 SEÑALES LTF (5M)
1. **Break of Structure (BOS)**: Vela de impulso que rompe swing previo
2. **Pullback a Order Block**: Retroceso al rango marcado en HTF (61.8%-78.6% Fibonacci)
3. **Entrada en Fair Value Gap**: Toque de zona desequilibrada
4. **Reversión en Liquidity Grab**: Mecha que barre stops y patrón de rechazo

## 🔧 Parámetros Configurables

```python
params = dict(
    swing_length=5,        # Longitud para swing highs/lows
    lookback=20,          # Período de lookback
    buffer_size=1000,     # Tamaño del buffer de datos
    
    # Indicadores técnicos
    macd_fast=12,         # MACD línea rápida
    macd_slow=26,         # MACD línea lenta
    macd_signal=9,        # MACD línea señal
    rsi_period=14,        # Período RSI
    
    # Fibonacci
    fib_min=0.618,        # Nivel mínimo Fibonacci
    fib_max=0.786,        # Nivel máximo Fibonacci
    
    # Order Blocks
    ob_lookback=50,       # Lookback para Order Blocks
    
    # Fair Value Gaps
    fvg_lookback=30,      # Lookback para FVGs
    fvg_min_size=0.0001,  # Tamaño mínimo FVG
)
```

## 📈 Condiciones de Entrada

### 🚀 COMPRA (Long)

#### 1. Break of Structure (BOS)
- ✅ **Confirmación de BOS al alza** en 5M con vela de cuerpo amplio
- ✅ **MACD (12,26,9)**: Crossover alcista (línea MACD por encima de señal)
- ✅ **RSI (14)**: Debe superar 50 y mostrar momentum al alza
- 🎯 **Entrada**: Al cierre de la vela de confirmación

#### 2. Pullback a Order Block
- ✅ **Pullback** al rango marcado en HTF
- ✅ **Fibonacci 61.8%-78.6%**: Retroceso ideal
- ✅ **MACD**: Crossover alcista en pullback
- ✅ **RSI > 50**: Confirmando momentum
- 🎯 **Entrada**: En pullback leve dentro del Order Block

#### 3. Entrada en Fair Value Gap
- ✅ **FVG alcista**: Zona desequilibrada detectada
- ✅ **FVG rellenado**: Precio toca la zona
- ✅ **MACD**: Crossover cerca del FVG
- ✅ **RSI > 50**: Confirmando momentum
- 🎯 **Entrada**: Al tocar la zona del FVG

#### 4. Reversión en Liquidity Grab
- ✅ **Liquidity Grab**: Mecha que barre stops
- ✅ **Patrón de rechazo**: Pin bar o engulfing alcista
- ✅ **MACD**: Crossover después del rechazo
- ✅ **RSI > 50**: Confirmando momentum
- 🎯 **Entrada**: Después del patrón de rechazo

### 📉 VENTA (Short)

#### 1. Break of Structure (BOS)
- ✅ **BOS bajista**: Vela de impulso que cierre por debajo del swing low
- ✅ **MACD**: Crossover bajista (línea MACD cruza por debajo de señal)
- ✅ **RSI < 50**: Confirmando debilidad
- 🎯 **Entrada**: En el cierre de la vela de ruptura

#### 2. Pullback a Order Block
- ✅ **Pullback** al Order Block bajista
- ✅ **Fibonacci 61.8%-78.6%**: Retroceso ideal
- ✅ **MACD**: Crossover bajista en pullback
- ✅ **RSI < 50**: Confirmando debilidad
- 🎯 **Entrada**: En pullback al Order Block/FVG roto

## 🛡️ Gestión de Riesgo

### Stop Loss
- **Compras**: Justo fuera del swing previo o rango de Order Block
- **Ventas**: Justo fuera del swing previo o rango de Order Block

### Take Profit
- **TP1**: Objetivo mínimo de 1:2 RR (Risk:Reward)
- **TP2**: Idealmente en la siguiente demanda/resistencia HTF

### Monitoreo
- **15M/1H**: Si la estructura HTF falla (nuevo BOS contrario), cerrar manualmente

## 📊 Indicadores Técnicos

### MACD (12, 26, 9)
- **Crossover alcista**: Línea MACD cruza por encima de la señal
- **Crossover bajista**: Línea MACD cruza por debajo de la señal
- **Confirmación**: Cerca del cierre de la vela de impulso

### RSI (14)
- **Alcista**: Debe superar 50 y mostrar momentum al alza
- **Bajista**: Debe estar por debajo de 50 confirmando debilidad
- **Evitar**: Zonas de sobrecompra extrema (>70) o sobreventa extrema (<30)

## 🎯 Patrones de Velas

### Vela de Impulso
- **Cuerpo**: Al menos 60% del rango total
- **Colas**: Máximo 20% del rango cada una
- **Dirección**: Verde para alcista, roja para bajista

### Patrón de Rechazo
- **Pin Bar**: Mecha larga, cuerpo pequeño
- **Engulfing**: Vela que envuelve completamente la anterior
- **Confirmación**: En zonas de Order Block o FVG

## 🚀 Uso de la Estrategia

### Instalación
```bash
# Clonar el repositorio
git clone <repository-url>
cd SmartMoney

# Instalar dependencias
pip install -r requirements.txt
```

### Ejecución
```python
# Importar la estrategia
from estrategia.ZonasMitigacion.zonas_mitigacion_strategy_new import ZonasMitigacionStrategy

# Configurar Backtrader
cerebro = bt.Cerebro()
cerebro.addstrategy(ZonasMitigacionStrategy)

# Ejecutar
results = cerebro.run()
```

### Test
```bash
# Ejecutar test de la estrategia
python tests/test_zonas_mitigacion_new.py
```

## 📈 Resultados Esperados

### Métricas de Rendimiento
- **Win Rate**: >60% (objetivo)
- **Risk:Reward**: 1:2 mínimo
- **Sharpe Ratio**: >1.0
- **Max Drawdown**: <20%

### Señales por Día
- **Promedio**: 2-5 señales
- **Calidad**: Alta probabilidad en zonas institucionales
- **Filtros**: Múltiples confirmaciones requeridas

## 🔧 Optimización

### Parámetros a Ajustar
1. **swing_length**: Sensibilidad de swing highs/lows
2. **fib_min/fib_max**: Niveles de Fibonacci
3. **fvg_min_size**: Tamaño mínimo de FVG
4. **ob_lookback**: Período para Order Blocks

### Filtros Adicionales
1. **Volumen**: Confirmar con volumen alto
2. **Tendencia HTF**: Solo operar en dirección de la tendencia
3. **Horarios**: Evitar horarios de baja liquidez
4. **Noticias**: Filtro de eventos económicos

## ⚠️ Consideraciones

### Limitaciones
- Requiere datos de alta calidad
- Sensible a cambios de volatilidad
- Necesita suficiente historial para análisis HTF

### Riesgos
- Falsos breakouts en mercados laterales
- Slippage en entradas rápidas
- Gap risk en aperturas de mercado

## 📚 Referencias

- **Smart Money Concepts**: ICT, SMC
- **Multi-Timeframe Analysis**: Wyckoff, VSA
- **Risk Management**: Van Tharp, Alexander Elder

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles. 