#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUEBA ICC SMARTMONEY CON PROGRESO VISUAL
=========================================

Este script ejecuta la prueba ICC con indicadores de progreso visual
usando tqdm para mostrar el avance del backtesting de manera más clara.
"""

import sys
import os
import time
from tqdm import tqdm
import subprocess
import threading
import queue

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_with_progress():
    """Ejecutar prueba_icc.py con barra de progreso visual"""
    
    print("🎯 PRUEBA ICC SMARTMONEY CON PROGRESO VISUAL")
    print("=" * 60)
    print("Este script ejecuta la estrategia ICC SmartMoney con indicadores")
    print("de progreso visual para monitorear el avance del backtesting.")
    print("=" * 60)
    
    # Verificar que existe el archivo principal
    main_script = "tests/ _icc.py"
    if not os.path.exists(main_script):
        print(f"❌ Error: No se encontró el archivo {main_script}")
        return False
    
    print(f"📂 Archivo principal: {main_script}")
    print(f"🚀 Iniciando ejecución con progreso visual...")
    print("-" * 60)
    
    try:
        # Ejecutar el script principal
        start_time = time.time()
        
        # Usar subprocess para ejecutar el script
        process = subprocess.Popen(
            [sys.executable, main_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Leer la salida en tiempo real
        progress_bar = None
        current_line = 0
        
        print("🔄 Ejecutando backtesting...")
        print("   📊 El progreso se mostrará en tiempo real")
        print("   ⏳ Esto puede tomar varios minutos...")
        print("-" * 60)
        
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                # Detectar líneas de progreso específicas
                if "📊 Progreso:" in line:
                    # Extraer información de progreso
                    try:
                        # Buscar el patrón "Progreso: X/Y (Z%)"
                        if "Progreso:" in line and "(" in line and ")" in line:
                            progress_part = line.split("Progreso:")[1].split("(")[0].strip()
                            current, total = map(int, progress_part.split("/"))
                            percentage = (current / total) * 100
                            
                            # Actualizar o crear barra de progreso
                            if progress_bar is None:
                                progress_bar = tqdm(
                                    total=total,
                                    desc="Backtesting ICC",
                                    unit="velas",
                                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                                )
                            
                            progress_bar.n = current
                            progress_bar.refresh()
                            
                            # Mostrar información adicional
                            if "Operaciones:" in line:
                                ops_part = line.split("Operaciones:")[1].strip()
                                print(f"   🎯 {ops_part}")
                    except:
                        pass
                
                # Mostrar otras líneas importantes
                elif any(keyword in line for keyword in [
                    "🚀 Estrategia ICC SmartMoney inicializada",
                    "🔍 Analizando SmartMoney ICC",
                    "🎯 SEÑAL SMARTMONEY",
                    "🟢 COMPRA EJECUTADA",
                    "🔴 VENTA EJECUTADA",
                    "📊 TRADE CERRADO",
                    "⏱️ Tiempo de ejecución",
                    "📊 RESULTADOS DEL BACKTESTING"
                ]):
                    print(f"   {line}")
                
                # Mostrar errores
                elif "❌" in line or "⚠️" in line:
                    print(f"   {line}")
                
                current_line += 1
        
        # Esperar a que termine el proceso
        process.wait()
        end_time = time.time()
        
        # Cerrar barra de progreso si existe
        if progress_bar:
            progress_bar.close()
        
        print("-" * 60)
        print(f"⏱️ Tiempo total de ejecución: {end_time - start_time:.2f} segundos")
        
        # Verificar el código de salida
        if process.returncode == 0:
            print("✅ Backtesting completado exitosamente")
            return True
        else:
            print(f"❌ Backtesting falló con código de salida: {process.returncode}")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Ejecución interrumpida por el usuario")
        if progress_bar:
            progress_bar.close()
        return False
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        if progress_bar:
            progress_bar.close()
        return False

def show_help():
    """Mostrar ayuda del script"""
    print("🎯 PRUEBA ICC SMARTMONEY CON PROGRESO VISUAL")
    print("=" * 50)
    print("Uso: python -m tests.prueba_icc_progress")
    print("")
    print("Este script ejecuta la estrategia ICC SmartMoney con:")
    print("   📊 Barra de progreso visual en tiempo real")
    print("   🔍 Monitoreo de análisis SmartMoney")
    print("   🎯 Seguimiento de operaciones")
    print("   ⏱️ Medición de tiempo de ejecución")
    print("")
    print("Características:")
    print("   ✅ Progreso visual con tqdm")
    print("   ✅ Información en tiempo real")
    print("   ✅ Detección de señales SmartMoney")
    print("   ✅ Seguimiento de operaciones")
    print("   ✅ Métricas de rendimiento")
    print("")
    print("Para más información, revisa el archivo prueba_icc.py")

if __name__ == '__main__':
    """Función principal"""
    try:
        # Verificar argumentos
        if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
            show_help()
            sys.exit(0)
        
        # Ejecutar con progreso
        success = run_with_progress()
        
        if success:
            print(f"\n🎉 ¡Proceso completado exitosamente!")
            print(f"   📊 Revisa los resultados arriba")
            print(f"   💡 Para ver el gráfico, ejecuta: python -m tests.prueba_icc")
        else:
            print(f"\n❌ El proceso falló")
            print(f"   💡 Revisa los errores arriba")
            print(f"   🔧 Para ejecutar sin progreso: python -m tests.prueba_icc")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
