import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
from fpdf import FPDF
from io import BytesIO

# --- LINKS DAS PLANILHAS NO GITHUB ---
url_efetivo = "https://github.com/DLOG2025/Dashboard/raw/main/BASE_EFETIVO_DLOG.xlsx"
url_funcoes = "https://github.com/DLOG2025/Dashboard/raw/main/FUNCOES_DE_PRACAS_COM_BGO.xlsx"

st.set_page_config(page_title="Efetivo – DLOG", page_icon="🪖", layout="wide")
st.title("🪖 Efetivo da Diretoria de Logística – PMAL")

# --- FUNÇÃO PARA CARREGAR PLANILHAS ---
@st.cache_data
def carregar_dados():
    df_efetivo = pd.read_excel(url_efetivo, sheet_name="Militares", dtype=str).fillna("")
    df_funcoes = pd.read_excel(url_funcoes, dtype=str).fillna("")
    return df_efetivo, df_funcoes

df_efetivo, df_funcoes = carregar_dados()

# --- PADRONIZAÇÃO E CHAVES ---
ordem_grad = [
    "CEL", "TEN CEL", "MAJ", "CAP", "1º TEN", "2º TEN",
    "SUBTENENTE", "1º SARGENTO", "2º SARGENTO", "3º SARGENTO", "CB", "SD"
]
df_efetivo = df_efetivo.applymap(lambda x: x.upper().strip() if isinstance(x, str) else x)
df_funcoes = df_funcoes.applymap(lambda x: x.upper().strip() if isinstance(x, str) else x)

col_grad = "GRADUAÇÃO DA FUNÇÃO" if "GRADUAÇÃO DA FUNÇÃO" in df_funcoes.columns else "GRADUAÇÃO"
col_setor = "FUNÇÃO"
col_nome = "NOME DE GUERRA"
col_bgo = "BGO"
col_vagas = "QUANTIDADE DE VAGAS POR GRADUAÇÃO" if "QUANTIDADE DE VAGAS POR GRADUAÇÃO" in df_funcoes.columns else "QTDE VAGAS POR GRADUAÇÃO"

# --- CÁLCULO DE VAGAS E OCUPAÇÃO ---
df_funcoes["OCUPADA"] = df_funcoes[col_nome] != ""
df_funcoes["ABERTA"] = df_funcoes[col_nome] == ""

# Calcula vagas por graduação/setor
kpi_qtd_vagas = df_funcoes.groupby(col_grad).size().reindex(ordem_grad, fill_value=0)
kpi_qtd_ocupadas = df_funcoes[df_funcoes["OCUPADA"]].groupby(col_grad).size().reindex(ordem_grad, fill_value=0)
kpi_qtd_abertas = df_funcoes[df_funcoes["ABERTA"]].groupby(col_grad).size().reindex(ordem_grad, fill_value=0)
total_prevista = len(df_funcoes)
total_ocupada = df_funcoes["OCUPADA"].sum()
total_aberta = df_funcoes["ABERTA"].sum()

# --- CRUZAMENTO: EFETIVO REAL × VAGAS PREVISTAS/OCUPADAS ---
efetivo_real = df_efetivo.groupby("posto_grad").size().reindex(ordem_grad, fill_value=0)
# Corrige CLASSIFICADO: só praças em função de graduação superior
def superior(grad_praça, grad_funcao):
    try:
        return ordem_grad.index(grad_funcao) < ordem_grad.index(grad_praça)
    except:
        return False

df_efetivo["CLASSIFICADO"] = (
    (df_efetivo["categoria"] == "PRAÇA") &
    (df_efetivo["posto_grad_funcao"] != "") &
    df_efetivo.apply(lambda row: superior(row["posto_grad"], row["posto_grad_funcao"]), axis=1)
)

