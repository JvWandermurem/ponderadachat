import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from sqlalchemy import create_engine, text

load_dotenv()

print("--- Iniciando Agente Auditor (Dunder Mifflin) ---")

try:
    print("Carregando banco vetorial (RAG)...")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    # Garanta que o caminho aqui está igual ao que você usou no ingest_data.py
    vector_db = FAISS.load_local(
        "../backend/data/faiss_index", 
        embedding_model,
        allow_dangerous_deserialization=True
    )
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível carregar o FAISS. Rode o ingest_data.py primeiro. Detalhe: {e}")
    vector_db = None

db_engine = create_engine("sqlite:///data/dunder_mifflin.db")

# LLM Principal
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


@tool
def ferramenta_rag(pergunta: str) -> str:
    """
    Use esta ferramenta para consultar a POLÍTICA DE COMPLIANCE, REGRAS DA EMPRESA
    ou buscar contextos em E-MAILS antigos.
    """
    if not vector_db: return "Erro: Banco vetorial indisponível."
    
    try:
        # Busca documentos relevantes
        docs = vector_db.similarity_search(pergunta, k=5)
        conteudo = "\n---\n".join([d.page_content for d in docs])
        return f"CONTEXTO ENCONTRADO NOS DOCUMENTOS:\n{conteudo}"
    except Exception as e:
        return f"Erro na busca vetorial: {e}"

@tool
def ferramenta_sql(query_natural: str) -> str:
    """
    Use esta ferramenta para consultar o BANCO DE DADOS financeiro.
    """
    schema = """
    Tabela: transacoes
    Colunas: id_transacao, data (TEXTO formato YYYY-MM-DD), funcionario, cargo, descricao, valor, categoria, departamento
    """
    try:
        prompt_sql = f"""
        Você é um Data Scientist SQL Sênior. Converta a pergunta em SQL SQLite.
        Schema: {schema}
        Pergunta: "{query_natural}"
        
        REGRAS CRÍTICAS (PARA EVITAR ERROS):
        1. O ANO É 2008.
        2. NÃO EXISTE COLUNA 'ano'. A data é uma STRING 'YYYY-MM-DD'.
        3. Para filtrar por ano, use: "data LIKE '2008%'" (NUNCA use YEAR() ou EXTRACT()).
        4. Retorne APENAS o código SQL puro.
        5. Sempre adicione LIMIT 10 no final.
        """
        response_sql = llm.invoke(prompt_sql).content
        sql_query = response_sql.strip().replace("```sql", "").replace("```", "")
        
        # Garante o limite e corrige alucinação de 'NOW'
        if 'limit' not in sql_query.lower() and not any(agg in sql_query.upper() for agg in ['SUM', 'COUNT', 'AVG']):
            sql_query += " LIMIT 10"
        
        print(f"DEBUG SQL GERADO: {sql_query}")

        with db_engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = [dict(row._mapping) for row in result]
            
        return f"RESULTADO DO BANCO (Amostra):\n{str(rows)}" 
    except Exception as e:
        return f"Erro SQL: {e}"

@tool
def verificar_quebras_compliance(dummy: str = "") -> str:
    """
    Auditoria Automática.
    Analisa a política (RAG) e gera SQL para encontrar violações (ex: limites de valor, categorias proibidas).
    """
    print("DEBUG: Iniciando Auditoria de Compliance (Nível 3.1)...")
    
    # 1. Busca as regras no texto
    regras = ferramenta_rag.invoke("Quais são os limites de valores para jantar e quais categorias de gastos são estritamente proibidas?")
    
    # 2. Força o LLM a pensar como um Auditor SQL
    prompt_analise = f"""
    Use as regras abaixo para criar uma query SQL que pegue os infratores na tabela 'transacoes'.
    
    REGRAS RECUPERADAS:
    {regras}
    
    SUA TAREFA:
    Escreva uma query SQL (SQLite) que selecione transações que:
    1. Ultrapassem o valor numérico citado nas regras (ex: se o limite é 100, busque > 100).
    2. Pertençam a categorias proibidas mencionadas (ex: se diz "proibido entretenimento", busque categoria='Entretenimento').
    3. Contenham palavras proibidas na coluna 'descricao' (ex: "Mágica", "Festa").
    
    Retorne APENAS o SQL. Adicione LIMIT 10 no final.
    """
    
    sql_violation = llm.invoke(prompt_analise).content.strip().replace("```sql", "").replace("```", "")
    
    # Garante o LIMIT para não quebrar a API da Groq
    if 'limit' not in sql_violation.lower():
        sql_violation += " LIMIT 10"
    
    print(f"DEBUG SQL COMPLIANCE: {sql_violation}")
    
    try:
        with db_engine.connect() as conn:
            result = conn.execute(text(sql_violation))
            infratores = [dict(row._mapping) for row in result]
            
        if not infratores:
            return "Auditoria automática: Nenhuma violação óbvia encontrada baseada nas regras atuais."
        
        return f"Encontrei {len(infratores)} violações (Amostra de 10):\n{str(infratores)}"
    except Exception as e:
        return f"Erro na verificação: {e}"

