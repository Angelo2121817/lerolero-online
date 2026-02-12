### INÍCIO DO CÓDIGO FINAL ADAPTADO PARA A NUVEM ###

import streamlit as st
import os
import datetime
import re
import glob
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from langchain_community.vectorstores import Chroma # <-- MUDANÇA 1: Usando Chroma, mais simples para nuvem
from langchain_huggingface import HuggingFaceEmbeddings # <-- MUDANÇA 2: Embeddings de nuvem
from langchain_groq import ChatGroq # <-- MUDANÇA 3: LLM de nuvem (Groq)
from langchain_core.prompts import ChatPromptTemplate
from fpdf import FPDF
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Defesa Ambiental", layout="wide")

# --- CENTRO DE CONTROLE ESTÉTICO (SEU CÓDIGO - MANTIDO 100%) ---
with st.sidebar:
    st.subheader("🎨 Estilo do Terminal")
    tema = st.selectbox("Selecione o Visual:", [
        "Moderno Executivo", "Hacker Verde", "Cyberpunk Neon", "Papel Digital", 
        "Modo Noturno", "Deep Sea", "Escritório", "Minimalista", "Metal Química", "Sunset"
    ])
estilos = {
    "Moderno Executivo": {"bg": "#0f172a", "txt": "#f1f5f9", "side": "#1e293b", "btn": "#3b82f6"},
    "Hacker Verde": {"bg": "#000000", "txt": "#00ff41", "side": "#0a0a0a", "btn": "#00ff41", "font": "monospace"},
    "Cyberpunk Neon": {"bg": "#0d0221", "txt": "#00f5d4", "side": "#240b36", "btn": "#9b5de5"},
    "Papel Digital": {"bg": "#f8fafc", "txt": "#1e293b", "side": "#f1f5f9", "btn": "#2563eb"},
    "Modo Noturno": {"bg": "#121212", "txt": "#e0e0e0", "side": "#1e1e1e", "btn": "#bb86fc"},
    "Deep Sea": {"bg": "#011627", "txt": "#d6deeb", "side": "#0b253a", "btn": "#2ec4b6"},
    "Escritório": {"bg": "#ffffff", "txt": "#333333", "side": "#eeeeee", "btn": "#0078d4"},
    "Minimalista": {"bg": "#fafafa", "txt": "#000000", "side": "#ffffff", "btn": "#000000"},
    "Metal Química": {"bg": "#2c3e50", "txt": "#ecf0f1", "side": "#34495e", "btn": "#e67e22"},
    "Sunset": {"bg": "#2d142c", "txt": "#ffa372", "side": "#510a32", "btn": "#ee4540"}
}
s = estilos[tema]
st.markdown(f"""
    <style>
    .stApp {{ background-color: {s['bg']}; color: {s['txt']}; font-family: {s.get('font', 'sans-serif')}; }}
    h1, h2, h3 {{ color: {s['txt']} !important; }}
    [data-testid="stSidebar"] {{ background-color: {s['side']}; border-right: 1px solid {s['btn']}; }}
    .stButton>button {{ background-color: {s['btn']}; color: {s['bg'] if tema != "Hacker Verde" else "#000"}; border-radius: 8px; border: none; font-weight: bold; }}
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{ background-color: {s['side']}; color: {s['txt']} !important; border: 1px solid {s['btn']}; }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO AUXILIAR: EXTRAÇÃO DE DADOS (SEU CÓDIGO - MANTIDO 100%) ---
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

# --- FUNÇÃO 1: EXTRAÇÃO INTELIGENTE (ADAPTADA) ---
def processar_pdf_completo(arquivo_pdf, api_key):
    try:
        reader = PdfReader(arquivo_pdf)
        texto_completo = ""
        for i, page in enumerate(reader.pages):
            try:
                extracted_text = page.extract_text()
                if extracted_text: texto_completo += extracted_text + "\n"
            except Exception: continue
        if not texto_completo.strip():
            return ("ERRO: Texto não extraído.", "ERRO: Texto não extraído.")

        # --- ADAPTAÇÃO: Usando Groq ---
        llm = ChatGroq(model="gemma-7b-it", temperature=0.0, api_key=api_key)

        template_dados = "Analise o texto da licença... TEXTO: {texto} RETORNE APENAS NESTE FORMATO:\nEMPRESA: (Razão Social)\nCNPJ: (CNPJ)\nENDERECO: (Logradouro)\nCIDADE: (Cidade - UF)"
        chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
        dados_cadastrais = chain_dados.invoke({"texto": texto_completo[:3000]}).content

        template_exigencias = "Analise o texto da Licença Ambiental... SUA MISSÃO: Listar todas as EXIGÊNCIAS TÉCNICAS... REGRAS ABSOLUTAS: ...SEPARAR CADA EXIGÊNCIA EXCLUSIVAMENTE com o delimitador '###'... TEXTO:\n{texto}\nRESPOSTA (APENAS AS EXIGÊNCIAS...):"
        chain_exig = ChatPromptTemplate.from_template(template_exigencias) | llm
        lista_exigencias = chain_exig.invoke({"texto": texto_completo}).content
        
        return dados_cadastrais, lista_exigencias
    except Exception as e:
        return (f"ERRO: {e}", f"ERRO: {e}")

# --- FUNÇÃO 1.B: EXTRAÇÃO SÓ CADASTRO (ADAPTADA) ---
def processar_apenas_cadastro(arquivo_pdf, api_key):
    try:
        reader = PdfReader(arquivo_pdf)
        texto_completo = ""
        for i, page in enumerate(reader.pages):
            if i > 2: break
            try:
                extracted_text = page.extract_text()
                if extracted_text: texto_completo += extracted_text + "\n"
            except Exception: continue
        if not texto_completo.strip(): return "ERRO: Texto não extraído."

        # --- ADAPTAÇÃO: Usando Groq ---
        llm = ChatGroq(model="gemma-7b-it", temperature=0.0, api_key=api_key)
        
        template_dados = "Analise o texto da licença... TEXTO: {texto} RETORNE APENAS NESTE FORMATO:\nEMPRESA: (Razão Social)\nCNPJ: (CNPJ)\nENDERECO: (Logradouro)\nCIDADE: (Cidade - UF)"
        chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
        return chain_dados.invoke({"texto": texto_completo}).content
    except Exception as e:
        return f"ERRO: {e}"

# --- FUNÇÃO 2: GERAR PDF FINAL (SEU CÓDIGO - MANTIDO 100%) ---
def gerar_pdf_final(itens, empresa, cidade, nome, cargo):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    empresa_limpa = str(empresa).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"{empresa_limpa}", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "RELATORIO DE EXIGENCIAS TECNICAS", ln=True, align="C")
    pdf.ln(15)
    for item in itens:
        titulo_limpo = str(item['titulo'])
        titulo_limpo = re.sub(r'item\s*\d*\.?\s*', '', titulo_limpo, flags=re.IGNORECASE).strip()
        titulo_limpo = titulo_limpo.encode('latin-1', 'replace').decode('latin-1')
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, titulo_limpo, ln=True, fill=True)
        pdf.ln(2)
        if item['exigencia']:
            pdf.set_font("Arial", "I", 10)
            pdf.set_text_color(80, 80, 80)
            exigencia_limpa = f"Exigencia: {str(item['exigencia'])}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, exigencia_limpa)
            pdf.ln(2)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 11)
        resposta_limpa = str(item['resposta']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, resposta_limpa)
        pdf.ln(10)
    if pdf.get_y() > 220: pdf.add_page()
    pdf.ln(10)
    meses = {"01": "janeiro", "02": "fevereiro", "03": "marco", "04": "abril", "05": "maio", "06": "junho", "07": "julho", "08": "agosto", "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro"}
    hoje = datetime.date.today()
    data_longa = f"{hoje.day} de {meses[hoje.strftime('%m')]} de {hoje.year}"
    cidade_limpa = str(cidade).encode('latin-1', 'replace').decode('latin-1')
    pdf.set_font("Arial", "I", 11)
    pdf.cell(0, 8, f"{cidade_limpa}, {data_longa}", ln=True, align="C")
    pdf.ln(10)
    pdf.line(pdf.get_x() + 50, pdf.get_y(), pdf.get_x() + 150, pdf.get_y())
    pdf.set_font("Arial", "B", 12)
    nome_limpo = str(nome).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, nome_limpo, ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    cargo_limpo = str(cargo).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 5, cargo_limpo, ln=True, align="C")
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- FUNÇÃO AUXILIAR: CONSULTAR IA (ADAPTADA) ---
def consultar_ia(exigencia, vectorstore, api_key, temperatura=0.0, modo="media"):
    docs = vectorstore.similarity_search(exigencia, k=3)
    contexto = "\n".join([d.page_content for d in docs])
    
    # --- ADAPTAÇÃO: Usando Groq ---
    llm = ChatGroq(model="gemma-7b-it", temperature=temperatura, api_key=api_key)
    
    instrucoes_modo = {
        "curta": "ESTILO: CURTO E GROSSO... FOCO: Diga apenas que a exigência foi cumprida...",
        "media": "ESTILO: EQUILIBRADO E TÉCNICO... FOCO: Confirme o atendimento da exigência e faça uma breve explicação...",
        "avancada": "ESTILO: TÉCNICO DETALHADO... FOCO: Explique o funcionamento técnico completo..."
    }.get(modo, "")

    template = f"Você é um Engenheiro Ambiental Sênior... {instrucoes_modo} REGRAS GERAIS: ... CONTEXTO (Gabarito):\n{{context}}\nEXIGÊNCIA (Pergunta):\n{{question}}\nRESPOSTA:"
    chain = ChatPromptTemplate.from_template(template) | llm
    return chain.invoke({"context": contexto, "question": exigencia}).content

# --- LÓGICA DE CRIAÇÃO DO CÉREBRO (ADAPTADA PARA NUVEM) ---
def construir_cerebro_nuvem():
    PASTA_DOCUMENTOS = "pdfs_cetesb"
    NOME_BANCO = "banco_chroma"
    MODELO_EMBEDDINGS = "all-MiniLM-L6-v2" # Modelo gratuito e eficiente
    documentos = []
    if not os.path.exists(PASTA_DOCUMENTOS): return None
    for arquivo_path in glob.glob(os.path.join(PASTA_DOCUMENTOS, "*.pdf")):
        try:
            loader = PyPDFLoader(arquivo_path)
            documentos.extend(loader.load())
        except Exception: continue
    if not documentos: return None
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documentos)
    embedding_function = HuggingFaceEmbeddings(model_name=MODELO_EMBEDDINGS)
    vectorstore = Chroma.from_documents(documents=splits, embedding=embedding_function, persist_directory=NOME_BANCO)
    return vectorstore

@st.cache_resource
def carregar_ou_construir_cerebro():
    NOME_BANCO = "banco_chroma"
    if os.path.exists(NOME_BANCO):
        embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return Chroma(persist_directory=NOME_BANCO, embedding_function=embedding_function)
    else:
        with st.spinner("Construindo a base de conhecimento pela primeira vez..."):
            return construir_cerebro_nuvem()

# --- ESTADO DA SESSÃO (SEU CÓDIGO - MANTIDO 100%) ---
if "relatorio" not in st.session_state: st.session_state.relatorio = []
if "fila_exigencias" not in st.session_state: st.session_state.fila_exigencias = []
if "dados_auto" not in st.session_state: st.session_state.dados_auto = {"empresa": "", "cnpj": "", "end": "", "cid": ""}

# --- CARREGAR CÉREBRO ---
vectorstore = carregar_ou_construir_cerebro()

# --- BARRA LATERAL (ADAPTADA) ---
with st.sidebar:
    # --- ADAPTAÇÃO: Lógica da Chave API ---
    st.header("🔑 Acesso")
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("Chave API da nuvem carregada!")
    except:
        st.error("Chave 'GROQ_API_KEY' não encontrada nos segredos do Streamlit Cloud.")
        st.stop()
    
    if st.button("🗑️ ZERAR SISTEMA", type="secondary"):
        # (Sua lógica de zerar mantida)
        st.rerun()

    st.markdown("---")
    uploaded_file = st.file_uploader("Subir Licença (PDF)", type="pdf")
    
    if uploaded_file:
        st.markdown("### Selecione a Tática:")
        if st.button("🕵️ IMPORTAR TUDO (AUTO)", type="primary"):
            with st.spinner("Extraindo Dados e Perguntas..."):
                # --- ADAPTAÇÃO: Passando a api_key ---
                txt_dados, txt_exigencias = processar_pdf_completo(uploaded_file, api_key)
                dados_extraidos = extrair_dados_cadastrais_do_texto(txt_dados)
                st.session_state.dados_auto.update(dados_extraidos)
                raw_list = txt_exigencias.split('###')
                st.session_state.fila_exigencias = [item.strip() for item in raw_list if len(item.strip()) > 10]
                st.success("Tudo carregado!")
                st.rerun()

        if st.button("📝 SÓ CADASTRO (MANUAL)"):
            with st.spinner("Lendo apenas o cabeçalho..."):
                # --- ADAPTAÇÃO: Passando a api_key ---
                txt_dados = processar_apenas_cadastro(uploaded_file, api_key)
                dados_extraidos = extrair_dados_cadastrais_do_texto(txt_dados)
                st.session_state.dados_auto.update(dados_extraidos)
                st.session_state.fila_exigencias = [] 
                st.success("Cadastro pronto!")
                st.rerun()

    st.markdown("---")
    INPUT_EMPRESA = st.text_input("Nome da Empresa", st.session_state.dados_auto["empresa"] or "METAL QUÍMICA")
    INPUT_CIDADE = st.text_input("Cidade", st.session_state.dados_auto["cid"] or "São José do Rio Preto - SP")
    INPUT_NOME = st.text_input("Seu Nome", "GENERAL")
    INPUT_CARGO = st.text_input("Seu Cargo", "Diretor Técnico")
    st.markdown("---")

# --- INTERFACE PRINCIPAL (SEU CÓDIGO - MANTIDO COM ADAPTAÇÕES) ---
st.title(f"🏭 {INPUT_EMPRESA} - Central de Defesa")

if not vectorstore:
    st.error("ERRO CRÍTICO: Cérebro não encontrado e falhou em ser construído. Verifique se a pasta 'pdfs_cetesb' e os arquivos PDF estão no repositório.")
    st.stop()

col_esq, col_dir = st.columns([1, 1])

with col_esq:
    # (Sua lógica mantida)
    st.subheader("1. Área de Trabalho")
    # ...

with col_dir:
    st.subheader("2. Editor Tático")
    if "editor_exigencia" in st.session_state:
        # ...
        if "editor_resposta" not in st.session_state:
            if st.button("GERAR RESPOSTA BLINDADA 🛡️", type="primary"):
                with st.spinner(f"Gerando resposta {st.session_state.get('modo_resposta', 'media')}..."):
                    # --- ADAPTAÇÃO: Passando a api_key ---
                    res = consultar_ia(st.session_state.editor_exigencia, vectorstore, api_key, temperatura=0.0, modo=st.session_state.get('modo_resposta', 'media'))
                    st.session_state.editor_resposta = res
                    st.rerun()
        # ...

st.markdown("---")
st.subheader("3. Relatório Final")
# (Sua lógica mantida)
# ...

### FIM DO CÓDIGO FINAL ADAPTADO PARA A NUVEM ###