# --- KPIs SUPERIORES ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Efetivo previsto", total_prevista)
col2.metric("Ocupadas", int(total_ocupada))
col3.metric("Abertas", int(total_aberta))
col4.metric("Efetivo real (todos)", int(len(df_efetivo)))
col5.metric("Classificados (apenas praças acima da graduação)", int(df_efetivo["CLASSIFICADO"].sum()))

# --- GRÁFICO DE BARRAS: PREVISTO × OCUPADO × ABERTO × REAL ---
st.subheader("📊 Comparativo de Vagas e Efetivo por Graduação (CEL ao SD)")
plot_df = pd.DataFrame({
    "Vagas Previstas": kpi_qtd_vagas,
    "Vagas Ocupadas": kpi_qtd_ocupadas,
    "Vagas Abertas": kpi_qtd_abertas,
    "Efetivo Real": efetivo_real,
}).fillna(0).astype(int)
fig = px.bar(
    plot_df,
    barmode="group",
    x=plot_df.index,
    y=["Vagas Previstas", "Vagas Ocupadas", "Vagas Abertas", "Efetivo Real"],
    color_discrete_map={
        "Vagas Previstas": "#636EFA", "Vagas Ocupadas": "#00CC96",
        "Vagas Abertas": "#EF553B", "Efetivo Real": "#AB63FA"
    },
    title="Efetivo Real x Previsto x Ocupado x Aberto (por Graduação)",
    text_auto=True
)
st.plotly_chart(fig, use_container_width=True)

# --- DONUT: STATUS DE OCUPAÇÃO DE VAGAS ---
st.subheader("🟠 Status Geral das Vagas Previstas")
donut_df = pd.DataFrame({
    "Status": ["OCUPADAS", "ABERTAS"],
    "Quantidade": [int(total_ocupada), int(total_aberta)]
})
fig2 = px.pie(donut_df, names="Status", values="Quantidade", hole=0.5, color="Status",
              color_discrete_map={"OCUPADAS": "#00CC96", "ABERTAS": "#EF553B"})
st.plotly_chart(fig2, use_container_width=True)

# --- TABELA OU GRÁFICO MELHORADO: VAGAS POR FUNÇÃO X GRADUAÇÃO ---
st.subheader("🔵 Vagas Previstas por Função x Graduação (apenas onde há vagas)")
pivot = pd.pivot_table(
    df_funcoes, values="OCUPADA", index=col_setor, columns=col_grad,
    aggfunc="count", fill_value=0
).reindex(columns=ordem_grad, fill_value=0)
pivot = pivot.loc[(pivot.sum(axis=1) > 0)]  # Exibe só funções que possuem vagas

# Exibe como tabela dinâmica (com rolagem)
st.dataframe(pivot, use_container_width=True, height=450)

# Também pode exibir gráfico de barras agrupadas (se preferir)
# fig3 = px.bar(pivot.reset_index().melt(id_vars=col_setor, var_name='Graduação', value_name='Vagas'),
#               x=col_setor, y='Vagas', color='Graduação', barmode='group')
# st.plotly_chart(fig3, use_container_width=True)

# --- CLASSIFICADOS POR SETOR ---
st.subheader("✅ Classificados por Setor (Praças ocupando vaga superior)")
classificados = df_efetivo[df_efetivo["CLASSIFICADO"]]
if not classificados.empty:
    tab_class = classificados.groupby(["setor_funcional", "nome", "posto_grad", "posto_grad_funcao"])[["categoria", "matricula"]].first().reset_index()
    tab_class = tab_class.rename(columns={"setor_funcional": "Setor", "nome": "Nome", "posto_grad": "Graduação", "posto_grad_funcao": "Vaga Ocupada", "matricula": "Matrícula", "categoria": "Categoria"})
    st.dataframe(tab_class, use_container_width=True)
    csv_class = tab_class.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar lista de Classificados (CSV)", data=csv_class, file_name="classificados_por_setor.csv", mime="text/csv")
else:
    st.info("Nenhum praça classificado em vaga superior encontrado.")

