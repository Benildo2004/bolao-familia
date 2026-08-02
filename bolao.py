import streamlit as st
import pandas as pd
import requests
from datetime import datetime

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
        res = requests.get(url).json()

        sorteados = set()
        detalhes = []
        for s in res:
            data_s = datetime.strptime(s['data'], "%d/%m/%Y")
            if data_s >= DATA_INICIO_BOLAO:
                dezenas = [int(n) for n in s['dezenas']]
                sorteados.update(dezenas)
                detalhes.append(
                    f"Concurso {s['concurso']} ({s['data']}): {s['dezenas']}")
        return sorteados, detalhes
    except:
        return set(), []


# --- INICIALIZAÇÃO ---
st.set_page_config(page_title="Bolão Família", layout="wide")
if 'participantes' not in st.session_state:
    st.session_state.participantes = []

sorteados, lista_concursos = buscar_resultados()

# --- SIDEBAR ---
st.sidebar.title("🎲 Menu")
aba = st.sidebar.radio(
    "Navegar:", ["📊 Ranking", "💰 Financeiro", "📅 Concursos", "⚙️ Organizador"])

# --- ABA: RANKING ---
if aba == "📊 Ranking":
    st.header(f"🏆 Classificação Atual")
    st.caption(
        f"Contando sorteios desde: {DATA_INICIO_BOLAO.strftime('%d/%m/%Y')}")

    if not st.session_state.participantes:
        st.info("Aguardando cadastro de participantes pelo Organizador.")
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
        st.table(df)  # Table é melhor para ver no celular

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
    for c in lista_concursos:
        st.write(c)

# --- ABA: ORGANIZADOR (SENHA) ---
elif aba == "⚙️ Organizador":
    st.header("Área Restrita")
    senha = st.text_input("Digite a senha para gerenciar", type="password")

    if senha == SENHA_ADMIN:
        st.success("Acesso Liberado")

        st.subheader("Subir Excel (.xlsx)")
        st.caption(
            "A planilha deve ter as colunas 'Nome' e 'Numeros' (separados por vírgula)")
        arq = st.file_uploader("Arquivo Excel", type="xlsx")
        if arq:
            if st.button("Processar Excel"):
                df_ex = pd.read_excel(arq)
                for _, row in df_ex.iterrows():
                    try:
                        n = str(row['Nome'])
                        nums = [int(i) for i in str(row['Numeros']).split(',')]
                        st.session_state.participantes.append(
                            {"nome": n, "numeros": nums})
                    except:
                        continue
                st.rerun()

        if st.button("❌ LIMPAR TODOS OS DADOS (Nova Rodada)"):
            st.session_state.participantes = []
            st.rerun()
    elif senha != "":
        st.error("Senha Incorreta")
