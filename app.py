import streamlit as st
import os
import datetime
import re # <-- Nova Importação para Regex
from pypdf import PdfReader
from pypdf.errors import PdfReadError # <-- Nova Importação para Erros Específicos
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Defesa Ambiental", layout="wide")
# --- CENTRO DE CONTROLE ESTÉTICO ---
with st.sidebar:
    st.subheader("🎨 Estilo do Terminal")
    tema = st.selectbox("Selecione o Visual:", [
        "Moderno Executivo", "Hacker Verde", "Cyberpunk Neon", "Papel Digital", 
        "Modo Noturno", "Deep Sea", "Escritório", "Minimalista", "Metal Química", "Sunset"
    ])

# Dicionário de Estilos
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
# --- FUNÇÃO AUXILIAR: EXTRAÇÃO DE DADOS CADASTRAIS ---
def extrair_dados_cadastrais_do_texto(texto_llm):
    """
    Extrai dados estruturados (empresa, cnpj, endereco, cidade) de um texto gerado pelo LLM.
    Usa expressões regulares para ser resiliente a pequenas variações de formatação.
    Retorna um dicionário com os dados encontrados.
    """
    dados = {
        "empresa": "",
        "cnpj": "",
        "endereco": "",
        "cidade": ""
    }
    
    # Padrões de regex para cada campo
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
        else:
            st.warning(f"⚠️ Aviso: Campo '{chave.upper()}' não encontrado na resposta do LLM.")
    
    return dados

# --- FUNÇÃO 1: EXTRAÇÃO INTELIGENTE (CADASTRO + PERGUNTAS) ---
def processar_pdf_completo(arquivo_pdf):
    """
    Processa um PDF completo, extraindo dados cadastrais e exigências.
    Retorna uma tupla (dados_cadastrais, lista_exigencias).
    Em caso de erro, retorna uma tupla com mensagens de erro claras.
    """
    try:
        # --- ETAPA 1: Leitura do PDF ---
        reader = PdfReader(arquivo_pdf)
        if len(reader.pages) == 0:
            return (
                "ERRO: O arquivo PDF está vazio.",
                "ERRO: O arquivo PDF está vazio."
            )
        
        texto_completo = ""
        for i, page in enumerate(reader.pages):
            try:
                extracted_text = page.extract_text()
                if extracted_text: # Adiciona apenas se houver texto
                    texto_completo += extracted_text + "\n"
            except Exception as e:
                # Em vez de quebrar, registra o erro e continua
                st.warning(f"⚠️ Aviso: Não foi possível extrair texto da página {i+1}.")
                continue
        
        if not texto_completo.strip():
            return (
                "ERRO: Não foi possível extrair nenhum texto do PDF. O arquivo pode estar escaneado (imagem) ou corrompido.",
                "ERRO: Não foi possível extrair nenhum texto do PDF. O arquivo pode estar escaneado (imagem) ou corrompido."
            )

        # --- ETAPA 2: Configuração e Uso do LLM ---
        try:
            llm = ChatOllama(model="llama3", temperature=0.0)
        except Exception as e:
            error_msg = f"ERRO: Falha ao inicializar o modelo LLM 'llama3'. Verifique se o Ollama está rodando e o modelo está instalado."
            return (error_msg, error_msg)

        # --- ETAPA 3: Extração de Dados Cadastrais ---
        template_dados = """
        Analise o texto da licença. Extraia dados do LICENCIADO.
        TEXTO: {texto}
        RETORNE APENAS NESTE FORMATO:
        EMPRESA: (Razão Social)
        CNPJ: (CNPJ)
        ENDERECO: (Logradouro)
        CIDADE: (Cidade - UF)
        """
        try:
            chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
            dados_cadastrais = chain_dados.invoke({"texto": texto_completo[:3000]}).content
            
            # Validação simples: verifica se a resposta contém as chaves esperadas
            if not all(key in dados_cadastrais for key in ["EMPRESA:", "CNPJ:", "ENDERECO:", "CIDADE:"]):
                st.warning("⚠️ Aviso: O formato da resposta para os dados cadastrais não é o esperado. Os dados podem estar incompletos.")
        except Exception as e:
            dados_cadastrais = f"ERRO: Falha ao extrair dados cadastrais. Detalhes: {str(e)[:100]}..."

        # --- ETAPA 4: Extração de Exigências (TEMPLATE CORRIGIDO - VERSÃO FINAL) ---
        template_exigencias = """
        Analise o texto da Licença Ambiental.
        SUA MISSÃO: Listar todas as EXIGÊNCIAS TÉCNICAS.

        REGRAS ABSOLUTAS:
        1. NUNCA, EM HIPÓTESE ALGUMA, NUMERE OS ITENS (não use 1., 2., 3., etc.).
        2. NUNCA escreva textos introdutórios (como "Aqui estão as exigências...") ou conclusivos.
        3. Ignore leis, artigos, preâmbulos e qualquer texto que não seja uma exigência direta.
        4. Copie o texto da exigência exatamente como está no documento.
        5. SEPARAR CADA EXIGÊNCIA EXCLUSIVAMENTE com o delimitador "###".
           Exemplo correto: "...exigência A... ### ...exigência B... ### ...exigência C..."

        TEXTO:
        {texto}
        
        RESPOSTA (APENAS AS EXIGÊNCIAS, SEM NADA ANTES OU DEPOIS):
        """
        try:
            chain_exig = ChatPromptTemplate.from_template(template_exigencias) | llm
            lista_exigencias = chain_exig.invoke({"texto": texto_completo}).content
            
            # Validação: Se não houver o delimitador, provavelmente não encontrou nada
            if "###" not in lista_exigencias:
                st.warning("⚠️ Aviso: Nenhuma exigência foi encontrada no documento ou o formato de saída não foi respeitado.")
        except Exception as e:
            lista_exigencias = f"ERRO: Falha ao extrair exigências. Detalhes: {str(e)[:100]}..."

        return dados_cadastrais, lista_exigencias

    except PdfReadError as e:
        error_msg = f"ERRO: O arquivo não é um PDF válido ou está corrompido."
        return (error_msg, error_msg)
    except Exception as e:
        error_msg = f"ERRO: Erro inesperado ao processar o PDF. Detalhes: {str(e)[:100]}..."
        return (error_msg, error_msg)


