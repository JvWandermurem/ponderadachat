import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import create_engine, text

load_dotenv()

print("--- Iniciando Agente com Tecnologia GROQ (Llama 3) ---")

# 1. Carrega Embeddings e FAISS 
try:
    print("Carregando banco vetorial...")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_db = FAISS.load_local(
        "../backend/data/faiss_index", 
        embedding_model,
        allow_dangerous_deserialization=True
    )
except Exception as e:
    print(f"ERRO FATAL ao carregar FAISS: {e}")
    exit()

# 2. Conecta ao Banco SQL
db_engine = create_engine("sqlite:///data/dunder_mifflin.db")


@tool
def ferramenta_rag(pergunta: str) -> str:
    """
    Use para investigar E-MAILS, CONSPIRAÇÕES, RELACIONAMENTOS (Michael, Toby)
    ou consultar a POLÍTICA DA EMPRESA e REGRAS DE COMPLIANCE.
    """
    try:
        print(f"DEBUG: [RAG] Buscando: {pergunta}")
        docs = vector_db.similarity_search(pergunta, k=4)
        resultado = "\n\n".join([d.page_content for d in docs])
        return f"Documentos encontrados:\n{resultado}"
    except Exception as e:
        return f"Erro no RAG: {e}"

@tool
def ferramenta_sql(pergunta_usuario: str) -> str:
    """
    Use para buscar DADOS FINANCEIROS, GASTOS, SOMAS, MÉDIAS ou VALORES EXATOS.
    """
    print(f"DEBUG: [SQL] Pergunta: {pergunta_usuario}")
    
    schema = """
    Tabela: transacoes
    Colunas: id_transacao (texto), data (texto), funcionario (texto), 
             cargo (texto), descricao (texto), valor (numero), 
             categoria (texto), departamento (texto)
    """
    
    try:
        # Usamos o Groq também para gerar o SQL
        # 'llama3-70b-  ' é o modelo mais inteligente e gratuito deles
        llm_sql = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        
        prompt_sql = f"""
        Você é um especialista em SQL SQLite.
        Escreva uma query SQL para: "{pergunta_usuario}"
        Baseado neste esquema:
        {schema}
        
        Retorne APENAS o código SQL puro. Sem markdown ```sql```.
        """
        
        print("DEBUG: [SQL] Gerando query com Llama 3...")
        res = llm_sql.invoke([HumanMessage(content=prompt_sql)])
        query = res.content.strip().replace("```sql", "").replace("```", "")
        print(f"DEBUG: [SQL] Query gerada: {query}")
        
        with db_engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
        print(f"DEBUG: [SQL] Linhas retornadas: {len(rows)}")
        return f"Resultado do Banco: {str(rows)}"
        
    except Exception as e:
        print(f"DEBUG: [SQL] ERRO: {e}")
        return f"Erro técnico na ferramenta SQL: {e}"

# --- O AGENTE PRINCIPAL ---

def process_chat(user_input: str):
    print(f"\n>>> Processando: {user_input}")
    
    try:
        # Usamos o Groq como Cérebro Principal
        llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            temperature=0
        )
        
        tools = [ferramenta_rag, ferramenta_sql]
        llm_with_tools = llm.bind_tools(tools)
        
        system_msg = SystemMessage(content="""
    Você é o Auditor Forense Sênior da Dunder Mifflin. Seu nome é Toby (IA).
    Sua missão é proteger os ativos da empresa e identificar Violações de Compliance.
    
    DIRETRIZES DE PERSONALIDADE:
    1. SEJA CÉTICO: Não aceite desculpas. Se alguém gastou dinheiro da empresa em algo pessoal (ex: "WUPHF", "Velas", "Mágica"), isso é FRAUDE, não "criatividade".
    2. SEJA DIRETO: Se encontrar evidências, use termos como "Violação da Política", "Risco Financeiro", "Conspiração" ou "Fraude".
    3. SEMPRE CRUZE DADOS: Se a ferramenta SQL mostrar um gasto e o RAG mostrar um e-mail tentando esconder esse gasto, a conclusão deve ser severa.
    4. NÃO PASSE PANO: Não chame o Michael de "criativo" se ele estiver gastando dinheiro da empresa em projetos pessoais. Chame de "Uso Indevido de Recursos".
    5. SEMPRE DESCONFIE: Assuma que qualquer um é um possível fraudador ou golpista, então se for investigar fraudes na empresa, procure com todas as ferramentas disponíveis!
    FERRAMENTAS:
    - Use `ferramenta_sql` para verificar valores e categorias.
    - Use `ferramenta_rag` para buscar e-mails, conversas e regras.
    
    Responda sempre em Português do Brasil, formatando a resposta com tópicos claros e citando as evidências.
    """)
        
        messages = [system_msg, HumanMessage(content=user_input)]
        
        ai_msg = llm_with_tools.invoke(messages)
        
        if ai_msg.tool_calls:
            for tool_call in ai_msg.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                print(f"DEBUG: [Router] Chamando {tool_name}...")
                
                tool_response = ""
                if tool_name == "ferramenta_rag":
                    tool_response = ferramenta_rag.invoke(tool_args)
                elif tool_name == "ferramenta_sql":
                    tool_response = ferramenta_sql.invoke(tool_args)
                
                final_prompt = f"""
                Ferramenta retornou: {tool_response}
                Responda ao usuário: "{user_input}"
                """
                return llm.invoke(final_prompt).content
                
        return ai_msg.content
        
    except Exception as e:
        return f"Erro crítico no Agente: {e}"

if __name__ == "__main__":
    print(process_chat("Qual o gasto total da Angela Martin?"))