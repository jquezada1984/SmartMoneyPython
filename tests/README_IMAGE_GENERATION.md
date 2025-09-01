# Generación Automática de Imágenes para Señales ICC

## Descripción

Este módulo implementa la generación automática de imágenes de gráficos cuando se detectan señales de compra o venta en la estrategia ICC SmartMoney, similar a como lo hace `implementacion_icc.py`.

## Características

### 🎨 Generación Automática de Imágenes

La funcionalidad se activa automáticamente en los siguientes momentos:

1. **Al detectar una señal ICC** - Se genera una imagen mostrando la señal detectada
2. **Al ejecutar una orden** - Se genera una imagen de confirmación con el precio real de ejecución
3. **Al cerrar un trade** - Se genera una imagen del cierre con el resultado
4. **Al cierre manual del backtesting** - Se genera una imagen del cierre final

### 📊 Contenido de las Imágenes

Cada imagen generada incluye:

- **Gráfico principal**: Candlesticks de EURUSD con las últimas 100 velas
- **Indicadores técnicos**: MACD y RSI en paneles separados
- **Señales ICC**: Marcadores de entrada, Stop Loss y Take Profits (R:R 1:1, 1:2, 1:3)
- **Información de la señal**: Dirección, precio de entrada, niveles de riesgo
- **Título descriptivo**: Incluye el tipo de señal y precio de entrada

### 🎯 Tipos de Señales Visualizadas

- **COMPRA (LONG)**: Marcador verde ▲ con niveles de TP por encima
- **VENTA (SHORT)**: Marcador rojo ▼ con niveles de TP por debajo
- **Stop Loss**: Marcador X rojo/verde según dirección
- **Take Profits**: Estrellas verdes/rojas para R:R 1:1, 1:2, 1:3

## Archivos del Sistema

### `image_generator.py`
Módulo principal que contiene:
- `generate_signal_image()`: Función principal para generar imágenes
- `add_icc_signals()`: Agregar señales ICC al gráfico
- `calculate_macd()` y `calculate_rsi()`: Cálculo de indicadores técnicos

### `prueba_icc.py` (Modificado)
Estrategia ICC que ahora incluye:
- Generación automática de imágenes al detectar señales
- Generación de imágenes de confirmación al ejecutar órdenes
- Generación de imágenes de cierre de trades
- Generación de imágenes de cierre manual

### `test_image_generation.py`
Script de pruebas que verifica:
- Generación de imágenes para señales de COMPRA
- Generación de imágenes para señales de VENTA
- Generación de imágenes sin señales
- Funcionamiento correcto del sistema

## Uso

### 1. Ejecutar Backtesting Normal

```bash
cd tests
python prueba_icc.py
```

Las imágenes se generarán automáticamente en el directorio `frames_png/`.

### 2. Probar Solo la Generación de Imágenes

```bash
cd tests
python test_image_generation.py
```

### 3. Ver Imágenes Generadas

Las imágenes se guardan en `frames_png/` con nombres descriptivos:
- `ICC_Signal_YYYYMMDD_HHMMSS_COMPRA.png`
- `ICC_Signal_YYYYMMDD_HHMMSS_VENTA.png`
- `ICC_Signal_YYYYMMDD_HHMMSS_CONFIRMACION.png`
- `ICC_Signal_YYYYMMDD_HHMMSS_CIERRE.png`

## Configuración

### Parámetros de Imagen

- **Resolución**: 1000x700 píxeles
- **Tema**: Plotly Dark (fondo oscuro)
- **Formato**: PNG
- **Ventana de visualización**: Últimas 100 velas
- **Indicadores**: MACD (12,26,9) y RSI (14)

### Directorio de Salida

```python
images_dir = "frames_png"  # Directorio donde se guardan las imágenes
```

## Dependencias

El sistema requiere las siguientes librerías (ya incluidas en `requirements.txt`):

- `plotly>=5.15.0` - Generación de gráficos interactivos
- `kaleido>=0.2.1` - Exportación de imágenes estáticas
- `pandas>=2.0.2` - Manipulación de datos
- `numpy>=1.24.3` - Cálculos numéricos
- `Pillow>=10.0.0` - Procesamiento de imágenes

## Ejemplo de Uso en Código

```python
from image_generator import generate_signal_image

# Generar imagen para una señal de compra
buy_signal = [{
    'direction': 'LONG',
    'entry_price': 1.0875,
    'risk_management': {
        'stop_loss': 1.0850,
        'take_profit': 1.0900
    }
}]

# Generar imagen
image_filename = generate_signal_image(
    data_buffer=data_buffer,
    icc_signals=buy_signal,
    signal_type="COMPRA"
)

if image_filename:
    print(f"Imagen generada: {image_filename}")
```

## Ventajas del Sistema

### ✅ Automatización Completa
- No requiere intervención manual
- Se integra perfectamente con la estrategia ICC existente

### ✅ Visualización Profesional
- Gráficos de calidad profesional
- Indicadores técnicos claros
- Marcadores de señales intuitivos

### ✅ Trazabilidad Completa
- Registro visual de todas las operaciones
- Historial completo de señales y ejecuciones
- Análisis posterior de decisiones de trading

### ✅ Fácil Análisis
- Imágenes listas para presentaciones
- Documentación visual de estrategias
- Análisis de patrones de entrada/salida

## Solución de Problemas

### Error: "No se pudo generar la imagen"
- Verificar que `plotly` y `kaleido` estén instalados
- Comprobar permisos de escritura en el directorio
- Verificar que haya suficientes datos en el buffer

### Error: "Directorio no encontrado"
- El directorio `frames_png` se crea automáticamente
- Verificar permisos de creación de directorios

### Imágenes de baja calidad
- Ajustar parámetros de resolución en `generate_signal_image()`
- Verificar configuración de `kaleido`

## Notas de Desarrollo

- El sistema mantiene la compatibilidad con la estrategia ICC existente
- Las imágenes se generan de forma asíncrona para no afectar el rendimiento
- Se incluye manejo de errores robusto para evitar fallos en el backtesting
- El formato de imagen PNG es ideal para análisis y presentaciones

## Futuras Mejoras

- [ ] Soporte para múltiples timeframes en una sola imagen
- [ ] Animaciones GIF de la evolución de señales
- [ ] Exportación a formatos adicionales (PDF, SVG)
- [ ] Personalización de temas y colores
- [ ] Integración con sistemas de notificación
