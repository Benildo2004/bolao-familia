import streamlit as st
import pandas as pd
import requests
import json
import os

# --- FILE TO SAVE DATA ---
DATA_FILE = "participantes.json"


def carregar_dados():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def salvar_dados(dados):
    with open(DATA_FILE, "w") as f:
        json.dump(dados, f, indent=4)


# --- CONFIG ---
st.set_page_config(page_title="Bolão Familiar", layout="wide")

# Initialize data
if 'participantes' not in st.session_state:
    st.session_state.participantes = carregar_dados()

# --- API MEGA SENA ---


@st.cache_data(ttl=3600)
def buscar_resultados():
    try:
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena"
        return requests.get(url).json()
    except:
        return []


resultados = buscar_resultados()
todos_sorteados = set()
for r in resultados:
    todos_sorteados.update([int(n) for n in r['dezenas']])

# --- SIDEBAR ---
menu = st.sidebar.selectbox(
    "Navegação", ["Ranking", "Cadastrar", "Financeiro"])

if menu == "Cadastrar":
    st.header("📝 Inscrição de Familiar")
    nome = st.text_input("Nome")
    nums = st.text_input("10 números (separados por vírgula)")

    if st.button("Salvar Jogo"):
        try:
            lista = [int(n.strip()) for n in nums.split(",")]
            if len(lista) == 10:
                novo = {"nome": nome, "numeros": lista}
                st.session_state.participantes.append(novo)
                salvar_dados(st.session_state.participantes)
                st.success("Salvo com sucesso!")
            else:
                st.error("Escolha 10 números.")
        except:
            st.error("Erro no formato.")

elif menu == "Ranking":
    st.header("🏆 Classificação Atual")
    if not st.session_state.participantes:
        st.write("Ninguém cadastrado.")
    else:
        tabela = []
        for p in st.session_state.participantes:
            acertos = [n for n in p['numeros'] if n in todos_sorteados]
            tabela.append({
                "Nome": p['nome'],
                "Acertos": len(acertos),
                "Números": p['numeros'],
                "Já Sorteados": acertos
            })

        df = pd.DataFrame(tabela).sort_values(by="Acertos", ascending=False)
        st.dataframe(df, use_container_width=True)

        # Check for winner
        vencedores = df[df["Acertos"] >= 10]
        if not vencedores.empty:
            st.balloons()
            st.success(f"TEMOS UM GANHADOR: {vencedores['Nome'].tolist()}")

            min_pts = df["Acertos"].min()
            lanternas = df[df["Acertos"] == min_pts]["Nome"].tolist()
            st.warning(f"Lanterna(s) (25%): {lanternas} com {min_pts} pontos")

elif menu == "Financeiro":
    qtd = len(st.session_state.participantes)
    total = qtd * 50
    st.metric("Total Arrecadado", f"R$ {total:.2f}")
    st.write(f"Vencedor (60%): R$ {total*0.6:.2f}")
    st.write(f"Lanterna (25%): R$ {total*0.25:.2f}")
