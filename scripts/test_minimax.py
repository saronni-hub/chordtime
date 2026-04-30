#!/usr/bin/env python3
"""
CrewAI con MiniMax M2.7 - Script de prueba
"""

from crewai import Agent, Task, Crew, Process
from langchain_community.chat_models import ChatMiniMax
import os

# Configuración MiniMax
os.environ["MINIMAX_API_KEY"] = "sk-cp-YiuTgsecfJHhaGetfvpXwyntOzf3zGqq4nn7XNvIgzT9lBQ8CwIH0NhWqCETYIDi4UaHS3BYZzuo1vWFZMaWtNXeROsZyL91AUivexPAEyUCqIm2NUY0ehI"
os.environ["MINIMAX_GROUP_ID"] = ""  # Déjalo vacío si no tienes

# Modelo MiniMax
llm = ChatMiniMax(
    model="MiniMax-M2.7",
    api_key=os.environ["MINIMAX_API_KEY"],
    group_id=os.environ.get("MINIMAX_GROUP_ID", ""),
    temperature=0.7,
    max_tokens=1000,
)

# Agente simple de prueba
agente_prueba = Agent(
    role="Asistente de prueba",
    goal="Responder preguntas simples",
    backstory="Eres un asistente útil que responde preguntas.",
    llm=llm,
    verbose=True,
)

# Tarea simple
tarea_prueba = Task(
    description="Responde: ¿Qué es CrewAI?",
    agent=agente_prueba,
    expected_output="Explicación breve de CrewAI",
)

# Ejecutar prueba
print("🤖 Probando conexión con MiniMax M2.7...")
try:
    crew = Crew(
        agents=[agente_prueba],
        tasks=[tarea_prueba],
        process=Process.sequential,
        verbose=True,
    )
    resultado = crew.kickoff()
    print("\n✅ ¡Funciona!")
    print("Resultado:", resultado)
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nPosibles soluciones:")
    print("1. Verifica tu API key de MiniMax")
    print("2. Asegúrate de que el modelo 'MiniMax-M2.7' existe")
    print("3. Comprueba tu conexión a internet")