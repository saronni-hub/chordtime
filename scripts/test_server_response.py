#!/usr/bin/env python3
"""
Test directo del endpoint de download
"""

import requests
import json
import sys

print("Test directo del servidor ChordTime")
print("=" * 60)

# Primero verificar que el servidor está vivo
try:
    status = requests.get("http://localhost:8193/api/status", timeout=5)
    print(f"✅ Servidor activo: {status.json()}")
except Exception as e:
    print(f"❌ Servidor no responde: {e}")
    sys.exit(1)

# Simular una petición de download (como hace el frontend)
print("\nSimulando petición de download...")

# Usar una URL corta para test rápido
test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley

payload = {
    "url": test_url,
    "format": "mp3",
    "quality": "best",
    "detect_chords": True
}

try:
    response = requests.post(
        "http://localhost:8193/api/yt/download",
        json=payload,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Respuesta del servidor:")
        print(f"   - Tiene 'bpm': {'bpm' in data}")
        print(f"   - Tiene 'duration': {'duration' in data}")
        print(f"   - Tiene 'source': {'source' in data}")
        print(f"   - Tiene 'chords': {'chords' in data}")
        print(f"   - Tiene 'json': {'json' in data}")
        
        if 'bpm' in data:
            print(f"   - BPM value: {data['bpm']}")
        if 'duration' in data:
            print(f"   - Duration: {data['duration']}")
        if 'source' in data:
            print(f"   - Source: {data['source']}")
            
        # Verificar estructura
        if 'chords' in data and isinstance(data['chords'], list):
            print(f"   - Número de acordes: {len(data['chords'])}")
            if data['chords']:
                print(f"   - Primer acorde: {data['chords'][0]}")
                
        # ¿El JSON es array u objeto?
        if 'json' in data:
            if isinstance(data['json'], list):
                print(f"   - 'json' es array (lista de acordes)")
            elif isinstance(data['json'], dict):
                print(f"   - 'json' es objeto (estructura completa)")
    else:
        print(f"\n❌ Error: {response.text[:200]}")
        
except Exception as e:
    print(f"\n❌ Excepción: {e}")

print("\n" + "=" * 60)
print("Test completado")
print("=" * 60)