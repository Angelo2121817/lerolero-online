### INÍCIO DO ARQUIVO COMPLETO: app.py (VERSÃO FINAL PARA DEPLOY) ###

import streamlit as st
import os
import datetime
from pypdf import PdfReader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from fpdf import FPDF
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Defesa Ambiental", layout="wide")

# --- FUNÇÕES DE PROCESSAMENTO DE PDF (Extração) ---
def processar_pdf_completo(arquivo_pdf, api_key):
    reader = PdfReader(arquivo_pdf)
    texto_completo = ""
    for page in reader.pages:
        texto_completo += page.extract_text() + "\n"
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.0, api_key=api_key)
    template_dados = """
    Analise o texto da licença. Extraia dados do LICENCIADO.
    TEXTO: {texto}
    RETORNE APENAS NESTE FORMATO:
    EMPRESA: (Razão Social)
    CNPJ: (CNPJ)
    ENDERECO: (Logradouro)
    CIDADE: (Cidade - UF)
    """
    chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
    dados_cadastrais = chain_dados.invoke({"texto": texto_completo[:4000]}).content
    template_exigencias = """
    Analise o texto da Licença Ambiental.
    SUA MISSÃO: Listar todas as EXIGÊNCIAS TÉCNICAS.
    REGRAS:
    1. Ignore leis, artigos e preâmbulos.
    2. Copie o texto da exigência.
    3. Separe cada exigência EXCLUSIVAMENTE com o delimitador "###".
    TEXTO:
    {texto}
    LISTA DE EXIGÊNCIAS (Separadas por ###):
    """
    chain_exig = ChatPromptTemplate.from_template(template_exigencias) | llm
    lista_exigencias = chain_exig.invoke({"texto": texto_completo}).content
    return dados_cadastrais, lista_exigencias

def processar_apenas_cadastro(arquivo_pdf, api_key):
    reader = PdfReader(arquivo_pdf)
    texto_completo = ""
    for i, page in enumerate(reader.pages):
        if i > 2: break 
        texto_completo += page.extract_text() + "\n"
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.0, api_key=api_key)
    template_dados = """
    Analise o texto da licença. Extraia dados do LICENCIADO.
    TEXTO: {texto}
    RETORNE APENAS NESTE FORMATO:
    EMPRESA: (Razão Social)
    CNPJ: (CNPJ)
    ENDERECO: (Logradouro)
    CIDADE: (Cidade - UF)
    """
    chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
    return chain_dados.invoke({"texto": texto_completo}).content

# --- FUNÇÃO DE GERAR PDF FINAL ---
def gerar_pdf_final(itens, empresa, cnpj, endereco, cidade, nome, cargo):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    empresa_limpa = str(empresa).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"{empresa_limpa}", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "RELATÓRIO DE ATENDIMENTO ÀS EXIGÊNCIAS TÉCNICAS", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    cnpj_limpo = str(cnpj).encode('latin-1', 'replace').decode('latin-1')
    end_limpo = str(endereco).encode('latin-1', 'replace').decode('latin-1')
    cidade_limpa = str(cidade).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 5, f"CNPJ: {cnpj_limpo}", ln=True, align="C")
    pdf.cell(0, 5, f"Endereço: {end_limpo}", ln=True, align="C")
    pdf.cell(0, 5, f"Local: {cidade_limpa} | Data: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.line(10, 45, 200, 45)
    pdf.ln(10)
    for item in itens:
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        tit = str(item['titulo']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 8, tit, ln=True, fill=True)
        pdf.ln(2)
        if item['exigencia']:
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(100, 100, 100)
            exi = f"Exigência: {str(item['exigencia'])}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, exi)
            pdf.ln(2)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        res = str(item['resposta']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, res)
        pdf.ln(8)
    pdf.ln(20)
    if pdf.get_y() > 250: pdf.add_page()
    pdf.line(10, pdf.get_y(), 100, pdf.get_y())
    pdf.set_font("Arial", "B", 11)
    nome_l = str(nome).encode('latin-1', 'replace').decode('latin-1')
    cargo_l = str(cargo).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 5, nome_l, ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, cargo_l, ln=True)
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- FUNÇÃO DE CONSULTA À IA ---
def consultar_ia(exigencia, vectorstore, api_key, temperatura=0.0):
    docs = vectorstore.similarity_search(exigencia, k=3)
    contexto = "\n".join([d.page_content for d in docs])
    llm = ChatGroq(model="llama3-70b-8192", temperature=temperatura, api_key=api_key)
    template = f"""
    Você é um redator técnico ambiental.
    TAREFA: Responder tecnicamente à exigência.
    REGRAS DE OURO:
    1. SEJA SUCINTO. Maximo 3 parágrafos curtos.
    2. IMPESSOALIDADE TOTAL: Não use nomes de pessoas (General) nem de empresas.
    3. Use voz passiva: "Foi realizado", "Mantém-se".
    4. NÃO repita a pergunta. Vá direto à solução técnica.
    CONTEXTO (Gabarito):
    {{context}}
    EXIGÊNCIA:
    {{question}}
    RESPOSTA TÉCNICA:
    """
    chain = ChatPromptTemplate.from_template(template) | llm
    return chain.invoke({"context": contexto, "question": exigencia}).content

