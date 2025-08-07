# Ejemplos de Estrategias de Trading

Esta carpeta contiene ejemplos de estrategias de trading que utilizan las librerías de Smart Money Concepts.

## Archivos

### `backtrader_momentum_strategy_example.py`
**Propósito**: Ejemplo de estrategia de Backtrader que utiliza la librería `MomentumSMCStrategyLib`

**Características**:
- Utiliza la librería `MomentumSMCStrategyLib` para calcular señales de trading
- Implementa las tres estrategias principales:
  - **Estrategia 1**: BOS + Vela de Impulso
  - **Estrategia 2**: Order Block + Fibonacci
  - **Estrategia 3**: Fair Value Gap (FVG)
- Incluye gestión de riesgo simplificada para el ejemplo
- Mantiene la funcionalidad de Backtrader para backtesting

**Uso**:
```python
# Ejemplo de uso con Backtrader
import backtrader as bt
from strategies_examples.backtrader_momentum_strategy_example import MomentumSMCStrategyExample

# Configurar cerebro de Backtrader
cerebro = bt.Cerebro()
cerebro.addstrategy(MomentumSMCStrategyExample)

# Agregar datos y ejecutar
cerebro.run()
cerebro.plot()
```

## Librería Utilizada

### `MomentumSMCStrategyLib`
**Ubicación**: `estrategia/Momentum/momentum_smc_strategy_lib.py`

**Propósito**: Librería independiente que proporciona:
- Cálculo de señales para las tres estrategias
- Análisis de confianza para cada señal
- Resumen estadístico de señales encontradas
- Funciones auxiliares para indicadores técnicos

**Uso Directo**:
```python
from estrategia.Momentum.momentum_smc_strategy_lib import MomentumSMCStrategyLib

# Inicializar librería
strategy_lib = MomentumSMCStrategyLib()

# Analizar datos
signals = strategy_lib.analyze_all_strategies(df)

# Obtener resumen
summary = strategy_lib.get_signal_summary(df)
```

## Estructura de Archivos

```
tests/
├── strategies_examples/
│   ├── __init__.py
│   ├── README.md
│   └── backtrader_momentum_strategy_example.py
└── smart01.py (visualización con señales)

estrategia/
└── Momentum/
    └── momentum_smc_strategy_lib.py (librería principal)
```

## Diferencias con la Versión Anterior

### Antes:
- `estrategia/Momentum/momentum_smc_strategy.py` contenía tanto la estrategia de Backtrader como la lógica de cálculo
- La lógica de cálculo estaba mezclada con la implementación de Backtrader

### Ahora:
- **Librería independiente**: `momentum_smc_strategy_lib.py` contiene solo la lógica de cálculo
- **Ejemplo de Backtrader**: `backtrader_momentum_strategy_example.py` muestra cómo usar la librería con Backtrader
- **Visualización**: `tests/smart01.py` utiliza la librería para mostrar señales en gráficos

## Ventajas de la Nueva Estructura

1. **Separación de responsabilidades**: La lógica de cálculo está separada de la implementación específica
2. **Reutilización**: La librería puede usarse en diferentes contextos (Backtrader, visualización, etc.)
3. **Mantenibilidad**: Es más fácil mantener y actualizar la lógica de cálculo
4. **Testabilidad**: Se puede probar la lógica de cálculo independientemente
5. **Flexibilidad**: Se pueden crear diferentes implementaciones usando la misma librería

## Próximos Pasos

1. Crear más ejemplos de estrategias
2. Agregar tests unitarios para la librería
3. Documentar mejor las funciones de la librería
4. Crear ejemplos de integración con otros frameworks 