# --- VAGAS ABERTAS POR SETOR/FUNÇÃO ---
st.subheader("🟣 Vagas Abertas por Setor/Função")
abertas = df_funcoes[df_funcoes["ABERTA"]]
if not abertas.empty:
    tab_abertas = abertas.groupby([col_setor, col_grad]).size().reset_index(name="Quantidade de Vagas Abertas")
    tab_abertas = tab_abertas.rename(columns={col_grad: "Graduação da vaga", col_setor: "Função/Sector"})
    st.dataframe(tab_abertas, use_container_width=True)
    csv_abertas = tab_abertas.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar vagas abertas (CSV)", data=csv_abertas, file_name="vagas_abertas.csv", mime="text/csv")
else:
    st.info("Não há vagas abertas no momento.")

# --- BUSCA DINÂMICA E TABELA INTERATIVA (AG-GRID) ---
st.subheader("🔍 Busca Detalhada e Tabela Dinâmica do Efetivo")
col_busca1, col_busca2 = st.columns([2, 3])
busca_nome = col_busca1.text_input("Buscar por nome, matrícula ou setor:", "")
status_sel = col_busca2.multiselect("Filtrar por status:", ["CLASSIFICADO", "VAGA CORRETA", "SEM BGO", ""], default=["CLASSIFICADO", "VAGA CORRETA", "SEM BGO", ""])
df_efetivo["status_ocupacao"] = np.where(df_efetivo["CLASSIFICADO"], "CLASSIFICADO",
                              np.where(df_efetivo["bgo_designacao"] == "", "SEM BGO",
                              np.where(df_efetivo["posto_grad"] == df_efetivo["posto_grad_funcao"], "VAGA CORRETA", "")))
filt = df_efetivo["status_ocupacao"].isin(status_sel)
if busca_nome:
    busca = busca_nome.upper()
    filt &= df_efetivo.apply(lambda row: busca in row["nome"] or busca in row["matricula"] or busca in row["setor_funcional"], axis=1)
tabela_final = df_efetivo[filt].copy()
cols_show = ["posto_grad", "nome", "nome_guerra", "categoria", "matricula", "quadro", "setor_funcional",
             "lotacao", "bgo_designacao", "posto_grad_funcao", "funcao_qo", "status_ocupacao"]
cols_show = [c for c in cols_show if c in tabela_final.columns]
tabela_final = tabela_final[cols_show]

# AgGrid visual
gb = GridOptionsBuilder.from_dataframe(tabela_final)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=30)
gb.configure_default_column(editable=False, groupable=True, resizable=True)
gb.configure_side_bar()
gb.configure_selection('multiple', use_checkbox=True)
gridOptions = gb.build()
AgGrid(tabela_final, gridOptions=gridOptions, enable_enterprise_modules=True, theme='alpine', height=1000)

csv_final = tabela_final.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Baixar tabela filtrada (CSV)", data=csv_final, file_name="Efetivo_DLOG.csv", mime="text/csv")
excel_buf = BytesIO()
tabela_final.to_excel(excel_buf, index=False, engine="openpyxl")
st.download_button("⬇️ Baixar tabela filtrada (XLSX)", data=excel_buf.getvalue(), file_name="Efetivo_DLOG.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def export_pdf(df_pdf):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Relatório Efetivo DLOG", ln=1, align="C")
    pdf.set_font("Arial", style='B', size=9)
    headers = df_pdf.columns.tolist()
    for h in headers:
        pdf.cell(23, 8, h[:12], border=1)
    pdf.ln()
    pdf.set_font("Arial", size=8)
    for _, row in df_pdf.iterrows():
        for v in row:
            pdf.cell(23, 8, str(v)[:12], border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

if st.button("📄 Baixar relatório em PDF"):
    st.download_button(
        "Clique aqui para baixar o PDF",
        export_pdf(tabela_final),
        file_name="Relatorio_Efetivo_DLOG.pdf",
        mime="application/pdf"
    )

st.caption("© Diretoria de Logística – PMAL | Dashboard Integrado – Efetivo Premium")
