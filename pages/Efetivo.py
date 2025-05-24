import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from fpdf import FPDF

# --- LINK DA PLANILHA NO GITHUB ---
url = "https://github.com/DLOG2025/Dashboard/raw/main/MATRIZ_EFETIVO_DLOG_COMPLETA.xlsx"

st.set_page_config(page_title="Efetivo – DLOG", page_icon="🪖", layout="wide")
st.title("🪖 Efetivo da Diretoria de Logística – PMAL")

@st.cache_data
def carregar():
    df = pd.read_excel(url, sheet_name="Militares", dtype=str).fillna("")
    df["categoria"] = df["categoria"].str.upper()
    df["posto_grad"] = df["posto_grad"].str.upper()
    df["lotacao"] = df["lotacao"].str.upper()
    df["setor_funcional"] = df["setor_funcional"].str.upper()
    df["bgo_designacao"] = df["bgo_designacao"].str.upper()
    df["posto_grad_funcao"] = df["posto_grad_funcao"].str.upper()
    df["funcao_qo"] = df["funcao_qo"].str.upper()
    return df

df = carregar()

# --- STATUS DE OCUPAÇÃO (classificado etc) ---
def status_ocupacao(row):
    if not row["bgo_designacao"]:
        return "SEM BGO"
    elif row["categoria"] == "PRAÇA" and row["posto_grad"] != row["posto_grad_funcao"]:
        # Praça em vaga superior
        return "CLASSIFICADO"
    elif row["categoria"] == "PRAÇA" and row["posto_grad"] == row["posto_grad_funcao"]:
        return "VAGA CORRETA"
    elif row["categoria"] == "OFICIAL":
        return "VAGA CORRETA"
    return "SEM CLASSIFICAÇÃO"

df["status_ocupacao"] = df.apply(status_ocupacao, axis=1)

# --- SIDEBAR: FILTROS AVANÇADOS ---
st.sidebar.header("Filtros")
# Categoria
cats = df["categoria"].dropna().unique().tolist()
cat_sel = st.sidebar.multiselect("Categoria", cats, default=cats)
# Posto/Graduação
postos = sorted(df["posto_grad"].dropna().unique().tolist())
posto_sel = st.sidebar.multiselect("Posto/Graduação", postos, default=postos)
# Setor funcional
setores = sorted(df["setor_funcional"].dropna().unique())
setor_sel = st.sidebar.multiselect("Setor funcional", setores, default=setores)
# Filtros rápidos
st.sidebar.markdown("---")
filtro_classificado = st.sidebar.checkbox("Mostrar só PRAÇAS classificados", value=False)
filtro_s_bgo = st.sidebar.checkbox("Mostrar só PRAÇAS sem BGO", value=False)
filtro_lotacao_dlog = st.sidebar.checkbox("Somente lotação na DLOG", value=False)

# --- FILTRAGEM DINÂMICA ---
df_filtrado = df.copy()
df_filtrado = df_filtrado[
    df_filtrado["categoria"].isin([c.upper() for c in cat_sel]) &
    df_filtrado["posto_grad"].isin([p.upper() for p in posto_sel]) &
    df_filtrado["setor_funcional"].isin([s.upper() for s in setor_sel])
]
if filtro_classificado:
    df_filtrado = df_filtrado[(df_filtrado["categoria"] == "PRAÇA") & (df_filtrado["status_ocupacao"] == "CLASSIFICADO")]
if filtro_s_bgo:
    df_filtrado = df_filtrado[(df_filtrado["categoria"] == "PRAÇA") & (df_filtrado["bgo_designacao"] == "")]
if filtro_lotacao_dlog:
    df_filtrado = df_filtrado[df_filtrado["lotacao"].str.strip() == "DLOG"]

# --- KPIs DE TOPO ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Efetivo total", len(df_filtrado))
col2.metric("Oficiais", (df_filtrado["categoria"] == "OFICIAL").sum())
col3.metric("Praças", (df_filtrado["categoria"] == "PRAÇA").sum())
col4.metric("Classificados (praças)", ((df_filtrado["categoria"] == "PRAÇA") & (df_filtrado["status_ocupacao"] == "CLASSIFICADO")).sum())
col5.metric("Sem BGO (praças)", ((df_filtrado["categoria"] == "PRAÇA") & (df_filtrado["bgo_designacao"] == "")).sum())

