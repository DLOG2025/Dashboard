import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Efetivo – DLOG", page_icon="🪖", layout="wide")
st.title("🪖 Efetivo da Diretoria de Logística")

# 1) Upload obrigatório
xlsx = st.file_uploader("🔄 Faça upload da BASE_EFETIVO_DLOG_v2.xlsx", type="xlsx")
if not xlsx:
    st.info("Envie a planilha para continuar.")
    st.stop()

# 2) Ler abas
dfs = pd.read_excel(xlsx, sheet_name=None)
df = dfs["Militares"]

# 3) Filtros simples
cat_opts = st.multiselect("Categoria", df["categoria"].unique(), default=list(df["categoria"].unique()))
df = df[df["categoria"].isin(cat_opts)]

# 4) KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Total", len(df))
col2.metric("Oficiais", (df["categoria"]=="Oficial").sum())
col3.metric("Praças",  (df["categoria"]=="Praça").sum())

# 5) Donut
cnt = df["categoria"].value_counts().reset_index()
cnt.columns = ["categoria","quant"]
st.plotly_chart(px.pie(cnt, names="categoria", values="quant", hole=.45), use_container_width=True)

# 6) Tabela
st.dataframe(df, use_container_width=True)
