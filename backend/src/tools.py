import os
import re
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from sqlalchemy import create_engine, text


load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY não encontrada")


embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

vector_db = FAISS.load_local(
    "../backend/data/faiss_index",
    embedding_model,
    allow_dangerous_deserialization=True
)

db_engine = create_engine("sqlite:///data/dunder_mifflin.db")


@tool
def ferramenta_rag(pergunta: str) -> str:
    docs = vector_db.similarity_search(pergunta, k=8)
    return "\n\n".join(d.page_content for d in docs)


@tool
def ferramenta_emails(pergunta: str) -> str:
    docs = vector_db.similarity_search(f"EMAILS {pergunta}", k=10)
    return "\n\n".join(d.page_content for d in docs)


@tool
def ferramenta_sql(pergunta_usuario: str) -> dict:
    system_sql = SystemMessage(content="""
    Você é um gerador de SQL SQLite.
    O banco é um snapshot histórico.
    O ano atual é 2008.
    É proibido usar funções de data dinâmica.
    Sempre filtre com data LIKE '2008%'.
    Use LIMIT 20.
    """)

    human_sql = HumanMessage(content=f"""
    Regras de compliance:
    - valor > 500
    - categorias suspeitas: Despesas Pessoais, Entretenimento, Mágica, Helicópteros
    - palavras-chave suspeitas: WUPHF, Velas, Serenity, Mágica

    Pergunta:
    "{pergunta_usuario}"

    Gere apenas a query SQL.
    """)

    llm_sql = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    resposta = llm_sql.invoke([system_sql, human_sql])

    query = resposta.content.strip().replace("```sql", "").replace("```", "")

    if re.search(r"now|current_date|current_timestamp", query, re.I):
        raise ValueError("Uso de data dinâmica detectado")

    if "limit" not in query.lower():
        query += "\nLIMIT 20"

    with db_engine.connect() as conn:
        rows = conn.execute(text(query)).fetchall()

    return {
        "total": len(rows),
        "exemplos": [
            {
                "id": r[0],
                "data": r[1],
                "funcionario": r[2],
                "descricao": r[4],
                "valor": r[5],
                "categoria": r[6],
                "departamento": r[7],
            }
            for r in rows[:10]
        ]
    }


@tool
def ferramenta_fraude_contextual() -> str:
    query = """
    SELECT id_transacao, data, funcionario, descricao, valor
    FROM transacoes
    WHERE data LIKE '2008%'
      AND valor > 500
    LIMIT 10
    """

    with db_engine.connect() as conn:
        transacoes = conn.execute(text(query)).fetchall()

    contexto = []
    for t in transacoes:
        emails = vector_db.similarity_search(
            f"emails {t[2]} desvio verba combinação",
            k=3
        )
        contexto.append({
            "transacao": t,
            "emails": [e.page_content for e in emails]
        })

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    prompt = f"""
    Analise as transações e os emails associados e conclua se há fraude contextual.

    Dados:
    {contexto}
    """

    return llm.invoke(prompt).content


def process_chat(user_input: str) -> str:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    tools = [
        ferramenta_rag,
        ferramenta_emails,
        ferramenta_sql,
        ferramenta_fraude_contextual
    ]

    llm_with_tools = llm.bind_tools(tools)

    system_msg = SystemMessage(content="""
    Você é o Auditor da Dunder Mifflin.
    Use RAG para política e emails.
    Use SQL para quebras objetivas.
    Use fraude contextual quando houver conluio.
    Responda em português do Brasil.
    """)

    messages = [
        system_msg,
        HumanMessage(content=user_input)
    ]

    ai_msg = llm_with_tools.invoke(messages)

    if ai_msg.tool_calls:
        for call in ai_msg.tool_calls:
            if call["name"] == "ferramenta_sql":
                r = ferramenta_sql.invoke(call["args"])
                return f"Foram encontradas {r['total']} transações suspeitas.\n{r['exemplos']}"
            if call["name"] == "ferramenta_rag":
                return ferramenta_rag.invoke(call["args"])
            if call["name"] == "ferramenta_emails":
                return ferramenta_emails.invoke(call["args"])
            if call["name"] == "ferramenta_fraude_contextual":
                return ferramenta_fraude_contextual.invoke({})

    return ai_msg.content