# --- FUNÇÃO 1.B: EXTRAÇÃO SÓ CADASTRO (Manual) ---
def processar_apenas_cadastro(arquivo_pdf):
    """
    Processa apenas as primeiras páginas de um PDF para extrair dados cadastrais.
    Retorna os dados cadastrais ou uma mensagem de erro.
    """
    try:
        reader = PdfReader(arquivo_pdf)
        if len(reader.pages) == 0:
            return "ERRO: O arquivo PDF está vazio."
        
        texto_completo = ""
        for i, page in enumerate(reader.pages):
            if i > 2: 
                break 
            try:
                extracted_text = page.extract_text()
                if extracted_text:
                    texto_completo += extracted_text + "\n"
            except Exception as e:
                st.warning(f"⚠️ Aviso: Não foi possível extrair texto da página {i+1}.")
                continue
        
        if not texto_completo.strip():
            return "ERRO: Não foi possível extrair texto das primeiras páginas do PDF."

        try:
            llm = ChatOllama(model="llama3", temperature=0.0)
        except Exception as e:
            return "ERRO: Falha ao inicializar o modelo LLM 'llama3'."

        template_dados = """
        Analise o texto da licença. Extraia dados do LICENCIADO.
        TEXTO: {texto}
        RETORNE APENAS NESTE FORMATO:
        EMPRESA: (Razão Social)
        CNPJ: (CNPJ)
        ENDERECO: (Logradouro)
        CIDADE: (Cidade - UF)
        """
        try:
            chain_dados = ChatPromptTemplate.from_template(template_dados) | llm
            dados_cadastrais = chain_dados.invoke({"texto": texto_completo}).content
            
            if not all(key in dados_cadastrais for key in ["EMPRESA:", "CNPJ:", "ENDERECO:", "CIDADE:"]):
                st.warning("⚠️ Aviso: O formato da resposta para os dados cadastrais não é o esperado.")
        except Exception as e:
            dados_cadastrais = f"ERRO: Falha ao extrair dados cadastrais. Detalhes: {str(e)[:100]}..."

        return dados_cadastrais

    except PdfReadError as e:
        return "ERRO: O arquivo não é um PDF válido ou está corrompido."
    except Exception as e:
        return f"ERRO: Erro inesperado ao processar o PDF. Detalhes: {str(e)[:100]}..."