@tool
def auditoria_cruzada_emails_banco(dummy: str = "") -> str:
    """
    Auditoria Cruzada (Emails x Banco).
    """
    print("DEBUG: Iniciando Auditoria Cruzada...")
    
    # Passo 1: RAG com termos genéricos de fraude
    termos = "esconder, segredo, não conte, nota fiscal, reembolso, posso comprar, lança como, magic"
    emails_suspeitos = ferramenta_rag.invoke(f"Busque e-mails contendo: {termos}")
    
    # Passo 2: Extração
    prompt_extracao = f"""
    Analise os e-mails e encontre intenções de fraude.
    E-mails: {emails_suspeitos}
    Retorne resumo: Quem, Item, Valor (se houver).
    """
    analise_emails = llm.invoke(prompt_extracao).content
    
    # Passo 3: SQL com instrução de data estrita
    prompt_verificacao = f"""
    Com base na análise: "{analise_emails}", gere SQL para validar a compra na tabela 'transacoes'.
    
    REGRAS DE OURO SQLITE:
    - NÃO USE funções de data (YEAR, NOW).
    - Para filtrar data, use: data LIKE '2008%'
    - Procure pelo funcionario E (descricao ou categoria ou valor).
    - Retorne APENAS SQL com LIMIT 10.
    """
    
    sql_check = llm.invoke(prompt_verificacao).content.strip().replace("```sql", "").replace("```", "")
    print(f"DEBUG SQL CRUZADO: {sql_check}")
    
    try:
        with db_engine.connect() as conn:
            result = conn.execute(text(sql_check))
            confirmados = [dict(row._mapping) for row in result]
            
        if not confirmados:
            return f"Analisei os e-mails, mas a query SQL não retornou transações. SQL Usado: {sql_check}. Contexto: {analise_emails}"
        
        return f"FRAUDE CONFIRMADA: E-mail suspeito cruzado com transação real!\nTransação: {str(confirmados)}\nContexto do E-mail: {analise_emails}"
            
    except Exception as e:
        return f"Erro na auditoria cruzada: {e}"


def process_chat(user_input: str) -> str:
    """
    Função principal chamada pela API.
    """
    print(f"\n>>> Processando mensagem do usuário: {user_input}")
    
    # Lista de ferramentas disponíveis para o "Cérebro"
    tools = [
        ferramenta_rag, 
        ferramenta_sql, 
        verificar_quebras_compliance, 
        auditoria_cruzada_emails_banco
    ]
    
    # "Bind" das ferramentas ao modelo
    llm_with_tools = llm.bind_tools(tools)
    
    system_msg = SystemMessage(content="""
    Você é o Agente de Auditoria Inteligente do Toby Flenderson (Dunder Mifflin).
    
    SEUS OBJETIVOS:
    1. Responder dúvidas sobre a política da empresa (Use RAG).
    2. Verificar gastos e dados financeiros (Use SQL).
    3. Identificar violações de regras (Use verificar_quebras_compliance).
    4. Investigar fraudes complexas e conluios (Use auditoria_cruzada_emails_banco).

    IMPORTANTE:
    - Se o usuário pedir "Verifique fraudes", "Faça uma auditoria" ou "Procure erros", NÃO faça perguntas de volta. EXECUTE AS FERRAMENTAS DE AUDITORIA (3.1 e 3.2) IMEDIATAMENTE.
    - Seja rigoroso. Michael Scott é frequentemente culpado.
    - Sempre cite a fonte (ex: "Segundo a tabela de transações..." ou "De acordo com o e-mail de data X...").
    """)
    
    messages = [system_msg, HumanMessage(content=user_input)]
    
    # 1. Primeira chamada ao LLM (ele decide qual ferramenta usar)
    ai_msg = llm_with_tools.invoke(messages)
    
    # 2. Loop de execução de ferramentas (se houver chamadas)
    if ai_msg.tool_calls:
        messages.append(ai_msg) # Adiciona a intenção do AI ao histórico
        
        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            print(f"DEBUG: Agente chamando ferramenta -> {tool_name}")
            
            tool_response = "Erro na execução da ferramenta."
            
            # Roteamento manual (simples e robusto)
            if tool_name == "ferramenta_rag":
                tool_response = ferramenta_rag.invoke(tool_args)
            elif tool_name == "ferramenta_sql":
                tool_response = ferramenta_sql.invoke(tool_args)
            elif tool_name == "verificar_quebras_compliance":
                tool_response = verificar_quebras_compliance.invoke(tool_args)
            elif tool_name == "auditoria_cruzada_emails_banco":
                tool_response = auditoria_cruzada_emails_banco.invoke(tool_args)
                
            # Adiciona a resposta da ferramenta ao histórico
            messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_response)))
            
        # 3. Chamada final para o LLM gerar a resposta em linguagem natural
        print("DEBUG: Gerando resposta final...")
        try:
            final_response = llm.invoke(messages)
            return final_response.content
        except Exception as e:
            return "Ocorreu um erro ao gerar a resposta final (possível limite de tokens), mas a auditoria encontrou os dados acima."
    
    return ai_msg.content

if __name__ == "__main__":
    # Teste rápido local
    print(process_chat("Faça uma auditoria completa em busca de fraudes e violações."))