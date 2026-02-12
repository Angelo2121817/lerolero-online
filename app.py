### SISTEMA DE DEFESA AMBIENTAL - VERSÃO FINAL COMPLETA ###

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

# --- ESTADO DA SESSÃO (INICIALIZAÇÃO) ---
if "relatorio" not in st.session_state: st.session_state.relatorio = []
if "fila_exigencias" not in st.session_state: st.session_state.fila_exigencias = []
if "dados_auto" not in st.session_state: 
    st.session_state.dados_auto = {"empresa": "", "cnpj": "", "endereco": "", "cidade": ""}

# --- CENTRO DE CONTROLE ESTÉTICO ---
with st.sidebar:
    st.subheader("🎨 Estilo do Terminal")
    tema = st.selectbox("Selecione o Visual:", [
        "Moderno Executivo", "Hacker Verde", "Cyberpunk Neon", "Papel Digital", 
        "Modo Noturno", "Deep Sea", "Escritório", "Minimalista", "Metal Química", "Sunset"
    ], index=6) # <-- TEMA PADRÃO "ESCRITÓRIO"

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

# --- FUNÇÕES DE EXTRAÇÃO E PROCESSAMENTO ---

### INÍCIO DO NOVO CÓDIGO ###

### INÍCIO DO CÓDIGO A SER SUBSTITUÍDO ###

def extrair_dados_cadastrais_do_texto(texto_llm):
    """Converte o texto bruto da IA em um dicionário de dados."""
    dados = {"empresa": "", "cnpj": "", "endereco": "", "cidade": ""}
    padroes = {
        "empresa": r"EMPRESA:\s*(.+)", 
        "cnpj": r"CNPJ:\s*(.+)",
        "endereco": r"ENDERECO:\s*(.+)", 
        "cidade": r"CIDADE:\s*(.+)"
    }
    for chave, padrao in padroes.items():
        match = re.search(padrao, texto_llm, re.IGNORECASE)
        if match: 
            dados[chave] = match.group(1).strip()
    return dados

### FIM DO CÓDIGO A SER SUBSTITUÍDO ###

### FIM DO NOVO CÓDIGO ###

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

        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0, api_key=api_key)

        template_dados = """
        Analise o texto da licença ambiental abaixo e extraia os dados do LICENCIADO.
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
        SUA MISSÃO: Listar todas as EXIGÊNCIAS TÉCNICAS que o cliente precisa cumprir.
        REGRAS:
        1. NUNCA escreva textos introdutórios como "Aqui estão as exigências...".
        2. Ignore leis, artigos e preâmbulos.
        3. Copie o texto fiel da exigência.
        4. Separe cada exigência EXCLUSIVAMENTE com o delimitador "###".
        TEXTO: {texto}
        RESPOSTA (APENAS AS EXIGÊNCIAS, SEM NADA ANTES OU DEPOIS):
        """
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
            
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0, api_key=api_key)
        template_dados = """
        Extraia os dados cadastrais.
        TEXTO: {texto}
        RETORNE APENAS NESTE FORMATO:
        EMPRESA: (Razão Social)
        CNPJ: (CNPJ)
        ENDERECO: (Logradouro)
        CIDADE: (Cidade - UF)
        """
        chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
        return chain_dados.invoke({"texto": texto_curto}).content
    except Exception as e:
        return f"ERRO: {e}"

def consultar_ia(exigencia, vectorstore, api_key, temperatura=0.0, modo="media"):
    docs = vectorstore.similarity_search(exigencia, k=3)
    contexto = "\n".join([d.page_content for d in docs])
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=temperatura, api_key=api_key)
    instrucoes_modo = {
        "curta": "ESTILO: CURTO E GROSSO. FOCO: Diga apenas que a exigência foi cumprida.",
        "media": "ESTILO: EQUILIBRADO E TÉCNICO. FOCO: Confirme o atendimento e explique brevemente.",
        "avancada": "ESTILO: TÉCNICO DETALHADO. FOCO: Explique o funcionamento técnico completo."
    }.get(modo, "ESTILO: TÉCNICO.")
    template = f"""
    Você é um Engenheiro Ambiental Sênior. {instrucoes_modo}
    REGRAS GERAIS: Use voz passiva, seja impessoal, não repita a pergunta.
    CONTEXTO (Gabarito): {{context}}
    EXIGÊNCIA (Pergunta): {{question}}
    RESPOSTA:
    """
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
        embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return Chroma(persist_directory=NOME_BANCO, embedding_function=embedding_function)
    return construir_cerebro()

### INÍCIO DO NOVO CÓDIGO ###

### INÍCIO DO NOVO CÓDIGO ###

# --- FUNÇÃO DE GERAR PDF FINAL ---
### INÍCIO DO NOVO CÓDIGO ###

