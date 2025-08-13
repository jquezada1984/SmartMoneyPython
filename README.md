# 🚀 SmartMoneyPython

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.0.26-orange.svg)](setup.py)

**Obtención de indicadores basados en conceptos de Smart Money o ICT para análisis técnico avanzado**

## 📖 Descripción

SmartMoneyPython es una librería Python especializada en el análisis de **Smart Money Concepts (SMC)** e **Inner Circle Trader (ICT)** para trading automatizado y análisis técnico. La librería proporciona herramientas avanzadas para detectar patrones de mercado, niveles de liquidez, order blocks, fair value gaps y otros conceptos fundamentales utilizados por traders institucionales.

### 🎯 Características Principales

- 🔍 **Análisis SMC Completo**: Detección automática de patrones de Smart Money
- 📊 **Indicadores Técnicos**: MACD, RSI, análisis de tendencias multi-timeframe
- 🕯️ **Patrones de Velas**: Identificación de patrones japoneses clásicos
- 💰 **Order Blocks & Liquidez**: Detección de zonas de acumulación y distribución
- 📈 **Fair Value Gaps**: Identificación de gaps de valor justo
- 🎬 **Visualización Avanzada**: Generación de gráficos interactivos y frames PNG
- 🔌 **Integración MT5**: Conexión directa con MetaTrader 5
- 🤖 **Trading Automatizado**: Generación de señales y backtesting

## 🚀 Instalación

### Requisitos Previos

- Python 3.8 o superior
- MetaTrader 5 (para funcionalidades de conexión)

### Instalación Rápida

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/SmartMoneyPython.git
cd SmartMoneyPython

# Instalar dependencias
pip install -r requirements.txt

# Instalar el paquete en modo editable
pip install -e .
```

### Dependencias Principales

```bash
pip install pandas>=2.0.2 numpy>=1.24.3 numba>=0.58.1
pip install plotly>=5.15.0 kaleido>=0.2.1 imageio>=2.31.0
pip install MetaTrader5>=5.0.45 backtrader>=1.9.78.123
```

## 📚 Uso Rápido

### 1. Análisis Básico SMC

```python
from smartmoneyconcepts import smc
import pandas as pd

# Cargar datos
df = pd.read_csv("datos_eurusd.csv")

# Análisis SMC completo
smc_analysis = smc(df, swing_length=20)

# Acceder a indicadores específicos
fvg_data = smc_analysis['fvg']
order_blocks = smc_analysis['ob']
trend_data = smc_analysis['trend_indicator']
```

### 2. Patrones de Velas

```python
from smartmoneyconcepts import CandlestickPatterns

patterns = CandlestickPatterns(df)
hammer_signals = patterns.hammer()
engulfing_signals = patterns.engulfing()
doji_signals = patterns.doji()
```

### 3. Análisis de Mercado

```python
from smartmoneyconcepts import MarketAnalysisLib

market_analysis = MarketAnalysisLib()
trend_analysis = market_analysis.detect_trend(df, method='structural')
support_resistance = market_analysis.find_support_resistance(df)
```

### 4. Integración con MT5

```python
from connectors.mt5_connector import MT5Connector

# Conectar a MetaTrader 5
mt5 = MT5Connector()

# Obtener datos en tiempo real
df = mt5.get_data("EURUSD", "1h", 500)

# Análisis completo
analysis = mt5.analyze_smc(df)
signals = mt5.generate_signals(df, analysis)
```

## 🎨 Visualización y Generación de Gráficos

### Generar Frames PNG para Animaciones

El archivo `tests/smart01.py` es un **visualizador avanzado** que genera frames PNG para crear animaciones de análisis técnico.

#### 🚀 Ejecución Directa

```bash
# Desde el directorio raíz del proyecto
python tests/smart01.py

# O como módulo Python
python -m tests.smart01
```

#### 📊 Qué Genera

- **Frames PNG** en la carpeta `frames_png/`
- **Gráficos multi-panel** con candlesticks, MACD, RSI
- **Análisis SMC completo** (Order Blocks, Fair Value Gaps, Liquidez)
- **Tendencias multi-timeframe** (15M, 1H, 4H)
- **Señales de trading** con niveles de confianza
- **Indicadores técnicos** precalculados para optimización

#### 🔧 Requisitos Previos

```bash
# Instalar dependencias necesarias
pip install plotly kaleido pillow tqdm

