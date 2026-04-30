#!/usr/bin/env python3
"""
ChordTime Direct JSON Generator
Obtiene JSON completo con BPM directamente desde el servidor
(sin depender del navegador/cache)
"""

import requests
import json
import sys
import os

def get_chordtime_json(youtube_url, output_file=None):
    """
    Obtiene JSON completo de ChordTime para una URL de YouTube
    
    Args:
        youtube_url: URL de YouTube
        output_file: Archivo donde guardar JSON (opcional)
    
    Returns:
        Diccionario con chords, BPM, duration, etc.
    """
    
    print(f"🎵 Procesando: {youtube_url}")
    print("=" * 60)
    
    # Verificar que el servidor esté activo
    try:
        status = requests.get("http://localhost:8193/api/status", timeout=5)
        if status.status_code != 200:
            print(f"❌ Servidor no responde correctamente: {status.status_code}")
            return None
        print("✅ Servidor ChordTime activo")
    except Exception as e:
        print(f"❌ No se puede conectar al servidor: {e}")
        print("   Asegúrate de que chordtime_server.py esté ejecutándose")
        return None
    
    # Preparar petición de download
    payload = {
        "url": youtube_url,
        "format": "mp3",
        "quality": "best",
        "detect_chords": True
    }
    
    print("⬇️  Descargando y detectando acordes...")
    try:
        response = requests.post(
            "http://localhost:8193/api/yt/download",
            json=payload,
            timeout=300  # 5 minutos para descarga larga
        )
        
        if response.status_code != 200:
            print(f"❌ Error del servidor: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return None
        
        data = response.json()
        
        # Extraer información importante
        print(f"✅ Canción procesada exitosamente")
        print(f"   Duración: {data.get('duration', 'N/A')} segundos")
        print(f"   BPM: {data.get('bpm', 'N/A')}")
        print(f"   Método: {data.get('source', 'N/A')}")
        print(f"   Acordes detectados: {len(data.get('chords', []))}")
        
        # Crear estructura completa para JSON
        full_data = {
            "metadata": {
                "title": data.get('filename', '').replace('.mp3', ''),
                "duration": data.get('duration'),
                "bpm": data.get('bpm'),
                "source": data.get('source'),
                "timestamp": data.get('timestamp', '')
            },
            "chords": data.get('json', data.get('chords', [])),
            "raw_response": data  # Incluir respuesta completa
        }
        
        # Guardar en archivo si se especificó
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)
            print(f"💾 JSON guardado en: {output_file}")
            print(f"   Tamaño: {os.path.getsize(output_file)} bytes")
        
        return full_data
        
    except requests.exceptions.Timeout:
        print("❌ Timeout: La descarga tomó demasiado tiempo")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None

def main():
    """Función principal"""
    print("🎹 ChordTime Direct JSON Generator")
    print("=" * 60)
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("Uso: python3 chordtime_direct.py <URL_YOUTUBE> [archivo_salida.json]")
        print("\nEjemplos:")
        print("  python3 chordtime_direct.py https://www.youtube.com/watch?v=...")
        print("  python3 chordtime_direct.py https://youtu.be/... canciones.json")
        print("\nEl archivo de salida es opcional. Si no se especifica,")
        print("se mostrará el JSON en consola.")
        return
    
    youtube_url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Procesar
    result = get_chordtime_json(youtube_url, output_file)
    
    if result:
        print("\n" + "=" * 60)
        print("🎉 PROCESO COMPLETADO")
        print("=" * 60)
        
        if not output_file:
            # Mostrar JSON en consola
            print("\nJSON completo (primeros 2000 caracteres):")
            print("=" * 60)
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            print(json_str[:2000])
            if len(json_str) > 2000:
                print("... [truncado]")
        
        # Mostrar resumen
        print("\n📊 RESUMEN:")
        print(f"   • Duración: {result['metadata'].get('duration')}s")
        print(f"   • BPM: {result['metadata'].get('bpm')}")
        print(f"   • Acordes: {len(result['chords'])}")
        print(f"   • Método: {result['metadata'].get('source')}")
    else:
        print("\n❌ No se pudo obtener el JSON")
        sys.exit(1)

if __name__ == "__main__":
    main()