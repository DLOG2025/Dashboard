import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
from io import BytesIO

st.set_page_config(page_title="Efetivo – DLOG", page_icon="🪖", layout="wide")
st.title("🪖 Efetivo da Diretoria de Logística – PMAL")

# URLs das planilhas
url_efetivo = "https://github.com/DLOG2025/Dashboard/raw/main/BASE_EFETIVO_DLOG.xlsx"
url_funcoes = "https://github.com/DLOG2025/Dashboard/raw/main/FUNCOES_DE_PRACAS_COM_BGO.xlsx"
url_efetivo_geral = "https://github.com/DLOG2025/Dashboard/raw/main/EFETIVO_GERAL_DA_DLOG%20.xlsx"

@st.cache_data
def carregar_dados():
    df_efetivo = pd.read_excel(url_efetivo, sheet_name="Militares", dtype=str).fillna("")
    df_funcoes = pd.read_excel(url_funcoes, dtype=str).fillna("")
    df_efetivo_geral = pd.read_excel(url_efetivo_geral, dtype=str).fillna("")
    return df_efetivo, df_funcoes, df_efetivo_geral

df_efetivo, df_funcoes, df_efetivo_geral = carregar_dados()

# Definição das graduações
ordem_grad = ["CEL", "TEN CEL", "MAJ", "CAP", "1º TEN", "2º TEN", 
              "SUBTENENTE", "1º SARGENTO", "2º SARGENTO", "3º SARGENTO", "CB", "SD"]

# Ajuste e padronização das colunas
df_funcoes.columns = df_funcoes.columns.str.upper().str.strip()
df_efetivo_geral.columns = df_efetivo_geral.columns.str.upper().str.strip()

# Cruzamento para gráfico comparativo
previstas = df_funcoes["GRADUAÇÃO DA FUNÇÃO"].value_counts().reindex(ordem_grad, fill_value=0)
ocupadas = df_funcoes[df_funcoes["NOME DE GUERRA"] != ""]["GRADUAÇÃO DA FUNÇÃO"].value_counts().reindex(ordem_grad, fill_value=0)
abertas = previstas - ocupadas
real = df_efetivo_geral["P/G"].value_counts().reindex(ordem_grad, fill_value=0)

# KPIs superiores
col1, col2, col3, col4 = st.columns(4)
col1.metric("Efetivo previsto", previstas.sum())
col2.metric("Vagas ocupadas", ocupadas.sum())
col3.metric("Vagas abertas", abertas.sum())
col4.metric("Efetivo real atual", real.sum())

# Gráfico comparativo ajustado
st.subheader("📊 Comparativo de Vagas e Efetivo")
df_comparativo = pd.DataFrame({
    "Graduação": ordem_grad,
    "Vagas Previstas": previstas.values,
    "Vagas Ocupadas": ocupadas.values,
    "Vagas Abertas": abertas.values,
    "Efetivo Real": real.values
}).melt(id_vars="Graduação", var_name="Situação", value_name="Quantidade")

fig_comparativo = px.bar(df_comparativo, x="Graduação", y="Quantidade", color="Situação", barmode="group", text_auto=True)
st.plotly_chart(fig_comparativo, use_container_width=True)

# Donut - Status geral
st.subheader("🟠 Status Geral das Vagas Previstas")
status_df = pd.DataFrame({
    "Situação": ["Ocupadas", "Abertas"],
    "Quantidade": [ocupadas.sum(), abertas.sum()]
})
fig_status = px.pie(status_df, names="Situação", values="Quantidade", hole=0.5, color="Situação",
                    color_discrete_map={"Ocupadas": "#00CC96", "Abertas": "#EF553B"})
st.plotly_chart(fig_status, use_container_width=True)

# ✅ Classificados por setor (apenas praças em vaga superior)
st.subheader("✅ Classificados por Setor")
grad_order = {grad: idx for idx, grad in enumerate(ordem_grad)}

def get_status_ocupacao(row):
    pg = row["posto_grad"]
    pg_funcao = row["posto_grad_funcao"]
    if pd.isna(pg_funcao) or pg_funcao == "":
        return "SEM BGO"
    elif grad_order.get(pg_funcao, 99) < grad_order.get(pg, 99):
        return "CLASSIFICADO"
    elif grad_order.get(pg_funcao, 99) == grad_order.get(pg, 99):
        return "VAGA CORRETA"
    else:
        return ""
        
df_efetivo["status_ocupacao"] = df_efetivo.apply(get_status_ocupacao, axis=1)
]

if not classificados.empty:
    classificados = classificados[["setor_funcional", "posto_grad", "posto_grad_funcao", "nome_guerra", "matricula"]]
    classificados.columns = ["Setor", "Graduação Militar", "Graduação da Vaga", "Nome Guerra", "Matrícula"]
    st.dataframe(classificados, use_container_width=True)
    st.download_button("⬇️ Baixar classificados (CSV)", classificados.to_csv(index=False), "classificados.csv")
else:
    st.info("Não há praças ocupando vaga superior no momento.")

# 🟣 Vagas abertas por Setor/Função corrigido
st.subheader("🟣 Vagas Abertas por Setor")
abertas_df = df_funcoes[df_funcoes["NOME DE GUERRA"] == ""]

if not abertas_df.empty:
    abertas_setor = abertas_df.groupby(["FUNÇÃO", "GRADUAÇÃO DA FUNÇÃO"]).size().reset_index(name="Quantidade de Vagas Abertas")
    abertas_setor.columns = ["Função/Setor", "Graduação da vaga", "Quantidade de Vagas Abertas"]
    st.dataframe(abertas_setor, use_container_width=True)
    st.download_button("⬇️ Baixar vagas abertas (CSV)", abertas_setor.to_csv(index=False), "vagas_abertas.csv")
else:
    st.info("Não há vagas abertas no momento.")

# 🔍 Busca detalhada do efetivo
st.subheader("🔍 Busca Detalhada do Efetivo")
busca_nome = st.text_input("Buscar (nome, matrícula, setor):").upper()
status_filtro = st.multiselect("Filtrar por status", ["CLASSIFICADO", "VAGA CORRETA", "SEM BGO"], default=["CLASSIFICADO", "VAGA CORRETA", "SEM BGO"])

df_efetivo["status_ocupacao"] = np.where(df_efetivo["posto_grad_funcao"] == "", "SEM BGO",
                               np.where(df_efetivo["posto_grad"] == df_efetivo["posto_grad_funcao"], "VAGA CORRETA", "CLASSIFICADO"))
filtro = df_efetivo["status_ocupacao"].isin(status_filtro)

if busca_nome:
    filtro &= df_efetivo.apply(lambda row: busca_nome in row["nome"].upper() or busca_nome in row["matricula"].upper() or busca_nome in row["setor_funcional"].upper(), axis=1)

resultados = df_efetivo[filtro][["posto_grad", "nome", "nome_guerra", "categoria", "matricula", "setor_funcional", "posto_grad_funcao", "status_ocupacao"]]

gb = GridOptionsBuilder.from_dataframe(resultados)
gb.configure_pagination(paginationPageSize=30)
grid_options = gb.build()
AgGrid(resultados, gridOptions=grid_options, height=1000, theme="alpine")

csv_final = resultados.to_csv(index=False)
st.download_button("⬇️ Baixar resultados filtrados (CSV)", csv_final, "efetivo_filtrado.csv")

st.caption("© Diretoria de Logística – PMAL | Dashboard Integrado – Efetivo Premium")