# Asegurar que existe el archivo de datos
# tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv
```

#### 📁 Estructura de Salida

```
frames_png/
├── frame_0400.png    # Vela 400
├── frame_0401.png    # Vela 401
├── frame_0402.png    # Vela 402
└── ...               # Hasta la última vela
```

#### ⚙️ Configuración del Script

- **Ventana de análisis**: 100 velas por frame
- **Inicio**: Desde la vela 400 (configurable)
- **Resolución**: 800x900 píxeles
- **Tema**: Oscuro profesional
- **Indicadores**: MACD, RSI, tendencias híbridas

#### 🎯 Casos de Uso

1. **Análisis técnico avanzado** con múltiples timeframes
2. **Creación de GIFs** para presentaciones
3. **Backtesting visual** de estrategias SMC
4. **Documentación** de análisis de mercado
5. **Educación** en Smart Money Concepts

### Características de Visualización

- 📊 **Gráficos Multi-panel**: Candlesticks, MACD, RSI, tendencias
- 🎯 **Indicadores SMC**: Order Blocks, Fair Value Gaps, niveles de liquidez
- 📈 **Análisis Multi-timeframe**: 15M, 1H, 4H con tendencias híbridas
- 🚦 **Señales de Trading**: Marcadores visuales con niveles de confianza
- 🎨 **Tema Oscuro**: Interfaz profesional para análisis técnico

## 🏗️ Arquitectura del Proyecto

```
SmartMoneyPython/
├── smartmoneyconcepts/          # Librería principal SMC
│   ├── smc.py                  # Análisis SMC core
│   ├── candlestick_patterns.py # Patrones de velas
│   └── market_analysis_lib.py  # Análisis de mercado
├── estrategia/                  # Estrategias de trading
│   ├── momentum_smc_strategy_lib.py
│   └── zonas_mitigacion_strategy_lib.py
├── connectors/                  # Conectores externos
│   └── mt5_connector.py        # Conexión MetaTrader 5
├── tests/                      # Tests y ejemplos
│   ├── smart01.py             # Visualizador avanzado
│   └── strategies_examples/   # Ejemplos de estrategias
├── docs/                       # Documentación
└── requirements.txt            # Dependencias
```

## 🔧 Configuración

### Configuración de MetaTrader 5

```python
# config/mt5_config.py
MT5_CONFIG = {
    'login': 123456,
    'password': 'tu_password',
    'server': 'tu_broker',
    'timeout': 60000
}
```

### Variables de Entorno

```bash
# Configurar credenciales MT5
export MT5_LOGIN=123456
export MT5_PASSWORD=tu_password
export MT5_SERVER=tu_broker

# Desactivar créditos (opcional)
export SMC_CREDIT=0
```

## 📊 Ejemplos de Uso

### Estrategia de Momentum SMC

```python
from estrategia.momentum_smc_strategy_lib import MomentumSMCStrategyLib

strategy = MomentumSMCStrategyLib()

# Precalcular indicadores
indicators = strategy.precalculate_indicators(df)

# Analizar todas las estrategias
signals = strategy.analyze_all_strategies(df)

# Obtener resumen
summary = strategy.get_signal_summary(df)
print(f"Total señales: {summary['total_signals']}")
```

### Backtesting con Backtrader

```python
# Ejecutar ejemplo de backtesting
python tests/strategies_examples/backtrader_momentum_strategy_example.py
```

## 🧪 Testing

### Ejecutar Tests

```bash
# Test unitario básico
python tests/unit_tests.py

# Test de detección SMC
python tests/debug_smc_detection.py

# Test de validación de tendencias
python tests/test_trend_validation.py
```

### 🎬 Visualizador Avanzado (smart01.py)

El archivo `tests/smart01.py` es una herramienta especializada para generar visualizaciones profesionales de análisis técnico.

#### 🚀 Ejecución

```bash
# Opción 1: Ejecución directa
python tests/smart01.py

# Opción 2: Como módulo Python
python -m tests.smart01

# Opción 3: Desde directorio tests
cd tests
python smart01.py
```

#### 📋 Requisitos Específicos

```bash
# Dependencias adicionales para visualización
pip install plotly kaleido pillow tqdm

# Verificar archivo de datos
ls tests/test_data/EURUSD/EURUSD_5M_2025_filtrado_fast.csv
```

#### 🔍 Funcionalidades del Script

- **Análisis SMC completo** con indicadores precalculados
- **Gráficos multi-panel** (Candlesticks + MACD + RSI + 3 Tendencias)
- **Señales de trading** con niveles de confianza
- **Tendencias híbridas** en timeframes 15M, 1H, 4H
- **Generación automática** de frames PNG para animaciones

#### 📊 Salida Generada

```
✅ Frames PNG con MACD, RSI, TENDENCIA 15M/1H/4H y SEÑALES DE TRADING guardados en: frames_png/
📊 Total de frames generados: [número]
🎯 Señales de trading encontradas: [número]
```

### Generar GIFs y Visualizaciones

```bash
# Generar GIF original
python tests/generate_gif_original.py

# Generar GIF personalizado
python tests/generate_gif.py
```

## 📈 Roadmap

- [ ] **v0.1.0**: Integración completa con Binance API
- [ ] **v0.2.0**: Estrategias de trading automatizado
- [ ] **v0.3.0**: Dashboard web interactivo
- [ ] **v0.4.0**: Machine Learning para predicciones
- [ ] **v1.0.0**: Plataforma completa de trading

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

### Guías de Contribución

- Sigue el estilo de código existente
- Agrega tests para nuevas funcionalidades
- Actualiza la documentación según sea necesario
- Usa commits descriptivos

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- **Inner Circle Trader (ICT)** por los conceptos fundamentales
- **Comunidad de Smart Money Concepts** por la inspiración
- **Contribuidores** que han ayudado a mejorar este proyecto

## 📞 Soporte

- 📧 **Email**: [tu-email@ejemplo.com]
- 🐛 **Issues**: [GitHub Issues](https://github.com/tu-usuario/SmartMoneyPython/issues)
- 📚 **Documentación**: [docs/](docs/)
- 💬 **Discord**: [Enlace al servidor]

---

⭐ **¿Te gustó este proyecto? ¡Dale una estrella en GitHub!**

*Desarrollado con ❤️ por John Quezada*
