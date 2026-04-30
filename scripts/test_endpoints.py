#!/usr/bin/env python3
"""
Prueba diferentes endpoints de MiniMax
"""

from langchain_openai import ChatOpenAI
import os

api_key = "sk-cp-YiuTgsecfJHhaGetfvpXwyntOzf3zGqq4nn7XNvIgzT9lBQ8CwIH0NhWqCETYIDi4UaHS3BYZzuo1vWFZMaWtNXeROsZyL91AUivexPAEyUCqIm2NUY0ehI"

endpoints = [
    "https://api.minimax.chat/v1",
    "https://api.minmax.chat/v1", 
    "https://api.minimax.com/v1",
    "https://api.minimaxglobal.com/v1",
    "https://openapi.minimax.chat/v1",
]

print("🔍 Probando endpoints de MiniMax Global...")

for endpoint in endpoints:
    print(f"\n📡 Probando: {endpoint}")
    try:
        llm = ChatOpenAI(
            model="MiniMax-M2.7",
            api_key=api_key,
            base_url=endpoint,
            temperature=0.7,
            max_tokens=100,
            timeout=10,
        )
        respuesta = llm.invoke("Hola")
        print(f"✅ ¡Funciona! Respuesta: {respuesta.content[:50]}...")
        break
    except Exception as e:
        print(f"❌ Error: {str(e)[:80]}")

print("\n---")
print("Si todos fallan, la key puede estar:")
print("1. Expirada")
print("2. De otra región (China vs Global)")
print("3. Necesita group_id")
print("4. Del proveedor equivocado")