# --- FUNÇÃO 2: GERAR PDF FINAL ---
def gerar_pdf_final(itens, empresa, cidade, nome, cargo):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- CABEÇALHO (SEM LOCAL E DATA) ---
    pdf.set_font("Arial", "B", 16)
    empresa_limpa = str(empresa).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"{empresa_limpa}", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "RELATORIO DE EXIGENCIAS TECNICAS", ln=True, align="C")
    pdf.ln(15) # Aumenta o espaço após o título
    
    # --- LISTA DE ITENS (SEM "ITEM X") ---
    for item in itens:
        # Remove "Item X" do título, tratando variações
        titulo_limpo = str(item['titulo'])
        titulo_limpo = re.sub(r'item\s*\d*\.?\s*', '', titulo_limpo, flags=re.IGNORECASE).strip()
        titulo_limpo = titulo_limpo.encode('latin-1', 'replace').decode('latin-1')

        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, titulo_limpo, ln=True, fill=True)
        pdf.ln(2)
        
        # Exigência
        if item['exigencia']:
            pdf.set_font("Arial", "I", 10)
            pdf.set_text_color(80, 80, 80)
            exigencia_limpa = f"Exigencia: {str(item['exigencia'])}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, exigencia_limpa)
            pdf.ln(2)
        
        # Resposta
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 11)
        resposta_limpa = str(item['resposta']).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, resposta_limpa)
        pdf.ln(10)
        
    # --- LOCAL E DATA (ANTES DA ASSINATURA, FORMATO LONGO E CENTRALIZADO) ---
    # Garante que a seção não quebre a página no meio
    if pdf.get_y() > 220:
        pdf.add_page()
        
    pdf.ln(10)
    
    # Dicionário de meses sem caracteres especiais
    meses = {
        "01": "janeiro", "02": "fevereiro", "03": "marco",
        "04": "abril", "05": "maio", "06": "junho",
        "07": "julho", "08": "agosto", "09": "setembro",
        "10": "outubro", "11": "novembro", "12": "dezembro"
    }
    hoje = datetime.date.today()
    data_longa = f"{hoje.day} de {meses[hoje.strftime('%m')]} de {hoje.year}"
    
    cidade_limpa = str(cidade).encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_font("Arial", "I", 11)
    pdf.cell(0, 8, f"{cidade_limpa}, {data_longa}", ln=True, align="C")
    pdf.ln(10)

    # --- ASSINATURA ---
    pdf.line(pdf.get_x() + 50, pdf.get_y(), pdf.get_x() + 150, pdf.get_y()) # Linha centralizada
    pdf.set_font("Arial", "B", 12)
    nome_limpo = str(nome).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, nome_limpo, ln=True, align="C")

    pdf.set_font("Arial", "", 10)
    cargo_limpo = str(cargo).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 5, cargo_limpo, ln=True, align="C")
        
    return pdf.output(dest="S").encode("latin-1", "replace")
# --- FUNÇÃO AUXILIAR: CONSULTAR IA (3 MODOS) ---
def consultar_ia(exigencia, vectorstore, temperatura=0.0, modo="media"):
    docs = vectorstore.similarity_search(exigencia, k=3)
    contexto = "\n".join([d.page_content for d in docs])
    
                llm = ChatGroq(
                model_name="llama3-70b-8192", 
                groq_api_key=st.secrets["GROQ_API_KEY"],
                temperature=temperatura
            )
    
    if modo == "curta":
        instrucoes_modo = """
        ESTILO: CURTO E GROSSO.
        TAMANHO: Máximo 1 parágrafo (3 a 5 linhas).
        FOCO: Diga apenas que a exigência foi cumprida e cite o equipamento/ação principal. Sem rodeios.
        """
    elif modo == "media":
        instrucoes_modo = """
        ESTILO: EQUILIBRADO E TÉCNICO.
        TAMANHO: Aproximadamente 2 parágrafos.
        FOCO: Confirme o atendimento da exigência e faça uma breve explicação técnica do funcionamento. Nem muito seco, nem muito detalhado.
        """
    else: # avançada
        instrucoes_modo = """
        ESTILO: TÉCNICO DETALHADO.
        TAMANHO: De 3 a 4 parágrafos.
        FOCO: Explique o funcionamento técnico completo, cite detalhes específicos do contexto, justifique a eficiência e use linguagem de engenharia elaborada.
        """

    template = f"""
    Você é um Engenheiro Ambiental Sênior.
    TAREFA: Responder à exigência abaixo com base no contexto.
    
    {instrucoes_modo}
    
    REGRAS GERAIS:
    1. IMPESSOALIDADE TOTAL: Não use nomes de pessoas. Use "A empresa", "Foi realizado".
    2. FATO: Use apenas informações do CONTEXTO.
    3. NÃO repita a pergunta.
    
    CONTEXTO (Gabarito):
    {{context}}
    
    EXIGÊNCIA (Pergunta):
    {{question}}
    
    RESPOSTA:
    """
    chain = ChatPromptTemplate.from_template(template) | llm
    return chain.invoke({"context": contexto, "question": exigencia}).content

