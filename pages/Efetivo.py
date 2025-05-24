import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Efetivo – DLOG", page_icon="🪖", layout="wide")
st.title("🪖 Efetivo da Diretoria de Logística – PMAL")

# --- LINK DIRETO DO GITHUB ---
url = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/BASE_EFETIVO_DLOG.xlsx"

@st.cache_data
def carregar_dados():
    # Carrega a aba "Militares"
    df_mil = pd.read_excel(url, sheet_name="Militares")
    return df_mil

df = carregar_dados()

# FILTRO DE CATEGORIA (Oficial/Praça)
st.sidebar.header("Filtros")
categorias = df["categoria"].dropna().unique().tolist()
cat_sel = st.sidebar.multiselect("Categoria", categorias, default=categorias)
df = df[df["categoria"].isin(cat_sel)]

# FILTRO DE POSTO/GRADUAÇÃO
postos = df["posto_grad"].dropna().unique().tolist()
posto_sel = st.sidebar.multiselect("Posto/Graduação", postos, default=postos)
df = df[df["posto_grad"].isin(posto_sel)]

# --- KPIs ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Efetivo", len(df))
col2.metric("Oficiais", (df["categoria"]=="Oficial").sum())
col3.metric("Praças", (df["categoria"]=="Praça").sum())

# --- GRÁFICO DONUT ---
st.subheader("Distribuição por Categoria")
df_cnt = df["categoria"].value_counts().reset_index()
df_cnt.columns = ["Categoria", "Quantidade"]
fig = px.pie(df_cnt, values="Quantidade", names="Categoria", hole=0.4, title="Efetivo Oficial x Praça")
st.plotly_chart(fig, use_container_width=True)

# --- TABELA DETALHADA ---
st.subheader("Tabela Detalhada do Efetivo")
st.dataframe(df, use_container_width=True)

# --- BOTÃO DE DOWNLOAD ---
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Baixar tabela (CSV)",
    data=csv,
    file_name="Efetivo_DLOG.csv",
    mime="text/csv"
)

st.caption("© Diretoria de Logística – PMAL | Dashboard Integrado")
