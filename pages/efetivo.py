import streamlit as st
import streamlit as st

st.set_page_config(page_title="Efetivo", page_icon="🪖", layout="wide")

# --- Botão HOME menor e estilizado ---
st.markdown("""
    <style>
    .home-btn {
        display: inline-block;
        width: 140px;
        height: 54px;
        margin: 10px 0 32px 0;
        background: #0A2342;
        color: #fff !important;
        font-size: 1.2rem;
        font-weight: bold;
        border: none;
        border-radius: 14px;
        text-align: center;
        line-height: 54px;
        text-decoration: none !important;
        box-shadow: 0 4px 16px 0 rgba(0,0,0,0.10);
        letter-spacing: 2px;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .home-btn:hover {
        background: #10336B;
        color: #f9dc5c !important;
        transform: scale(1.04);
        text-decoration: none !important;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<a href="/" class="home-btn" target="_self">HOME</a>', unsafe_allow_html=True)

# Agora começa o resto do seu dashboard:
st.title("DLOG PMAL – Efetivo")
# ...coloque aqui todos os seus gráficos, tabelas etc.

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

# URLs dos arquivos
url_oficiais = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OFICIAIS.xlsx"
url_pracas = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/PRA%C3%87AS.xlsx"
url_efetivo_geral = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/EFETIVO_GERAL_DA_DLOG%20.xlsx"

# Carregar os dados
@st.cache_data
def carregar_efetivo():
    df_oficiais = pd.read_excel(url_oficiais, dtype=str).fillna("")
    df_pracas = pd.read_excel(url_pracas, dtype=str).fillna("")
    df_efetivo_geral = pd.read_excel(url_efetivo_geral, dtype=str).fillna("")
    # Padroniza nomes das colunas para facilitar concatenação
    df_oficiais.columns = df_oficiais.columns.str.upper().str.strip()
    df_pracas.columns = df_pracas.columns.str.upper().str.strip()
    df_efetivo_geral.columns = df_efetivo_geral.columns.str.upper().str.strip()
    return df_oficiais, df_pracas, df_efetivo_geral

df_oficiais, df_pracas, df_efetivo_geral = carregar_efetivo()

# Unifica tudo numa tabela (todas as colunas possíveis)
df_busca = pd.concat([df_oficiais, df_pracas, df_efetivo_geral], ignore_index=True)
df_busca = df_busca.drop_duplicates(subset=["MAT"])  # Duplicados por matrícula removidos

# Adiciona coluna 'STATUS_OCUPACAO' se não existir (padrão SEM BGO)
if "STATUS_OCUPACAO" not in df_busca.columns:
    df_busca["STATUS_OCUPACAO"] = "SEM BGO"

st.subheader("🔍 Busca Detalhada do Efetivo (Todos os militares)")

# Filtros opcionais
busca = st.text_input("Buscar por nome, matrícula, nome de guerra ou setor:").upper()
status_list = ["CLASSIFICADO", "VAGA CORRETA", "SEM BGO"]
status_filtro = st.multiselect("Filtrar por status", status_list, default=status_list)

# Aplica filtros (se houver)
df_mostrar = df_busca.copy()
if busca:
    df_mostrar = df_mostrar[
        df_mostrar.apply(
            lambda row: busca in row.get("NOME", "").upper() or
                        busca in row.get("MAT", "").upper() or
                        busca in row.get("N GUERRA", "").upper() or
                        busca in row.get("LOTAÇÃO", "").upper() or
                        busca in row.get("SETOR", "").upper(), axis=1)
    ]

if "STATUS_OCUPACAO" in df_mostrar.columns:
    df_mostrar = df_mostrar[df_mostrar["STATUS_OCUPACAO"].isin(status_filtro)]

# Colunas a exibir (ajuste conforme suas colunas)
colunas_visiveis = [col for col in ["P/G", "NOME", "N GUERRA", "MAT", "CPF", "QUADRO", "LOTAÇÃO", "SETOR", "STATUS_OCUPACAO"] if col in df_mostrar.columns]
df_exibir = df_mostrar[colunas_visiveis]

# Exibição com AG-Grid (30 linhas/página)
gb = GridOptionsBuilder.from_dataframe(df_exibir)
gb.configure_pagination(paginationPageSize=30)
grid_options = gb.build()
AgGrid(df_exibir, gridOptions=grid_options, height=1000, theme="alpine")

st.download_button("⬇️ Baixar lista completa (CSV)", df_exibir.to_csv(index=False), "efetivo_busca_detalhada.csv")

st.caption("© Diretoria de Logística – PMAL | Busca Detalhada Efetivo")
