#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE PRUEBA PARA GENERACIÓN DE IMÁGENES ICC
===============================================

Este script prueba la funcionalidad de generación de imágenes
cuando se detectan señales ICC.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar el directorio raíz al path para importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar el generador de imágenes
from image_generator import generate_signal_image

def create_test_data():
    """Crear datos de prueba para simular señales ICC"""
    # Crear fechas de prueba (últimas 200 velas de 5 minutos)
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=200 * 5)
    
    # Generar timestamps cada 5 minutos
    timestamps = pd.date_range(start=start_time, end=end_time, freq='5T')
    
    # Crear datos OHLCV simulados
    np.random.seed(42)  # Para reproducibilidad
    
    # Precio base EURUSD
    base_price = 1.0850
    
    # Generar precios con tendencia alcista
    price_changes = np.random.normal(0.0001, 0.0005, len(timestamps))
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] + change
        prices.append(max(new_price, 1.0800))  # Mínimo 1.0800
    
    # Crear OHLCV
    data = []
    for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
        # Simular volatilidad
        volatility = 0.0003
        
        # Generar OHLC
        open_price = price
        high_price = price + abs(np.random.normal(0, volatility))
        low_price = price - abs(np.random.normal(0, volatility))
        close_price = price + np.random.normal(0, volatility * 0.5)
        
        # Asegurar que high >= max(open, close) y low <= min(open, close)
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Volumen simulado
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'datetime': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return data

def test_buy_signal():
    """Probar generación de imagen para señal de COMPRA"""
    print("🧪 Probando generación de imagen para señal de COMPRA...")
    
    # Crear datos de prueba
    test_data = create_test_data()
    
    # Crear señal de COMPRA simulada
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
        data_buffer=test_data,
        icc_signals=buy_signal,
        signal_type="COMPRA_TEST"
    )
    
    if image_filename:
        print(f"✅ Imagen de COMPRA generada exitosamente: {image_filename}")
        return True
    else:
        print("❌ Fallo en generación de imagen de COMPRA")
        return False

def test_sell_signal():
    """Probar generación de imagen para señal de VENTA"""
    print("🧪 Probando generación de imagen para señal de VENTA...")
    
    # Crear datos de prueba
    test_data = create_test_data()
    
    # Crear señal de VENTA simulada
    sell_signal = [{
        'direction': 'SHORT',
        'entry_price': 1.0825,
        'risk_management': {
            'stop_loss': 1.0850,
            'take_profit': 1.0800
        }
    }]
    
    # Generar imagen
    image_filename = generate_signal_image(
        data_buffer=test_data,
        icc_signals=sell_signal,
        signal_type="VENTA_TEST"
    )
    
    if image_filename:
        print(f"✅ Imagen de VENTA generada exitosamente: {image_filename}")
        return True
    else:
        print("❌ Fallo en generación de imagen de VENTA")
        return False

def test_no_signal():
    """Probar generación de imagen sin señales"""
    print("🧪 Probando generación de imagen sin señales...")
    
    # Crear datos de prueba
    test_data = create_test_data()
    
    # Generar imagen sin señales
    image_filename = generate_signal_image(
        data_buffer=test_data,
        icc_signals=[],
        signal_type="SIN_SEÑAL_TEST"
    )
    
    if image_filename:
        print(f"✅ Imagen sin señales generada exitosamente: {image_filename}")
        return True
    else:
        print("❌ Fallo en generación de imagen sin señales")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 INICIANDO PRUEBAS DE GENERACIÓN DE IMÁGENES ICC")
    print("=" * 60)
    
    # Contar imágenes existentes antes de las pruebas
    images_dir = "frames_png"
    if os.path.exists(images_dir):
        initial_images = len([f for f in os.listdir(images_dir) if f.startswith("ICC_Signal_")])
        print(f"📊 Imágenes existentes antes de las pruebas: {initial_images}")
    else:
        initial_images = 0
        print(f"📊 No hay directorio de imágenes existente")
    
    print()
    
    # Ejecutar pruebas
    test_results = []
    
    # Prueba 1: Señal de COMPRA
    test_results.append(test_buy_signal())
    print()
    
    # Prueba 2: Señal de VENTA
    test_results.append(test_sell_signal())
    print()
    
    # Prueba 3: Sin señales
    test_results.append(test_no_signal())
    print()
    
    # Mostrar resultados finales
    print("=" * 60)
    print("📊 RESULTADOS DE LAS PRUEBAS:")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results)
    failed_tests = total_tests - passed_tests
    
    print(f"   • Total de pruebas: {total_tests}")
    print(f"   • Pruebas exitosas: {passed_tests}")
    print(f"   • Pruebas fallidas: {failed_tests}")
    print(f"   • Tasa de éxito: {(passed_tests/total_tests)*100:.1f}%")
    
    # Contar imágenes generadas
    if os.path.exists(images_dir):
        final_images = len([f for f in os.listdir(images_dir) if f.startswith("ICC_Signal_")])
        new_images = final_images - initial_images
        print(f"\n🎨 IMÁGENES GENERADAS:")
        print(f"   • Imágenes antes: {initial_images}")
        print(f"   • Imágenes después: {final_images}")
        print(f"   • Nuevas imágenes: {new_images}")
        
        if new_images > 0:
            print(f"   • Directorio: {os.path.abspath(images_dir)}")
            
            # Mostrar archivos generados
            image_files = [f for f in os.listdir(images_dir) if f.startswith("ICC_Signal_")]
            image_files.sort()
            print(f"   • Archivos generados:")
            for img_file in image_files[-new_images:]:
                print(f"      - {img_file}")
    else:
        print(f"\n❌ No se pudo acceder al directorio de imágenes")
    
    # Resumen final
    if passed_tests == total_tests:
        print(f"\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS! El generador de imágenes funciona correctamente.")
    else:
        print(f"\n⚠️ Algunas pruebas fallaron. Revisar errores arriba.")
    
    return passed_tests == total_tests

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Pruebas interrumpidas por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado durante las pruebas: {e}")
        sys.exit(1)
