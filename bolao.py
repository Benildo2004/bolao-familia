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
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            return json.load(f)
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

# --- BUSCA DE RESULTADOS (COM DUPLA API + SUPORTE MANUAL) ---


@st.cache_data(ttl=3600)
def buscar_resultados_lotofacil():
    # API Primária (Loterias API)
    url_primaria = "https://loteriasapi.com/api/v2/lotofacil"
    try:
        response = requests.get(url_primaria, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            if isinstance(dados, list) and len(dados) > 0:
                concursos = {}
                for c in dados[:10]:  # Pega os últimos 10
                    num = str(c.get("conquarso") or c.get("concurso"))
                    dezenas = c.get("dezenas") or c.get("dezenasSorteadas")
                    data = c.get("data")
                    if num and dezenas:
                        concursos[num] = {"data": data, "dezenas": [
                            str(d).zfill(2) for d in dezenas]}
                if concursos:
                    return concursos
    except:
        pass

    # API Secundária (Alternativa)
    url_secundaria = "https://brasilapi.com.br/api/loterias/v1/lotofacil"
    try:
        response = requests.get(url_secundaria, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            num = str(dados.get("concurso"))
            dezenas = [str(d).zfill(2) for d in dados.get("dezenas", [])]
            data = dados.get("data")
            if num and dezenas:
                return {num: {"data": data, "dezenas": dezenas}}
    except:
        pass

    return {}


# Inicializa dados salvos no JSON se não existirem
dados_app = carregar_dados()
if "concursos_manuais" not in dados_app:
    dados_app["concursos_manuais"] = {}
    salvar_dados(dados_app)

# --- INTERFACE DO APLICATIVO ---
st.title("⚽ Bolão da Família")

menu = ["🏆 Ranking & Resultados", "👥 Participantes", "⚙️ Organizador"]
escolha = st.sidebar.selectbox("Navegação", menu)

# Carrega os resultados da API
resultados_api = buscar_resultados_lotofacil()

# Junta os resultados da API com os lançamentos manuais do organizador
concursos_oficiais = {**resultados_api, **dados_app["concursos_manuais"]}

if escolha == "🏆 Ranking & Resultados":
    st.subheader("📊 Sorteios Válidos Registrados")

    if concursos_oficiais:
        # Ordena do mais recente para o mais antigo
        concursos_ordenados = sorted(
            concursos_oficiais.keys(), key=lambda x: int(x), reverse=True)

        for num in concursos_ordenados[:5]:
            info = concursos_oficiais[num]
            data_str = f" ({info.get('data', '')})" if info.get('data') else ""
            st.write(f"**Concurso {num}{data_str}**: `{info['dezenas']}`")
    else:
        st.info("Nenhum concurso carregado no momento. Verifique a conexão ou utilize o Organizador para lançamento manual.")

    st.divider()
    st.subheader("🥇 Ranking Atual")

    # Lê a planilha Excel enviada
    df_excel = ler_excel_local()
    if df_excel is not None:
        st.write("Planilha carregada com sucesso do seu projeto!")
        st.dataframe(df_excel)
    else:
        st.warning(
            "O arquivo `bolao_atual.xlsx` ainda não foi encontrado na pasta do projeto.")

elif escolha == "👥 Participantes":
    st.subheader("👥 Lista de Participantes e Apostas")
    df_excel = ler_excel_local()
    if df_excel is not None:
        st.dataframe(df_excel)
    else:
        st.warning("Nenhum dado de participantes carregado no Excel.")

elif escolha == "⚙️ Organizador":
    st.subheader("⚙️ Painel do Organizador")
    senha_digitada = st.text_input(
        "Digite a senha de administrador:", type="password")

    if senha_digitada == SENHA_ADMIN:
        st.success("Acesso autorizado!")
        st.divider()

        st.markdown("### ✍️ Lançamento Manual de Concurso")
        st.info("Caso a API demore para atualizar, você pode cadastrar o concurso manualmente aqui. Ele terá prioridade e nunca será duplicado.")

        with st.form("form_manual"):
            novo_concurso = st.text_input("Número do Concurso (ex: 3040)")
            data_concurso = st.text_input("Data do Sorteio (ex: 04/08/2026)")
            # Campo para os 15 números da lotofácil ou os números do bolão
            dezenas_str = st.text_input(
                "Dezenas sorteadas separadas por vírgula (ex: 01, 03, 05, ...)")

            botao_salvar = st.form_submit_button("Salvar Concurso Manualmente")

            if botao_salvar:
                if novo_concurso and dezenas_str:
                    # Limpa e formata as dezenas digitadas
                    lista_dezenas = [d.strip().zfill(2)
                                     for d in dezenas_str.split(",")]

                    # Salva no JSON de manuais
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
