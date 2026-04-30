#!/usr/bin/env python3
"""
Prueba DeepSeek API
"""

from langchain_openai import ChatOpenAI
import os

api_key = "sk-81bee82b9636458f90878f520a279638"

print("🤖 Probando DeepSeek API...")

try:
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=0.7,
        max_tokens=100,
        timeout=10,
    )
    
    respuesta = llm.invoke("Hola, ¿puedes decirme qué es CrewAI en una frase?")
    print("✅ ¡Funciona!")
    print("Respuesta:", respuesta.content)
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPosibles problemas:")
    print("1. API key incorrecta o expirada")
    print("2. Sin conexión a internet")
    print("3. Límite de tokens alcanzado")