# --- ESTADO DA SESSÃO ---
if "relatorio" not in st.session_state: st.session_state.relatorio = []
if "fila_exigencias" not in st.session_state: st.session_state.fila_exigencias = []
if "dados_auto" not in st.session_state: st.session_state.dados_auto = {"empresa": "", "cnpj": "", "end": "", "cid": ""}

# --- CARREGAR CÉREBRO ---
@st.cache_resource
def carregar_cerebro():
    #embeddings = OllamaEmbeddings(model="llama3")
    #try:
        #if os.path.exists("banco_faiss"):
        #    return FAISS.load_local("banco_faiss", embeddings, allow_dangerous_deserialization=True)
       # return None
   # except:
        return None

vectorstore = carregar_cerebro()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🛠️ Configuração")
    
    # BOTÃO DE ZERAR SISTEMA (NOVIDADE)
    if st.button("🗑️ ZERAR SISTEMA (NOVO)", type="secondary"):
        st.session_state.relatorio = []
        st.session_state.fila_exigencias = []
        st.session_state.dados_auto = {"empresa": "", "cnpj": "", "end": "", "cid": ""}
        if "editor_exigencia" in st.session_state: del st.session_state.editor_exigencia
        if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
        st.rerun()

    st.markdown("---")
    
    uploaded_file = st.file_uploader("Subir Licença (PDF)", type="pdf")
    
    if uploaded_file:
        st.markdown("### Selecione a Tática:")
        
        if st.button("🕵️ IMPORTAR TUDO (AUTO)", type="primary"):
            with st.spinner("Extraindo Dados e Perguntas..."):
                txt_dados, txt_exigencias = processar_pdf_completo(uploaded_file)
                
                # --- NOVA LÓGICA DE EXTRAÇÃO USANDO A FUNÇÃO AUXILIAR ---
                dados_extraidos = extrair_dados_cadastrais_do_texto(txt_dados)
                st.session_state.dados_auto["empresa"] = dados_extraidos["empresa"]
                st.session_state.dados_auto["cnpj"] = dados_extraidos["cnpj"]
                st.session_state.dados_auto["end"] = dados_extraidos["endereco"]
                st.session_state.dados_auto["cid"] = dados_extraidos["cidade"]
                
                raw_list = txt_exigencias.split('###')
                st.session_state.fila_exigencias = [item.strip() for item in raw_list if len(item.strip()) > 10]
                st.success("Tudo carregado!")
                st.rerun()

        if st.button("📝 SÓ CADASTRO (MANUAL)"):
            with st.spinner("Lendo apenas o cabeçalho..."):
                txt_dados = processar_apenas_cadastro(uploaded_file)
                
                # --- NOVA LÓGICA DE EXTRAÇÃO USANDO A FUNÇÃO AUXILIAR ---
                dados_extraidos = extrair_dados_cadastrais_do_texto(txt_dados)
                st.session_state.dados_auto["empresa"] = dados_extraidos["empresa"]
                st.session_state.dados_auto["cnpj"] = dados_extraidos["cnpj"]
                st.session_state.dados_auto["end"] = dados_extraidos["endereco"]
                st.session_state.dados_auto["cid"] = dados_extraidos["cidade"]
                
                st.session_state.fila_exigencias = [] 
                st.success("Cadastro pronto! Insira perguntas manualmente.")
                st.rerun()

    st.markdown("---")
    INPUT_EMPRESA = st.text_input("Nome da Empresa", st.session_state.dados_auto["empresa"] if st.session_state.dados_auto["empresa"] else "METAL QUÍMICA")
    INPUT_CIDADE = st.text_input("Cidade", st.session_state.dados_auto["cid"] if st.session_state.dados_auto["cid"] else "São José do Rio Preto - SP")
    INPUT_NOME = st.text_input("Seu Nome", "GENERAL")
    INPUT_CARGO = st.text_input("Seu Cargo", "Diretor Técnico")
    st.markdown("---")
    st.warning("Se o banco de dados tiver nomes de outras empresas, a IA tentará substituir pelo nome acima.")

# --- INTERFACE PRINCIPAL ---
st.title(f"🏭 {INPUT_EMPRESA} - Central de Defesa")

col_esq, col_dir = st.columns([1, 1])

