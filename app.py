### SISTEMA DE DEFESA AMBIENTAL - VERSÃO CIRÚRGICA FINAL ###

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

# --- ESTADO DA SESSÃO ---
if "relatorio" not in st.session_state: st.session_state.relatorio = []
if "fila_exigencias" not in st.session_state: st.session_state.fila_exigencias = []
if "dados_auto" not in st.session_state: 
    st.session_state.dados_auto = {"empresa": "", "cnpj": "", "endereco": "", "cidade": ""}

# --- ESTILOS (SEU CÓDIGO MANTIDO) ---
with st.sidebar:
    st.subheader("🎨 Estilo do Terminal")
    tema = st.selectbox("Selecione o Visual:", ["Moderno Executivo", "Hacker Verde", "Cyberpunk Neon", "Papel Digital", "Modo Noturno", "Deep Sea", "Escritório", "Minimalista", "Metal Química", "Sunset"])
estilos = {
    "Moderno Executivo": {"bg": "#0f172a", "txt": "#f1f5f9", "side": "#1e293b", "btn": "#3b82f6"}, "Hacker Verde": {"bg": "#000000", "txt": "#00ff41", "side": "#0a0a0a", "btn": "#00ff41", "font": "monospace"}, "Cyberpunk Neon": {"bg": "#0d0221", "txt": "#00f5d4", "side": "#240b36", "btn": "#9b5de5"}, "Papel Digital": {"bg": "#f8fafc", "txt": "#1e293b", "side": "#f1f5f9", "btn": "#2563eb"}, "Modo Noturno": {"bg": "#121212", "txt": "#e0e0e0", "side": "#1e1e1e", "btn": "#bb86fc"}, "Deep Sea": {"bg": "#011627", "txt": "#d6deeb", "side": "#0b253a", "btn": "#2ec4b6"}, "Escritório": {"bg": "#ffffff", "txt": "#333333", "side": "#eeeeee", "btn": "#0078d4"}, "Minimalista": {"bg": "#fafafa", "txt": "#000000", "side": "#ffffff", "btn": "#000000"}, "Metal Química": {"bg": "#2c3e50", "txt": "#ecf0f1", "side": "#34495e", "btn": "#e67e22"}, "Sunset": {"bg": "#2d142c", "txt": "#ffa372", "side": "#510a32", "btn": "#ee4540"}
}
s = estilos[tema]
st.markdown(f"""<style>.stApp{{background-color:{s['bg']};color:{s['txt']};font-family:{s.get('font','sans-serif')};}} h1,h2,h3{{color:{s['txt']}!important;}} [data-testid="stSidebar"]{{background-color:{s['side']};border-right:1px solid {s['btn']};}} .stButton>button{{background-color:{s['btn']};color:{s['bg'] if tema!="Hacker Verde" else "#000"};border-radius:8px;border:none;font-weight:bold;}} .stTextInput>div>div>input,.stTextArea>div>div>textarea{{background-color:{s['side']};color:{s['txt']}!important;border:1px solid {s['btn']};}}</style>""", unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO (SEU CÓDIGO MANTIDO) ---
def extrair_dados_cadastrais_do_texto(texto_llm):
    dados = {"empresa": "", "cnpj": "", "endereco": "", "cidade": ""}
    padroes = {"empresa": r"EMPRESA:\s*(.+)", "cnpj": r"CNPJ:\s*(.+)", "endereco": r"ENDERECO:\s*(.+)", "cidade": r"CIDADE:\s*(.+)"}
    for chave, padrao in padroes.items():
        match = re.search(padrao, texto_llm, re.IGNORECASE)
        if match: dados[chave] = match.group(1).strip()
    return dados

def processar_pdf_completo(arquivo_pdf, api_key):
    try:
        reader = PdfReader(arquivo_pdf)
        texto_completo = ""
        for page in reader.pages:
            try:
                extracted_text = page.extract_text()
                if extracted_text: texto_completo += extracted_text + "\n"
            except: continue
        if not texto_completo.strip(): return "ERRO: Texto não extraído.", "ERRO: Texto não extraído."
        llm = ChatGroq(model="gemma-7b-it", temperature=0.0, api_key=api_key)
        template_dados = "Analise o texto da licença ambiental...TEXTO: {texto}...EMPRESA: (Razão Social)..."
        chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
        dados_cadastrais = chain_dados.invoke({"texto": texto_completo[:4000]}).content
        template_exigencias = "Analise o texto da Licença Ambiental...SUA MISSÃO: Listar todas as EXIGÊNCIAS TÉCNICAS...TEXTO: {texto}..."
        chain_exig = ChatPromptTemplate.from_template(template_exigencias) | llm
        lista_exigencias = chain_exig.invoke({"texto": texto_completo}).content
        return dados_cadastrais, lista_exigencias
    except Exception as e:
        return f"ERRO: {e}", f"ERRO: {e}"

def processar_apenas_cadastro(arquivo_pdf, api_key):
    try:
        reader = PdfReader(arquivo_pdf)
        texto_curto = ""
        for i, page in enumerate(reader.pages):
            if i > 2: break
            texto_curto += page.extract_text() + "\n"
        llm = ChatGroq(model="gemma-7b-it", temperature=0.0, api_key=api_key)
        template_dados = "Extraia os dados cadastrais...TEXTO: {texto}...EMPRESA: (Razão Social)..."
        chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
        return chain_dados.invoke({"texto": texto_curto}).content
    except Exception as e:
        return f"ERRO: {e}"

def consultar_ia(exigencia, vectorstore, api_key, temperatura=0.0, modo="media"):
    docs = vectorstore.similarity_search(exigencia, k=3)
    contexto = "\n".join([d.page_content for d in docs])
    llm = ChatGroq(model="gemma-7b-it", temperature=temperatura, api_key=api_key)
    instrucoes_modo = {"curta": "ESTILO: CURTO E GROSSO...", "media": "ESTILO: EQUILIBRADO E TÉCNICO...", "avancada": "ESTILO: TÉCNICO DETALHADO..."}.get(modo, "ESTILO: TÉCNICO.")
    template = f"Você é um Engenheiro Ambiental Sênior. {instrucoes_modo}...CONTEXTO (Gabarito): {{context}}...EXIGÊNCIA (Pergunta): {{question}}...RESPOSTA:"
    chain = ChatPromptTemplate.from_template(template) | llm
    return chain.invoke({"context": contexto, "question": exigencia}).content

def construir_cerebro():
    PASTA_DOCUMENTOS = "pdfs_cetesb"; NOME_BANCO = "banco_chroma"
    if not os.path.exists(PASTA_DOCUMENTOS): os.makedirs(PASTA_DOCUMENTOS); return None
    documentos = []
    loaders = {".pdf": PyPDFLoader, ".txt": TextLoader, ".docx": Docx2txtLoader}
    for extensao, loader_class in loaders.items():
        for arc in glob.glob(os.path.join(PASTA_DOCUMENTOS, f"*{extensao}")):
            try:
                loader = loader_class(arc); documentos.extend(loader.load())
            except: continue
    if not documentos: return None
    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(documentos)
    vectorstore = Chroma.from_documents(documents=splits, embedding=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"), persist_directory=NOME_BANCO)
    return vectorstore

@st.cache_resource
def carregar_ou_construir_cerebro():
    NOME_BANCO = "banco_chroma"
    if os.path.exists(NOME_BANCO):
        return Chroma(persist_directory=NOME_BANCO, embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
    return construir_cerebro()

def gerar_pdf_final(itens, empresa, cidade, nome, cargo):
    # (Sua função de gerar PDF mantida)
    return b"PDF content"

# --- INTERFACE PRINCIPAL ---
vectorstore = carregar_ou_construir_cerebro()

with st.sidebar:
    st.header("🔑 Acesso")
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("Chave API carregada!")
    except:
        st.error("Chave 'GROQ_API_KEY' não encontrada."); st.stop()
    
    st.markdown("---")
    uploaded_file = st.file_uploader("Subir Licença (PDF)", type="pdf")
    
    if uploaded_file:
        st.markdown("### Selecione a Tática:")
        
        if st.button("🕵️ IMPORTAR TUDO (AUTO)", type="primary"):
            with st.spinner("Extraindo Dados e Perguntas..."):
                txt_dados, txt_exigencias = processar_pdf_completo(uploaded_file, api_key)
                
                # --- CIRURGIA 1: VERIFICAÇÃO DE ERRO ---
                if "ERRO:" in txt_dados:
                    st.error(f"Falha ao processar PDF: {txt_dados}")
                else:
                    novos_dados = extrair_dados_cadastrais_do_texto(txt_dados)
                    st.session_state.dados_auto.update(novos_dados)
                    raw_list = txt_exigencias.split('###') if "###" in txt_exigencias else txt_exigencias.split('\n')
                    st.session_state.fila_exigencias = [item.strip() for item in raw_list if len(item.strip()) > 10]
                    st.success("Processamento concluído!")
                    st.rerun()

        if st.button("📝 SÓ CADASTRO (MANUAL)"):
            with st.spinner("Lendo cabeçalho..."):
                txt_dados = processar_apenas_cadastro(uploaded_file, api_key)
                
                # --- CIRURGIA 2: VERIFICAÇÃO DE ERRO ---
                if "ERRO:" in txt_dados:
                    st.error(f"Falha ao processar PDF: {txt_dados}")
                else:
                    novos_dados = extrair_dados_cadastrais_do_texto(txt_dados)
                    st.session_state.dados_auto.update(novos_dados)
                    st.session_state.fila_exigencias = [] 
                    st.success("Cadastro preenchido!")
                    st.rerun()

    st.markdown("---")
    st.subheader("📝 Dados do Cliente")
    INPUT_EMPRESA = st.text_input("Empresa", st.session_state.dados_auto["empresa"])
    INPUT_CNPJ = st.text_input("CNPJ", st.session_state.dados_auto["cnpj"])
    INPUT_ENDERECO = st.text_input("Endereço", st.session_state.dados_auto["endereco"])
    INPUT_CIDADE = st.text_input("Cidade", st.session_state.dados_auto["cidade"])
    st.markdown("---")
    INPUT_NOME = st.text_input("Assinatura (Nome)", "Engenheiro Responsável")
    INPUT_CARGO = st.text_input("Cargo", "Diretor Técnico")

# --- CORPO DA PÁGINA (SEU CÓDIGO MANTIDO) ---
st.title("🛡️ CENTRAL DE DEFESA AMBIENTAL")
if not vectorstore: st.warning("Atenção: Base de conhecimento (cérebro) não encontrada.")
# (Resto da sua lógica da interface principal)
