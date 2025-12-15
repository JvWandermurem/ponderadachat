import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega a chave do arquivo .env
load_dotenv()

# Configura a API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERRO: Chave GOOGLE_API_KEY não encontrada no .env")
    exit()

genai.configure(api_key=api_key)

print(f"--- Consultando modelos para a chave: {api_key[:5]}... ---")

try:
    # Lista todos os modelos disponíveis
    found = False
    for m in genai.list_models():
        # Filtra apenas modelos que geram texto (chat)
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            found = True
            
    if not found:
        print("Nenhum modelo de geração de texto encontrado para essa chave.")
        
except Exception as e:
    print(f"Erro ao conectar na API: {e}")