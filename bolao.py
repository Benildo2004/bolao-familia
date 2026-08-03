import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os

# --- CONFIGURAÇÃO MANUAL (Altere aqui para cada nova rodada) ---
DATA_INICIO_BOLAO = datetime(2026, 7, 26)
SENHA_ADMIN = "familia123"  # Altere sua senha aqui

# --- CONFIGURAÇÃO DE PREÇOS ---
VALOR_COTA = 50.0
PERC_GANHADOR = 0.60
PERC_LANTERNA = 0.25

# --- FUNÇÃO DE BUSCA NA API ---


@st.cache_data(ttl=3600)
def buscar_resultados():
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
        # timeout adicionado para não travar o app se a Caixa estiver lenta
        res = requests.get(url, timeout=10).json()

        sorteados = set()
        detalhes = []
        for s in res:
            data_s = datetime.strptime(s['data'], "%d/%m/%Y")
            if data_s >= DATA_INICIO_BOLAO:
                dezenas = [int(n) for n in s['dezenas']]
                sorteados.update(dezenas)
                detalhes.append(
                    f"Concurso {s['concurso']} ({s['data']}): {s['dezenas']}")
        return sorteados, detalhes, False  # False indica que NÃO houve erro
    except Exception:
        return set(), [], True  # True indica que houve erro na conexão

# --- FUNÇÃO PARA CARREGAR EXCEL AUTOMATICAMENTE ---


def carregar_planilha_local():
    lista_temp = []
    # Verifica se o arquivo existe no repositório do GitHub
    if os.path.exists("bolao_atual.xlsx"):
        try:
            df_ex = pd.read_excel("bolao_atual.xlsx")
            for _, row in df_ex.iterrows():
                try:
                    n = str(row['Nome'])
                    # O .strip() limpa espaços antes e depois do número
                    nums = [int(i.strip())
                            for i in str(row['Numeros']).split(',')]
                    lista_temp.append({"nome": n, "numeros": nums})
                except:
                    continue
        except Exception:
            pass
    return lista_temp


# --- INICIALIZAÇÃO ---
st.set_page_config(page_title="Bolão Família", layout="wide")

# Carrega os dados automaticamente se a lista de participantes estiver vazia
if 'participantes' not in st.session_state or not st.session_state.participantes:
    st.session_state.participantes = carregar_planilha_local()

sorteados, lista_concursos, erro_api = buscar_resultados()

# --- SIDEBAR ---
st.sidebar.title("🎲 Menu")
aba = st.sidebar.radio(
    "Navegar:", ["📊 Ranking", "💰 Financeiro", "📅 Concursos", "⚙️ Organizador"])

# Aviso visual na barra lateral caso a API falhe
if erro_api:
    st.sidebar.error(
        "⚠️ Erro de conexão com a loteria. Resultados podem estar desatualizados.")

# --- ABA: RANKING ---
if aba == "📊 Ranking":
    st.header(f"🏆 Classificação Atual")
    st.caption(
        f"Contando sorteios desde: {DATA_INICIO_BOLAO.strftime('%d/%m/%Y')}")

    if not st.session_state.participantes:
        st.info(
            "Nenhum participante encontrado. O arquivo 'bolao_atual.xlsx' não foi lido ou está vazio.")
    else:
        dados = []
        for p in st.session_state.participantes:
            acertos = [n for n in p['numeros'] if n in sorteados]
            dados.append({
                "Nome": p['nome'],
                "Acertos": len(acertos),
                "Faltam": 10 - len(acertos),
                "Números Escolhidos": sorted(p['numeros']),
                "Números Sorteados": sorted(acertos)
            })

        df = pd.DataFrame(dados).sort_values(by="Acertos", ascending=False)
        st.table(df)

        # Lógica de Vitória
        vencedores = df[df["Acertos"] >= 10]
        if not vencedores.empty:
            st.balloons()
            st.success(
                f"🏁 RODADA ENCERRADA! Ganhador(es): {', '.join(vencedores['Nome'].tolist())}")
            min_p = df["Acertos"].min()
            lanternas = df[df["Acertos"] == min_p]["Nome"].tolist()
            st.warning(
                f"🐢 Lanterna(s) (25% do prêmio): {', '.join(lanternas)} com {min_p} acertos.")

# --- ABA: FINANCEIRO ---
elif aba == "💰 Financeiro":
    st.header("💰 Resumo Financeiro")
    total_p = len(st.session_state.participantes)
    arrecadado = total_p * VALOR_COTA
    st.metric("Total de Participantes", total_p)
    col1, col2 = st.columns(2)
    col1.metric("Prêmio 1º Lugar (60%)",
                f"R$ {arrecadado * PERC_GANHADOR:.2f}")
    col2.metric("Prêmio Lanterna (25%)",
                f"R$ {arrecadado * PERC_LANTERNA:.2f}")

# --- ABA: CONCURSOS ---
elif aba == "📅 Concursos":
    st.header("Sorteios Válidos")
    if erro_api:
        st.warning("A lista de concursos não pôde ser atualizada neste momento.")
    for c in lista_concursos:
        st.write(c)

# --- ABA: ORGANIZADOR (SENHA) ---
elif aba == "⚙️ Organizador":
    st.header("Área Restrita")
    senha = st.text_input("Digite a senha para gerenciar", type="password")

    if senha == SENHA_ADMIN:
        st.success("Acesso Liberado")

        st.subheader("Subir Excel (.xlsx) Manualmente")
        st.caption(
            "Use apenas se quiser sobrescrever a planilha oficial temporariamente.")
        arq = st.file_uploader("Arquivo Excel", type="xlsx")
        if arq:
            if st.button("Processar Excel"):
                st.session_state.participantes = []  # Limpa antes de carregar o novo
                df_ex = pd.read_excel(arq)
                for _, row in df_ex.iterrows():
                    try:
                        n = str(row['Nome'])
                        nums = [int(i.strip())
                                for i in str(row['Numeros']).split(',')]
                        st.session_state.participantes.append(
                            {"nome": n, "numeros": nums})
                    except:
                        continue
                st.rerun()

        st.divider()
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Recarregar Planilha Oficial"):
                st.session_state.participantes = carregar_planilha_local()
                st.rerun()
        with col_btn2:
            if st.button("❌ LIMPAR TODOS OS DADOS"):
                st.session_state.participantes = []
                st.rerun()

    elif senha != "":
        st.error("Senha Incorreta")
