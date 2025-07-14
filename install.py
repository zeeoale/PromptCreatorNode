
# install.py
# Installa tutte le librerie necessarie per PromptCreatorNode
import subprocess

libs = [
    "openai",
    "cohere",
    "google-generativeai"
]

for lib in libs:
    try:
        subprocess.check_call(["pip", "install", lib])
    except Exception as e:
        print(f"Errore installando {lib}: {e}")
