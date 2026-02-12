### INÍCIO DO ARQUIVO COMPLETO: treinar.py (VERSÃO FINAL PARA DEPLOY) ###

import os
import glob
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- CONFIGURAÇÃO PARA DEPLOY: Usando caminhos relativos ---
PASTA_DOCUMENTOS = "pdfs_cetesb"
NOME_BANCO = "banco_chroma"
MODELO_EMBEDDINGS = "all-MiniLM-L6-v2"

def carregar_documentos_da_pasta(pasta):
    documentos = []
    loaders = {".pdf": PyPDFLoader, ".txt": TextLoader, ".docx": Docx2txtLoader}
    print(f"--- INICIANDO PROTOCOLO DE LEITURA ---")
    print(f"Buscando documentos na pasta: '{pasta}'")
    for extensao, loader_class in loaders.items():
        caminho_busca = os.path.join(pasta, f"**/*{extensao}")
        arquivos_encontrados = glob.glob(caminho_busca, recursive=True)
        if arquivos_encontrados:
            print(f"Encontrados {len(arquivos_encontrados)} arquivo(s) com extensão '{extensao}'.")
            for arquivo_path in arquivos_encontrados:
                try:
                    print(f"Processando: {arquivo_path}...")
                    loader = loader_class(arquivo_path)
                    documentos.extend(loader.load())
                except Exception as e:
                    print(f"🚨 Falha ao ler o arquivo {arquivo_path}: {e}")
    return documentos

def treinar_cerebro():
    documentos = carregar_documentos_da_pasta(PASTA_DOCUMENTOS)
    if not documentos:
        print("\n❌ ERRO CRÍTICO: Nenhum documento válido foi carregado.")
        return
    print(f"\n2. Dividindo {len(documentos)} páginas/documentos em pedaços...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documentos)
    print(f"✅ Documentos divididos em {len(splits)} pedaços.")
    print(f"\n3. Gerando embeddings com o modelo '{MODELO_EMBEDDINGS}'...")
    embedding_function = HuggingFaceEmbeddings(model_name=MODELO_EMBEDDINGS)
    print(f"\n4. Criando e salvando o cérebro na pasta '{NOME_BANCO}'...")
    vectorstore = Chroma.from_documents(
        documents=splits, 
        embedding=embedding_function,
        persist_directory=NOME_BANCO 
    )
    print("\n--- ✅ MISSÃO CUMPRIDA! ---")

if __name__ == "__main__":
    treinar_cerebro()

### FIM DO ARQUIVO COMPLETO: treinar.py (VERSÃO FINAL PARA DEPLOY) ###