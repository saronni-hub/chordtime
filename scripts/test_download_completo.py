#!/usr/bin/env python3
"""
Test simple para ChordTime - Verificar descarga completa
"""

import requests
import json
import time

print("Test de descarga completa de ChordTime")
print("=" * 60)

# Primero, limpiar logs
print("Limpiando logs anteriores...")
open("/tmp/chordtime_test.log", "w").close()

# URL de prueba (corta)
test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up (4:01)

print(f"\nProbando con: {test_url}")

# Simular una petición de download
payload = {
    "url": test_url,
    "format": "mp3",
    "quality": "best",
    "detect_chords": True
}

print("\nEnviando petición de download...")
try:
    start_time = time.time()
    response = requests.post(
        "http://localhost:8193/api/yt/download",
        json=payload,
        timeout=120  # 2 minutos para descarga
    )
    elapsed = time.time() - start_time
    
    print(f"Tiempo de respuesta: {elapsed:.1f} segundos")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Download exitoso")
        print(f"   Archivo: {data.get('filename', 'N/A')}")
        print(f"   Acordes detectados: {data.get('chord_count', 0)}")
        print(f"   Duración: {data.get('duration', 'N/A')}")
        print(f"   BPM: {data.get('bpm', 'N/A')}")
        print(f"   Método: {data.get('source', 'N/A')}")
        
        # Verificar si es canción completa
        duration = data.get('duration', 0)
        if isinstance(duration, str):
            # Convertir "4:01" a segundos
            if ":" in duration:
                mins, secs = duration.split(":")
                duration_sec = int(mins) * 60 + int(secs)
            else:
                duration_sec = float(duration)
        else:
            duration_sec = float(duration)
            
        if duration_sec > 100:  # Más de 1:40
            print(f"✅ Parece canción completa (~{duration_sec:.0f}s)")
        else:
            print(f"⚠️  Duración corta ({duration_sec:.1f}s) - podría ser solo 90s")
            
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Respuesta: {response.text[:200]}")
        
except Exception as e:
    print(f"\n❌ Excepción: {e}")

print("\n" + "=" * 60)
print("Revisando logs...")
print("=" * 60)

try:
    with open("/tmp/chordtime_debug_detailed.log", "r") as f:
        lines = f.readlines()
        print(f"Total líneas en log: {len(lines)}")
        print("\nÚltimas 20 líneas relevantes:")
        for line in lines[-20:]:
            if any(keyword in line for keyword in ["Download", "Audio", "Duration", "File size", "Found:"]):
                print(f"  {line.strip()}")
except FileNotFoundError:
    print("Log file no encontrado")

print("\n" + "=" * 60)
print("Test completado")
print("=" * 60)