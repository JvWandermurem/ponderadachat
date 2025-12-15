from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents import process_chat 

app = FastAPI(title="Auditoria Toby API")

# Configuração de CORS (Permite que o React converse com o Python)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, troque pelo domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserMessage(BaseModel):
    message: str

@app.get("/")
def health_check():
    return {"status": "Dunder Mifflin API Online"}

@app.post("/chat")
def chat_endpoint(body: UserMessage):
    """
    Endpoint principal. Recebe { "message": "texto" } e retorna a resposta do Agente.
    """
    try:
        print(f"Recebendo mensagem: {body.message}")
        resposta_agente = process_chat(body.message)
        return {"response": resposta_agente}
    except Exception as e:
        print(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Roda o servidor na porta 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)