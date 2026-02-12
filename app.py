### INÍCIO DO CÓDIGO DE DIAGNÓSTICO - app.py ###

import streamlit as st
import os
import datetime
import re
import glob
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from fpdf import FPDF
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Defesa Ambiental", layout="wide")

# --- ESTILOS (SEU CÓDIGO) ---
# ... (Seu código de estilos é mantido aqui, omitido por brevidade) ...

# --- FUNÇÕES (ADAPTADAS COM DIAGNÓSTICO) ---
def extrair_dados_cadastrais_do_texto(texto_llm):
    dados = {"empresa": "", "cnpj": "", "endereco": "", "cidade": ""}
    padroes = {
        "empresa": r"EMPRESA:\s*(.+)", "cnpj": r"CNPJ:\s*(.+)",
        "endereco": r"ENDERECO:\s*(.+)", "cidade": r"CIDADE:\s*(.+)"
    }
    for chave, padrao in padroes.items():
        match = re.search(padrao, texto_llm, re.IGNORECASE)
        if match: dados[chave] = match.group(1).strip()
    return dados

def processar_pdf_completo(arquivo_pdf, api_key):
    try:
        st.info("DIAGNÓSTICO: Dentro de 'processar_pdf_completo'. Lendo o PDF...")
        reader = PdfReader(arquivo_pdf)
        texto_completo = ""
        for i, page in enumerate(reader.pages):
            try:
                extracted_text = page.extract_text()
                if extracted_text: texto_completo += extracted_text + "\n"
            except Exception: continue
        if not texto_completo.strip():
            return ("ERRO: Nenhum texto foi extraído do PDF.", "ERRO: Nenhum texto foi extraído do PDF.")
        
        st.info("DIAGNÓSTICO: PDF lido com sucesso. Conectando à IA (Groq)...")
        llm = ChatGroq(model="gemma-7b-it", temperature=0.0, api_key=api_key)

        st.info("DIAGNÓSTICO: Extraindo dados cadastrais...")
        template_dados = "Analise o texto da licença... TEXTO: {texto} RETORNE APENAS NESTE FORMATO:\nEMPRESA: (Razão Social)\nCNPJ: (CNPJ)\nENDERECO: (Logradouro)\nCIDADE: (Cidade - UF)"
        chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
        dados_cadastrais = chain_dados.invoke({"texto": texto_completo[:3000]}).content
        st.info(f"DIAGNÓSTICO: Resposta da IA (Dados): {dados_cadastrais[:100]}...")

        st.info("DIAGNÓSTICO: Extraindo exigências...")
        template_exigencias = "Analise o texto da Licença Ambiental... SUA MISSÃO: Listar todas as EXIGÊNCIAS TÉCNICAS... REGRAS ABSOLUTAS: ...SEPARAR CADA EXIGÊNCIA EXCLUSIVAMENTE com o delimitador '###'... TEXTO:\n{texto}\nRESPOSTA (APENAS AS EXIGÊNCIAS...):"
        chain_exig = ChatPromptTemplate.from_template(template_exigencias) | llm
        lista_exigencias = chain_exig.invoke({"texto": texto_completo}).content
        st.info(f"DIAGNÓSTICO: Resposta da IA (Exigências): {lista_exigencias[:100]}...")
        
        return dados_cadastrais, lista_exigencias
    except Exception as e:
        st.error(f"DIAGNÓSTICO: ERRO CRÍTICO dentro de 'processar_pdf_completo': {e}")
        return (f"ERRO: {e}", f"ERRO: {e}")

def processar_apenas_cadastro(arquivo_pdf, api_key):
    # ... (lógica similar) ...
    return "Função de cadastro manual."

def gerar_pdf_final(itens, empresa, cidade, nome, cargo):
    # ... (Sua função de gerar PDF mantida) ...
    return b"PDF content"

def consultar_ia(exigencia, vectorstore, api_key, temperatura=0.0, modo="media"):
    # ... (Sua função de consultar IA mantida) ...
    return "Resposta da IA"