# --- CÉREBRO (CARREGADOR DO BANCO DE DADOS) ---
@st.cache_resource
def carregar_cerebro():
    # --- MUDANÇA PARA DEPLOY: Usando caminhos relativos ---
    NOME_BANCO = "banco_chroma"
    MODELO_EMBEDDINGS = "all-MiniLM-L6-v2"
    
    embedding_function = HuggingFaceEmbeddings(model_name=MODELO_EMBEDDINGS)
    
    if os.path.exists(NOME_BANCO):
        print(f"🧠 Carregando cérebro ChromaDB da pasta '{NOME_BANCO}'...")
        vectorstore = Chroma(
            persist_directory=NOME_BANCO, 
            embedding_function=embedding_function
        )
        print("✅ Cérebro carregado com sucesso!")
        return vectorstore
    else:
        return None

# --- INÍCIO DA INTERFACE STREAMLIT ---

vectorstore = carregar_cerebro()

if "relatorio" not in st.session_state: st.session_state.relatorio = []
if "fila_exigencias" not in st.session_state: st.session_state.fila_exigencias = []
if "dados_auto" not in st.session_state: st.session_state.dados_auto = {"empresa": "", "cnpj": "", "end": "", "cid": ""}

# BARRA LATERAL
with st.sidebar:
    st.header("🔑 Acesso")
    # --- VERSÃO SEGURA PARA DEPLOY ---
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("Chave API carregada!")
    except:
        st.error("Chave 'GROQ_API_KEY' não encontrada. Adicione-a aos segredos do seu app no Streamlit Cloud.")
        st.stop()
        
    st.header("📂 Operação com PDF")
    uploaded_file = st.file_uploader("Subir Licença (PDF)", type="pdf")
    if uploaded_file:
        st.markdown("### Selecione a Tática:")
        if st.button("🕵️ IMPORTAR TUDO (AUTO)", type="primary"):
            with st.spinner("Extraindo Dados e Perguntas..."):
                txt_dados, txt_exigencias = processar_pdf_completo(uploaded_file, api_key)
                linhas = txt_dados.split('\n')
                for l in linhas:
                    if "EMPRESA:" in l: st.session_state.dados_auto["empresa"] = l.replace("EMPRESA:", "").strip()
                    if "CNPJ:" in l: st.session_state.dados_auto["cnpj"] = l.replace("CNPJ:", "").strip()
                    if "ENDERECO:" in l: st.session_state.dados_auto["end"] = l.replace("ENDERECO:", "").strip()
                    if "CIDADE:" in l: st.session_state.dados_auto["cid"] = l.replace("CIDADE:", "").strip()
                raw_list = txt_exigencias.split('###')
                st.session_state.fila_exigencias = [item.strip() for item in raw_list if len(item.strip()) > 10]
                st.success("Tudo carregado!")
                st.rerun()
        if st.button("📝 SÓ CADASTRO (MANUAL)"):
            with st.spinner("Lendo apenas o cabeçalho..."):
                txt_dados = processar_apenas_cadastro(uploaded_file, api_key)
                linhas = txt_dados.split('\n')
                for l in linhas:
                    if "EMPRESA:" in l: st.session_state.dados_auto["empresa"] = l.replace("EMPRESA:", "").strip()
                    if "CNPJ:" in l: st.session_state.dados_auto["cnpj"] = l.replace("CNPJ:", "").strip()
                    if "ENDERECO:" in l: st.session_state.dados_auto["end"] = l.replace("ENDERECO:", "").strip()
                    if "CIDADE:" in l: st.session_state.dados_auto["cid"] = l.replace("CIDADE:", "").strip()
                st.session_state.fila_exigencias = [] 
                st.success("Cadastro preenchido! Insira as perguntas manualmente.")
                st.rerun()
    st.markdown("---")
    st.header("📝 Cliente")
    INPUT_EMPRESA = st.text_input("Empresa", st.session_state.dados_auto["empresa"])
    INPUT_CNPJ = st.text_input("CNPJ", st.session_state.dados_auto["cnpj"])
    INPUT_ENDERECO = st.text_input("Endereço", st.session_state.dados_auto["end"])
    INPUT_CIDADE = st.text_input("Cidade", st.session_state.dados_auto["cid"])
    st.markdown("---")
    st.info("Assinatura:")
    INPUT_NOME = st.text_input("Nome", "Engenheiro Responsável")
    INPUT_CARGO = st.text_input("Cargo", "Diretor Técnico")

