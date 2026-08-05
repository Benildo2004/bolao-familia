import json
import os
import requests
import streamlit as st
import pandas as pd

# Nome dos arquivos locais
ARQUIVO_DADOS = "participantes.json"
PLANILHA_EXCEL = "bolao_atual.xlsx"
SENHA_ADMIN = "familia123"

st.set_page_config(page_title="Bolão da Família",
                   page_icon="⚽", layout="centered")

# --- FUNÇÕES DE DADOS ---


def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, dict):
                    return dados
        except:
            pass
    return {}


def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


def ler_excel_local():
    if os.path.exists(PLANILHA_EXCEL):
        try:
            df = pd.read_excel(PLANILHA_EXCEL)
            return df
        except Exception as e:
            st.error(f"Erro ao ler a planilha Excel: {e}")
    return None

# --- BUSCA DE RESULTADOS ROBUSTA ---


@st.cache_data(ttl=3600)
def buscar_resultados_lotofacil():
    concursos = {}

    # Tentativa 1: API Loterias API
    try:
        response = requests.get(
            "https://loteriasapi.com/api/v2/lotofacil", timeout=5)
        if response.status_code == 200:
            dados = response.json()
            lista_itens = dados if isinstance(dados, list) else [dados]
            for c in lista_itens:
                num = str(c.get("concurso") or c.get("numero") or "")
                dezenas = c.get("dezenas") or c.get(
                    "dezenasSorteadas") or c.get("listaDezenas")
                data = c.get("data")
                if num and dezenas:
                    concursos[num] = {"data": data, "dezenas": [
                        str(d).zfill(2) for d in dezenas]}
    except:
        pass

    if concursos:
        return concursos

    # Tentativa 2: BrasilAPI
    try:
        response = requests.get(
            "https://brasilapi.com.br/api/loterias/v1/lotofacil", timeout=5)
        if response.status_code == 200:
            dados = response.json()
            num = str(dados.get("concurso", ""))
            dezenas = [str(d).zfill(2) for d in dados.get("dezenas", [])]
            data = dados.get("data", "")
            if num and dezenas:
                concursos[num] = {"data": data, "dezenas": dezenas}
    except:
        pass

    return concursos


# Inicializa dados salvos com segurança
dados_app = carregar_dados()
if "concursos_manuais" not in dados_app:
    dados_app["concursos_manuais"] = {}
    salvar_dados(dados_app)

# --- INTERFACE DO APLICATIVO ---
st.title("⚽ Bolão da Família")

# Menu original restaurado exatamente como você definiu
menu = ["🏆 Ranking & Resultados", "🎲 Concursos",
        "💰 Financeiro", "⚙️ Organizador"]
escolha = st.sidebar.selectbox("Navegação", menu)

# Carrega os resultados e junta com os manuais do organizador
resultados_api = buscar_resultados_lotofacil()
concursos_oficiais = {**resultados_api, **
                      dados_app.get("concursos_manuais", {})}

if escolha == "🏆 Ranking & Resultados":
    st.subheader("🥇 Ranking Atual")
    df_excel = ler_excel_local()
    if df_excel is not None:
        st.dataframe(df_excel)
    else:
        st.warning(
            "O arquivo `bolao_atual.xlsx` ainda não foi encontrado na pasta do projeto. Use o Organizador para enviá-lo.")

elif escolha == "🎲 Concursos":
    st.subheader("📊 Sorteios Válidos Registrados")
    if concursos_oficiais:
        concursos_ordenados = sorted(concursos_oficiais.keys(
        ), key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
        for num in concursos_ordenados[:10]:
            info = concursos_oficiais[num]
            data_str = f" ({info.get('data', '')})" if info.get('data') else ""
            st.write(f"**Concurso {num}{data_str}**: `{info['dezenas']}`")
    else:
        st.info("Nenhum concurso carregado no momento. Utilize o Organizador para lançamento manual se necessário.")

elif escolha == "💰 Financeiro":
    st.subheader("💰 Controle Financeiro do Bolão")
    st.info("Informações financeiras e de pagamentos dos participantes.")
    df_excel = ler_excel_local()
    if df_excel is not None:
        # Exibe colunas relevantes se existirem na planilha
        st.dataframe(df_excel)
    else:
        st.warning("Nenhum dado financeiro carregado no Excel.")

elif escolha == "⚙️ Organizador":
    st.subheader("⚙️ Painel do Organizador")
    senha_digitada = st.text_input(
        "Digite a senha de administrador:", type="password")

    if senha_digitada == SENHA_ADMIN:
        st.success("Acesso autorizado!")
        st.divider()

        # 1. Restauração do Upload da Planilha
        st.markdown("### 📁 Atualizar Planilha do Bolão (Excel)")
        st.info("Faça o upload da sua planilha atualizada (`bolao_atual.xlsx`) para atualizar o app instantaneamente.")
        uploaded_file = st.file_uploader(
            "Escolha o arquivo Excel", type=["xlsx", "xls"])

        if uploaded_file is not None:
            with open(PLANILHA_EXCEL, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Planilha atualizada com sucesso! Recarregue a página.")

        st.divider()

        # 2. Lançamento Manual de Concurso
        st.markdown("### ✍️ Lançamento Manual de Concurso")
        st.info("Caso a API da Caixa demore para atualizar (como o concurso 3040), cadastre manualmente aqui para o ranking funcionar na hora.")

        with st.form("form_manual"):
            novo_concurso = st.text_input("Número do Concurso (ex: 3040)")
            data_concurso = st.text_input("Data do Sorteio (ex: 04/08/2026)")
            dezenas_str = st.text_input(
                "Dezenas sorteadas separadas por vírgula (ex: 01, 03, 05, ...)")

            botao_salvar = st.form_submit_button("Salvar Concurso Manualmente")

            if botao_salvar:
                if novo_concurso and dezenas_str:
                    lista_dezenas = [d.strip().zfill(2)
                                     for d in dezenas_str.split(",")]

                    dados_atuais = carregar_dados()
                    if "concursos_manuais" not in dados_atuais:
                        dados_atuais["concursos_manuais"] = {}

                    dados_atuais["concursos_manuais"][str(novo_concurso)] = {
                        "data": data_concurso,
                        "dezenas": lista_dezenas
                    }
                    salvar_dados(dados_atuais)
                    st.success(
                        f"Concurso {novo_concurso} salvo com sucesso! Atualize a página.")
                else:
                    st.error("Preencha o número do concurso e as dezenas.")

        st.divider()
        if st.button("🔄 Forçar Limpeza de Cache de Concursos"):
            st.cache_data.clear()
            st.success("Cache limpo! Recarregue a página.")

    elif senha_digitada != "":
        st.error("Senha incorreta.")
