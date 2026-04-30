#!/usr/bin/env python3
"""
Prueba MiniMax con OpenAI-compatible API
"""

from langchain_openai import ChatOpenAI
import os

# Configuración MiniMax (API compatible con OpenAI)
os.environ["OPENAI_API_KEY"] = "sk-cp-YiuTgsecfJHhaGetfvpXwyntOzf3zGqq4nn7XNvIgzT9lBQ8CwIH0NhWqCETYIDi4UaHS3BYZzuo1vWFZMaWtNXeROsZyL91AUivexPAEyUCqIm2NUY0ehI"

print("🤖 Probando MiniMax M2.7...")

try:
    # MiniMax tiene endpoint compatible con OpenAI
    llm = ChatOpenAI(
        model="MiniMax-M2.7",
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://api.minimax.chat/v1",  # Endpoint de MiniMax
        temperature=0.7,
        max_tokens=500,
    )
    
    # Prueba simple
    respuesta = llm.invoke("¿Qué es CrewAI? Responde en una frase.")
    print("✅ ¡Funciona!")
    print("Respuesta:", respuesta.content)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPosibles problemas:")
    print("1. API key incorrecta")
    print("2. Modelo no disponible")
    print("3. Endpoint incorrecto")
    print("4. Sin conexión a internet")