# --- FUNÇÃO DE GERAR PDF FINAL ---
### INÍCIO DO NOVO CÓDIGO ###

### INÍCIO DO NOVO CÓDIGO ###

# --- FUNÇÃO DE GERAR PDF FINAL ---
def gerar_pdf_final(itens, empresa, cidade, nome, cargo):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Limpeza robusta de TODOS os caracteres indesejados
    empresa_limpa = str(empresa).strip().strip("'\"“”*")
    cidade_limpa = str(cidade).strip().strip("'\"“”*")
    nome_limpo = str(nome).strip().strip("'\"“”*")
    cargo_limpo = str(cargo).strip().strip("'\"“”*")

    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, empresa_limpa.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "RELATORIO DE ATENDIMENTO AS EXIGENCIAS TECNICAS", ln=True, align="C")
    pdf.ln(10)
    
    for item in itens:
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        tit = str(item['titulo']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 8, tit, ln=True, fill=True, align="C")
        pdf.ln(2)
        if item['exigencia']:
            pdf.set_font("Arial", "I", 9)
            pdf.set_text_color(100, 100, 100)
            exi = f"Exigencia: {str(item['exigencia'])}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, exi)
            pdf.ln(2)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        res = str(item['resposta']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, res)
        pdf.ln(8)
        
    # Assinatura
    if pdf.get_y() > 240: pdf.add_page()
    pdf.ln(10)
    
    # --- CIRURGIA FINAL E DEFINITIVA PARA A LINHA DA DATA ---
    # 1. Prepara a data formatada
    hoje = datetime.date.today()
    meses = {
        "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril", 
        "05": "maio", "06": "junho", "07": "julho", "08": "agosto", 
        "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro"
    }
    data_formatada = f"{hoje.day} de {meses[hoje.strftime('%m')]} de {hoje.year}"
    
    # 2. Cria a string completa da linha
    linha_cidade_data = f"{cidade_limpa}, {data_formatada}"
    
    # 3. Define a fonte EXATAMENTE antes de escrever
    pdf.set_font("Arial", "", 11)
    
    # 4. Escreve a linha completa de uma só vez
    pdf.cell(0, 10, linha_cidade_data.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    
    # --- FIM DA CIRURGIA ---
    
    pdf.ln(15)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, nome_limpo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, cargo_limpo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    
    return pdf.output(dest="S").encode("latin-1", "replace")

### FIM DO NOVO CÓDIGO ###
### FIM DO NOVO CÓDIGO ###
# --- INTERFACE PRINCIPAL ---
vectorstore = carregar_ou_construir_cerebro()

### INÍCIO DO NOVO CÓDIGO ###

with st.sidebar:
    st.header("🔑 Acesso")
    try:
        # A chave é carregada silenciosamente. Se falhar, o app para.
        api_key = st.secrets["GROQ_API_KEY"]
    except:
        st.error("Chave 'GROQ_API_KEY' não encontrada.")
        st.stop()

    # <<< CIRURGIA 1: Botão para zerar a sessão.
    if st.button("Nova Análise 🔄"):
        # Limpa todas as variáveis de sessão para recomeçar
        st.session_state.relatorio = []
        st.session_state.fila_exigencias = []
        st.session_state.dados_auto = {"empresa": "", "cnpj": "", "endereco": "", "cidade": ""}
        # Limpa também os estados temporários do editor, se existirem
        if "editor_exigencia" in st.session_state:
            del st.session_state.editor_exigencia
        if "editor_resposta" in st.session_state:
            del st.session_state.editor_resposta
        st.rerun()

    st.markdown("---")
    uploaded_file = st.file_uploader("Subir Licença (PDF)", type="pdf")
    
    if uploaded_file:
        st.markdown("### Selecione a Tática:")
        
        if st.button("🕵️ IMPORTAR TUDO (AUTO)", type="primary"):
            with st.spinner("Extraindo Dados e Perguntas..."):
                txt_dados, txt_exigencias = processar_pdf_completo(uploaded_file, api_key)
                
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
    INPUT_NOME = st.text_input("Assinatura (Nome)", "Ângelo Aparecido Amadeu Júnior")
    INPUT_CARGO = st.text_input("Cargo", "Diretor Técnico")

### FIM DO NOVO CÓDIGO ###

# CORPO DA PÁGINA
st.title("🛡️ CENTRAL DE DEFESA AMBIENTAL")
if not vectorstore: st.warning("Atenção: Base de conhecimento (cérebro) não encontrada. As respostas da IA serão baseadas apenas no conhecimento geral.")
col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("1. Fila de Exigências")
    if st.session_state.fila_exigencias:
        st.info(f"Existem {len(st.session_state.fila_exigencias)} itens para processar.")
        opcoes = [f"{i+1}. {item[:60]}..." for i, item in enumerate(st.session_state.fila_exigencias)]
        idx = st.selectbox("Selecione o item:", range(len(opcoes)), format_func=lambda x: opcoes[x])
        exigencia_selecionada = st.session_state.fila_exigencias[idx]
        st.text_area("Texto da Exigência:", value=exigencia_selecionada, height=150, disabled=True)
        if st.button("RESPONDER ESTE ITEM >>"):
            st.session_state.editor_exigencia = exigencia_selecionada
            st.session_state.editor_indice = idx
            if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
            st.rerun()
    else:
        st.write("Fila vazia. Importe um PDF ou adicione manualmente.")
        if st.button("➕ ADICIONAR ITEM MANUAL"):
            st.session_state.editor_exigencia = ""
            if "editor_indice" in st.session_state: del st.session_state.editor_indice
            st.rerun()
### INÍCIO DO NOVO CÓDIGO ###

with col2:
    st.subheader("2. Editor Técnico")
    if "editor_exigencia" in st.session_state:
        # Configurações de resposta
        modo = st.radio("Profundidade da Resposta:", ["curta", "media", "avancada"], index=0, horizontal=True) # Mantém a resposta curta como padrão
        
        tit_sugerido = f"Item {len(st.session_state.relatorio) + 1}"
        titulo_item = st.text_input("Título do Relatório:", tit_sugerido)
        texto_exigencia = st.text_area("Exigência:", value=st.session_state.editor_exigencia, height=100)
        
        if "editor_resposta" not in st.session_state:
            if st.button("GERAR RESPOSTA TÉCNICA ⚡", type="primary"):
                if not vectorstore:
                    st.error("Base de conhecimento não encontrada. Resposta não pode ser gerada.")
                else:
                    with st.spinner("Consultando base técnica..."):
                        resposta = consultar_ia(texto_exigencia, vectorstore, api_key, modo=modo)
                        st.session_state.editor_resposta = resposta
                        st.rerun()
        
        if "editor_resposta" in st.session_state:
            resposta_final = st.text_area("Resposta da IA (Editável):", value=st.session_state.editor_resposta, height=200)
            
            c1, c2 = st.columns(2)
            if c1.button("✅ APROVAR E SALVAR"):
                # 1. Salva o item atual no relatório
                st.session_state.relatorio.append({
                    "titulo": titulo_item, 
                    "exigencia": texto_exigencia, 
                    "resposta": resposta_final
                })
                
                # 2. Remove o item da fila de exigências
                idx_antigo = st.session_state.get("editor_indice", -1)
                if 0 <= idx_antigo < len(st.session_state.fila_exigencias):
                    st.session_state.fila_exigencias.pop(idx_antigo)
                
                # <<< CIRURGIA: Lógica para avançar para o próximo item automaticamente >>>
                
                # 3. Limpa a resposta do editor atual
                del st.session_state.editor_resposta
                
                # 4. Verifica se ainda há itens na fila
                if st.session_state.fila_exigencias:
                    # Pega o próximo item (que agora está no mesmo índice do que foi removido)
                    # Garante que o índice não seja maior que a lista
                    novo_idx = min(idx_antigo, len(st.session_state.fila_exigencias) - 1)
                    
                    # Prepara o editor para o próximo item
                    st.session_state.editor_exigencia = st.session_state.fila_exigencias[novo_idx]
                    st.session_state.editor_indice = novo_idx
                else:
                    # Se a fila acabou, limpa o editor completamente
                    del st.session_state.editor_exigencia
                
                # 5. Reinicia a página para mostrar o próximo item ou a tela limpa
                st.rerun()
                
            if c2.button("❌ CANCELAR"):
                del st.session_state.editor_exigencia
                if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
                st.rerun()

### FIM DO NOVO CÓDIGO ###
st.markdown("---")
st.subheader("3. Visualização do Relatório")
if st.session_state.relatorio:
    for i, item in enumerate(st.session_state.relatorio):
        with st.expander(f"📌 {item['titulo']}"):
            st.write(f"**Exigência:** {item['exigencia']}")
            st.markdown(f"**Resposta:**\n{item['resposta']}")
            if st.button("Remover Item", key=f"del_{i}"):
                st.session_state.relatorio.pop(i)
                st.rerun()
    st.markdown("---")
    pdf_bytes = gerar_pdf_final(st.session_state.relatorio, INPUT_EMPRESA, INPUT_CIDADE, INPUT_NOME, INPUT_CARGO)
    st.download_button(label="📄 BAIXAR RELATÓRIO EM PDF", data=pdf_bytes, file_name=f"Relatorio_Defesa_{INPUT_EMPRESA}.pdf", mime="application/pdf", type="primary")
else:
    st.info("Ainda não há itens aprovados no relatório.")