# --- COLUNA DA ESQUERDA ---
with col_esq:
    st.subheader("1. Área de Trabalho")
    if st.session_state.fila_exigencias:
        st.success(f"Modo Automático: {len(st.session_state.fila_exigencias)} itens na fila.")
        opcoes = [f"{i+1}. {item[:50]}..." for i, item in enumerate(st.session_state.fila_exigencias)]
        idx = st.selectbox("Selecione:", range(len(opcoes)), format_func=lambda x: opcoes[x])
        exigencia_atual = st.session_state.fila_exigencias[idx]
        st.text_area("Texto Original:", value=exigencia_atual, height=150, disabled=True)
        
        if st.button("RESPONDER >>"):
            st.session_state.editor_exigencia = exigencia_atual
            st.session_state.editor_indice = idx
            if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
            st.rerun()
    else:
        st.info("Modo Manual: Digite a exigência abaixo.")
        st.markdown("---")
        exigencia_manual = st.text_area("Digite a Exigência:", height=150)
        if st.button("ENVIAR PARA O EDITOR >>"):
            if exigencia_manual:
                st.session_state.editor_exigencia = exigencia_manual
                st.session_state.editor_indice = -1
                if "editor_resposta" in st.session_state: del st.session_state.editor_resposta
                st.rerun()

# --- COLUNA DA DIREITA: O EDITOR ---
with col_dir:
    st.subheader("2. Editor Tático")
    
    if "editor_exigencia" in st.session_state:
        tit_padrao = f"Item {len(st.session_state.relatorio) + 1}"
        titulo_usuario = st.text_input("Título do Tópico", value=tit_padrao)
        st.info(f"Trabalhando em: {st.session_state.editor_exigencia[:100]}...")
        
        # --- O SELETOR DE CALIBRE (3 NÍVEIS) ---
        modo_resposta = st.radio(
            "Calibre da Resposta:",
            ["curta", "media", "avancada"],
            format_func=lambda x: {
                "curta": "🟢 Curta (Direta)",
                "media": "🟡 Média (Equilibrada)",
                "avancada": "🔴 Avançada (Detalhada)"
            }.get(x),
            horizontal=True,
            index=1 # Começa na Média
        )

        # BOTÃO GERAR
        if "editor_resposta" not in st.session_state:
            if st.button("GERAR RESPOSTA BLINDADA 🛡️", type="primary"):
                if not vectorstore:
                    st.error("Cérebro desligado. Rode 'treinar.py'.")
                else:
                    with st.spinner(f"Gerando resposta {modo_resposta}..."):
                        res = consultar_ia(st.session_state.editor_exigencia, vectorstore, temperatura=0.0, modo=modo_resposta)
                        st.session_state.editor_resposta = res
                        st.rerun()
        
        # ÁREA DE REVISÃO
        if "editor_resposta" in st.session_state:
            
            # Botão Refazer
            if st.button("🔄 REFAZER (TENTAR OUTRA)"):
                with st.spinner("Reformulando..."):
                    res = consultar_ia(st.session_state.editor_exigencia, vectorstore, temperatura=0.3, modo=modo_resposta)
                    st.session_state.editor_resposta = res
                    st.rerun()
            
            texto_final = st.text_area("Texto da Resposta:", value=st.session_state.editor_resposta, height=250)
            
            c1, c2 = st.columns(2)
            if c1.button("✅ ADICIONAR"):
                st.session_state.relatorio.append({
                    "titulo": titulo_usuario,
                    "exigencia": st.session_state.editor_exigencia,
                    "resposta": texto_final
                })
                
                # Remove da fila SE estiver no modo automático
                idx = st.session_state.get("editor_indice", -1)
                if idx >= 0 and idx < len(st.session_state.fila_exigencias): 
                    st.session_state.fila_exigencias.pop(idx)
                
                del st.session_state.editor_exigencia
                del st.session_state.editor_resposta
                st.success("Adicionado!")
                st.rerun()
                
            if c2.button("CANCELAR"):
                del st.session_state.editor_exigencia
                del st.session_state.editor_resposta
                st.rerun()

# --- RELATÓRIO FINAL ---
st.markdown("---")
st.subheader("3. Relatório Final")
for i, item in enumerate(st.session_state.relatorio):
    with st.expander(f"{item['titulo']}"):
        st.write(item['resposta'])
        if st.button("Remover", key=f"del_{i}"):
            st.session_state.relatorio.pop(i)
            st.rerun()
            
if len(st.session_state.relatorio) > 0:
    st.markdown("---")
    pdf_bytes = gerar_pdf_final(st.session_state.relatorio, INPUT_EMPRESA, INPUT_CIDADE, INPUT_NOME, INPUT_CARGO)
    st.download_button("📄 BAIXAR PDF FINAL", pdf_bytes, "Defesa_Cetesb.pdf", "application/pdf", type="primary")