# --- LÓGICA DE CRIAÇÃO DO CÉREBRO (ADAPTADA COM DIAGNÓSTICO) ---
def construir_cerebro_nuvem():
    st.info("DIAGNÓSTICO: Iniciando 'construir_cerebro_nuvem'...")
    PASTA_DOCUMENTOS = "pdfs_cetesb"
    NOME_BANCO = "banco_chroma"
    MODELO_EMBEDDINGS = "all-MiniLM-L6-v2"
    if not os.path.exists(PASTA_DOCUMENTOS):
        st.error(f"DIAGNÓSTICO: A pasta '{PASTA_DOCUMENTOS}' não foi encontrada! O cérebro não pode ser construído.")
        return None
    
    arquivos_pdf = glob.glob(os.path.join(PASTA_DOCUMENTOS, "*.pdf"))
    if not arquivos_pdf:
        st.warning(f"DIAGNÓSTICO: Nenhum arquivo PDF encontrado na pasta '{PASTA_DOCUMENTOS}'.")
        return None

    st.info(f"DIAGNÓSTICO: {len(arquivos_pdf)} PDFs encontrados. Lendo documentos...")
    documentos = []
    for arquivo_path in arquivos_pdf:
        try:
            loader = PyPDFLoader(arquivo_path)
            documentos.extend(loader.load())
        except Exception: continue
    
    if not documentos:
        st.error("DIAGNÓSTICO: Falha ao carregar o conteúdo dos PDFs.")
        return None

    st.info("DIAGNÓSTICO: Dividindo os textos em pedaços (chunks)...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documentos)

    st.info("DIAGNÓSTICO: Gerando os embeddings (vetores)... Isso pode demorar.")
    embedding_function = HuggingFaceEmbeddings(model_name=MODELO_EMBEDDINGS)
    
    st.info("DIAGNÓSTICO: Salvando o cérebro no banco de dados Chroma...")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_function, persist_directory=NOME_BANCO)
    st.success("DIAGNÓSTICO: Cérebro construído e salvo com sucesso!")
    return vectorstore

@st.cache_resource
def carregar_ou_construir_cerebro():
    NOME_BANCO = "banco_chroma"
    st.info(f"DIAGNÓSTICO: Verificando se o cérebro ('{NOME_BANCO}') já existe...")
    if os.path.exists(NOME_BANCO):
        st.info("DIAGNÓSTICO: Cérebro encontrado! Carregando...")
        embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return Chroma(persist_directory=NOME_BANCO, embedding_function=embedding_function)
    else:
        st.warning("DIAGNÓSTICO: Cérebro não encontrado. Disparando a construção...")
        with st.spinner("Construindo a base de conhecimento pela primeira vez..."):
            return construir_cerebro_nuvem()

# --- ESTADO DA SESSÃO ---
if "relatorio" not in st.session_state: st.session_state.relatorio = []
if "fila_exigencias" not in st.session_state: st.session_state.fila_exigencias = []
if "dados_auto" not in st.session_state: st.session_state.dados_auto = {"empresa": "", "cnpj": "", "end": "", "cid": ""}

# --- CARREGAR CÉREBRO ---
vectorstore = carregar_ou_construir_cerebro()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🔑 Acesso")
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("Chave API da nuvem carregada!")
    except:
        st.error("Chave 'GROQ_API_KEY' não encontrada nos segredos do Streamlit Cloud.")
        st.stop()
    
    st.markdown("---")
    uploaded_file = st.file_uploader("Subir Licença (PDF)", type="pdf")
    
    if uploaded_file:
        st.info("DIAGNÓSTICO: PDF foi carregado pelo usuário.")
        st.markdown("### Selecione a Tática:")
        if st.button("🕵️ IMPORTAR TUDO (AUTO)", type="primary"):
            st.info("DIAGNÓSTICO: Botão 'IMPORTAR TUDO' foi clicado.")
            with st.spinner("Analisando o documento..."):
                txt_dados, txt_exigencias = processar_pdf_completo(uploaded_file, api_key)
                
                # --- DIAGNÓSTICO APÓS A CHAMADA ---
                if "ERRO:" in txt_dados:
                    st.error(f"DIAGNÓSTICO FINAL: A função retornou um erro: {txt_dados}")
                    st.stop()

                st.info("DIAGNÓSTICO: Processamento concluído. Atualizando o estado da sessão...")
                dados_extraidos = extrair_dados_cadastrais_do_texto(txt_dados)
                st.session_state.dados_auto.update(dados_extraidos)
                raw_list = txt_exigencias.split('###')
                st.session_state.fila_exigencias = [item.strip() for item in raw_list if len(item.strip()) > 10]
                
                if not st.session_state.fila_exigencias:
                    st.warning("DIAGNÓSTICO FINAL: Nenhuma exigência foi adicionada à fila.")
                else:
                    st.success(f"DIAGNÓSTICO FINAL: {len(st.session_state.fila_exigencias)} exigências carregadas!")
                
                st.rerun()
    # ... (resto da sua sidebar) ...

# --- INTERFACE PRINCIPAL ---
st.title("Sistema de Defesa Ambiental (Modo Diagnóstico)")

if not vectorstore:
    st.error("ERRO CRÍTICO: O CÉREBRO (VECTORSTORE) NÃO FOI CARREGADO. Verifique as mensagens de diagnóstico acima.")
    st.stop()
else:
    st.success("DIAGNÓSTICO: Cérebro (Vectorstore) carregado e pronto para uso.")

# ... (resto da sua interface principal) ...

### FIM DO CÓDIGO DE DIAGNÓSTICO ###
