import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# HuggingFace modelo de embading (Local)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter

load_dotenv()

def ingest_sql():
    # Variáveis para o SLQlite
    print("--- Iniciando Ingestão SQL ---")
    csv_path = "../backend/data/transacoes_bancarias.csv"
    db_path = "sqlite:///data/dunder_mifflin.db"
    
    #carregando o csv
    df = pd.read_csv(csv_path)

    #conecta o modelo no banco de dados
    engine = create_engine(db_path)

    # DataFrame Salvo como uma tabela chamada 'transacoes'
    # index=False-  não salvar o número da linha como coluna
    # if_exists='replace' - se rodarmos de novo, ele apaga e recria
    df.to_sql("transacoes", engine, index=False, if_exists="replace")
    print("Sucesso: Banco SQL criado.")

def ingest_vectors():
    print("--- Iniciando Ingestão Vetorial (Local) ---")

    paths= [
        "../backend/data/politica_compliance.txt", 
        "../backend/data/emails.txt"
    ]

    raw_text = ""
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_text += f.read() + "\n\n"
        except FileNotFoundError:
            print(f"Aviso: Arquivo {path} não encontrado.")

    #Separador de texto com a quebra de linha\n, o tamanho de cada bloco é 1000 carateres e ele sempre começa com os 200 primeiros caracteres do último chunck pra não perder contexto
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200
    )
    texts = text_splitter.split_text(raw_text)
    print(f"Texto dividido em {len(texts)} pedaços.")
    
    # modelo (all-MiniLM-L6-v2) para realizar o embedding.
    print("Carregando modelo de embedding local (pode demorar uns segundos na 1ª vez)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Cria o índice FAISS usando o modelo local
    vectorstore = FAISS.from_texts(texts, embeddings)
    
    vectorstore.save_local("../backend/data/faiss_index")
    print("Sucesso: Índice Vetorial salvo localmente!")

if __name__ == "__main__":
    ingest_sql()
    ingest_vectors()