# --- CORPO PRINCIPAL DA INTERFACE ---
st.title("🛡️ SISTEMA DE DEFESA AMBIENTAL")

if not vectorstore:
    st.error("Cérebro não encontrado. Rode 'treinar.py' para criar o banco de dados vetorial.")
    st.stop()

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("1. Fila de Exigências")
    if st.session_state.fila_exigencias:
        st.success(f"Modo Automático: {len(st.session_state.fila_exigencias)} itens na fila.")
        opcoes = [f"{i+1}. {item[:50]}..." for i, item in enumerate(st.session_state.fila_exigencias)]
        idx = st.selectbox("Selecione:", range(len(opcoes)), format_func=lambda x: opcoes[x])
        exigencia_atual = st.session_state.fila_exigencias[idx]
        st.text_area("Texto:", value=exigencia_atual, height=150, disabled=True)
        if st.button("RESPONDER >>"):
            st.session_state.editor_exigencia = exigencia_atual
            st.session_state.editor_indice = idx
            if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
            st.rerun()
    else:
        st.info("Fila vazia. Adicione itens manualmente.")
        if st.button("➕ CRIAR ITEM MANUAL"):
            st.session_state.editor_exigencia = ""
            st.session_state.editor_indice = -1
            if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
            st.rerun()

with col2:
    st.subheader("2. Editor Tático")
    if "editor_exigencia" in st.session_state:
        tit_padrao = f"Item {len(st.session_state.relatorio)+1}"
        titulo_usuario = st.text_input("Título", tit_padrao)
        texto_exigencia = st.text_area("Exigência:", value=st.session_state.editor_exigencia, height=150)
        if "editor_resposta" not in st.session_state:
            if st.button("GERAR SOLUÇÃO ⚡", type="primary"):
                with st.spinner("Consultando Base Técnica..."):
                    res = consultar_ia(texto_exigencia, vectorstore, api_key, 0.0)
                    st.session_state.editor_resposta = res
                    st.rerun()
        if "editor_resposta" in st.session_state:
            if st.button("🔄 REFAZER (Outra abordagem)"):
                with st.spinner("Reformulando..."):
                    res = consultar_ia(texto_exigencia, vectorstore, api_key, 0.3)
                    st.session_state.editor_resposta = res
                    st.rerun()
            resposta_final = st.text_area("Resposta:", value=st.session_state.editor_resposta, height=200)
            c1, c2 = st.columns(2)
            if c1.button("✅ APROVAR"):
                st.session_state.relatorio.append({"titulo": titulo_usuario, "exigencia": texto_exigencia, "resposta": resposta_final})
                idx = st.session_state.get("editor_indice", -1)
                if idx >= 0 and idx < len(st.session_state.fila_exigencias): 
                    st.session_state.fila_exigencias.pop(idx)
                del st.session_state.editor_exigencia
                if "editor_resposta" in st.session_state:
                    del st.session_state.editor_resposta
                st.rerun()
            if c2.button("CANCELAR"):
                del st.session_state.editor_exigencia
                if "editor_resposta" in st.session_state:
                    del st.session_state.editor_resposta
                st.rerun()

st.markdown("---")
st.subheader("3. Relatório Final")
for i, item in enumerate(st.session_state.relatorio):
    with st.expander(f"{item['titulo']}"):
        st.write(item['resposta'])
        if st.button("X", key=f"d{i}"):
            st.session_state.relatorio.pop(i)
            st.rerun()

if st.session_state.relatorio:
    pdf = gerar_pdf_final(st.session_state.relatorio, INPUT_EMPRESA, INPUT_CNPJ, INPUT_ENDERECO, INPUT_CIDADE, INPUT_NOME, INPUT_CARGO)
    st.download_button("📄 BAIXAR PDF", pdf, "Relatorio.pdf", "application/pdf", type="primary")

### FIM DO ARQUIVO COMPLETO: app.py (VERSÃO FINAL PARA DEPLOY) ###