# --- GRÁFICO DONUT: STATUS DE OCUPAÇÃO ---
st.subheader("Distribuição dos Status de Ocupação")
status_counts = df_filtrado["status_ocupacao"].value_counts().reset_index()
status_counts.columns = ["Status", "Quantidade"]
fig = px.pie(
    status_counts, values="Quantidade", names="Status", hole=0.45, color_discrete_sequence=px.colors.sequential.Blues
)
st.plotly_chart(fig, use_container_width=True)

# --- GRÁFICO DE BARRAS POR POSTO/GRADUAÇÃO ---
st.subheader("Efetivo por Posto/Graduação")
bar_pg = df_filtrado.groupby("posto_grad")["nome"].count().reset_index()
bar_pg.columns = ["Posto/Graduação", "Quantidade"]
fig2 = px.bar(
    bar_pg, x="Posto/Graduação", y="Quantidade", text_auto=True, color="Quantidade",
    color_continuous_scale="Blues"
)
st.plotly_chart(fig2, use_container_width=True)

# --- HEATMAP POR SETOR x GRADUAÇÃO ---
st.subheader("Distribuição por Setor Funcional x Graduação")
heat = pd.pivot_table(
    df_filtrado, values="nome", index="setor_funcional", columns="posto_grad", aggfunc="count", fill_value=0
)
fig3 = px.imshow(heat, text_auto=True, aspect="auto", color_continuous_scale="Blues", title="Contagem")
st.plotly_chart(fig3, use_container_width=True)

# --- KPIs POR SETOR E QUADRO ---
st.markdown("##### Resumo por setor funcional")
st.dataframe(df_filtrado.groupby("setor_funcional")["nome"].count().reset_index().rename(columns={"nome": "Qtd"}), use_container_width=True)

st.markdown("##### Resumo por quadro")
if "quadro" in df_filtrado.columns:
    st.dataframe(df_filtrado.groupby("quadro")["nome"].count().reset_index().rename(columns={"nome": "Qtd"}), use_container_width=True)

# --- TABELA DETALHADA DINÂMICA (AG-GRID) ---
st.subheader("Tabela Detalhada do Efetivo")

# Reorganizar colunas: posto_grad antes do nome, remover hierarquia_nivel se existir
cols_tabela = ["posto_grad", "nome", "nome_guerra", "categoria", "matricula", "quadro",
               "setor_funcional", "lotacao", "bgo_designacao", "posto_grad_funcao", "funcao_qo", "status_ocupacao"]
cols_tabela = [c for c in cols_tabela if c in df_filtrado.columns]
df_show = df_filtrado[cols_tabela].copy()

# Indica “classificado” como destaque positivo
def classificado_cell(row):
    if row["status_ocupacao"] == "CLASSIFICADO":
        return "✅ CLASSIFICADO"
    elif row["status_ocupacao"] == "SEM BGO":
        return "⚠️ SEM BGO"
    elif row["status_ocupacao"] == "VAGA CORRETA":
        return "VAGA CORRETA"
    else:
        return row["status_ocupacao"]

df_show["status_ocupacao"] = df_show.apply(classificado_cell, axis=1)

# Botão exportar CSV
csv = df_show.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar tabela filtrada (CSV)", data=csv, file_name="Efetivo_DLOG.csv", mime="text/csv")

# Botão exportar XLSX
excel = df_show.to_excel(index=False, engine="openpyxl")
st.download_button("⬇️ Baixar tabela filtrada (XLSX)", data=excel, file_name="Efetivo_DLOG.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Tabela interativa Ag-Grid
gb = GridOptionsBuilder.from_dataframe(df_show)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_default_column(editable=False, groupable=True, resizable=True)
gb.configure_side_bar()
gb.configure_selection('multiple', use_checkbox=True)
gridOptions = gb.build()
AgGrid(df_show, gridOptions=gridOptions, enable_enterprise_modules=True, theme='alpine', height=400)

# --- AÇÕES EXTRAS: Exportar PDF ---
def export_pdf(df_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Relatório Efetivo DLOG", ln=1, align="C")
    # Cabeçalhos
    pdf.set_font("Arial", style='B', size=9)
    headers = df_pdf.columns.tolist()
    for h in headers:
        pdf.cell(23, 8, h, border=1)
    pdf.ln()
    pdf.set_font("Arial", size=8)
    # Dados
    for _, row in df_pdf.iterrows():
        for v in row:
            pdf.cell(23, 8, str(v), border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

if st.button("📄 Baixar relatório em PDF"):
    st.download_button(
        "Clique aqui para baixar o PDF",
        export_pdf(df_show),
        file_name="Relatorio_Efetivo_DLOG.pdf",
        mime="application/pdf"
    )

st.caption("© Diretoria de Logística – PMAL | Dashboard Integrado – Efetivo")
