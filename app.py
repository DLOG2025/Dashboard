import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Dashboard ISSP 🚓", layout="wide")
st.title("🚓 Dashboard ISSP - Frota e Consumo de Combustível")

# --- URLs do GitHub ---
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA_BASE = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Base.xlsx"
URL_FROTA_ENRICHED = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM_MUNICIPIOS = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"

# --- Carregar dados ---
@st.cache_data
def load_data():
    df_abastecimento = pd.read_excel(URL_ABAST)
    df_frota_base = pd.read_excel(URL_FROTA_BASE)
    df_frota_enriched = pd.read_excel(URL_FROTA_ENRICHED)
    df_opm_municipios = pd.read_excel(URL_OPM_MUNICIPIOS)
    return df_abastecimento, df_frota_base, df_frota_enriched, df_opm_municipios

df_abast, df_frota_base, df_frota_enriched, df_opm = load_data()

# --- Barra lateral com filtros ---
st.sidebar.header("🎛️ Filtros")
opcoes_unidade = df_abast['UNIDADE'].unique().tolist()
unidades = st.sidebar.multiselect("Unidade", opcoes_unidade, default=opcoes_unidade)

opcoes_comb = df_abast['COMBUSTIVEL_DOMINANTE'].unique().tolist()
combustiveis = st.sidebar.multiselect("Combustível", opcoes_comb, default=opcoes_comb)

frotas = df_frota_enriched['Frota'].unique().tolist()
filtro_frota = st.sidebar.multiselect("Tipo de Frota", frotas, default=frotas)

# Filtro por Ano (se existir campo)
if "ARQUIVO" in df_abast.columns:
    anos = sorted(list(set([str(x).split("_")[-1].replace(".xlsx", "") for x in df_abast['ARQUIVO']])))
    ano = st.sidebar.multiselect("Ano (Arquivo)", anos, default=anos)
    df_abast['ANO'] = df_abast['ARQUIVO'].astype(str).apply(lambda x: str(x).split("_")[-1].replace(".xlsx", "") if "_" in x else "N/D")
else:
    df_abast['ANO'] = "N/D"
    ano = ["N/D"]

# --- Aplicando Filtros ---
df_filtro = df_abast[
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis) &
    df_abast['ANO'].isin(ano)
].copy()

# Unindo informações de frota
df_filtro = df_filtro.merge(df_frota_enriched[['PLACA', 'Frota', 'PADRAO', 'MARCA', 'MODELO', 'CUSTO_PADRAO_MENSAL', 'CARACTERIZACAO', 'IDADE_FROTA']],
                            on="PLACA", how="left")
df_filtro = df_filtro[df_filtro['Frota'].isin(filtro_frota)]

# --- Painel de Indicadores ---
st.markdown("### 📊 Painel de Indicadores")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Abastecimentos", f"{df_filtro.shape[0]:,}")
col2.metric("Viaturas Únicas", df_filtro['PLACA'].nunique())
col3.metric("Total de Litros", f"{df_filtro['TOTAL_LITROS'].sum():,.0f} L")
col4.metric("Total Gasto (R$)", f"R$ {df_filtro['VALOR_TOTAL'].sum():,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
idade_media = np.round(df_filtro['IDADE_FROTA'].mean(), 1) if 'IDADE_FROTA' in df_filtro else "N/D"
col5.metric("Idade Média da Frota", idade_media)

st.divider()

# --- Gráficos principais ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Visão Geral", 
    "⛽ Consumo e Gasto", 
    "🚗 Ranking de Viaturas", 
    "🗺️ OPMs & Municípios"
])

with tab1:
    st.subheader("📌 Destaques Gerais")
    colA, colB = st.columns(2)
    consumo_unidade = df_filtro.groupby("UNIDADE")['TOTAL_LITROS'].sum().sort_values(ascending=False)
    colA.plotly_chart(
        px.bar(consumo_unidade, orientation="h", labels={"value": "Litros", "index": "Unidade"}, title="Litros por Unidade"),
        use_container_width=True
    )
    valor_unidade = df_filtro.groupby("UNIDADE")['VALOR_TOTAL'].sum().sort_values(ascending=False)
    colB.plotly_chart(
        px.bar(valor_unidade, orientation="h", labels={"value": "R$", "index": "Unidade"}, title="Gasto por Unidade"),
        use_container_width=True
    )
    st.markdown("> 💡 **Dica:** Clique nas barras para filtrar!")

with tab2:
    st.subheader("⛽ Distribuição de Combustível")
    colA, colB = st.columns([2, 1])
    combustiveis_graf = df_filtro['COMBUSTIVEL_DOMINANTE'].value_counts()
    colA.plotly_chart(
        px.pie(
            names=combustiveis_graf.index,
            values=combustiveis_graf.values,
            title="Proporção por Combustível"
        ),
        use_container_width=True
    )
    linha_tempo = df_filtro.groupby("ANO")[["TOTAL_LITROS", "VALOR_TOTAL"]].sum().reset_index()
    colB.plotly_chart(
        px.bar(linha_tempo, x="ANO", y="TOTAL_LITROS", title="Consumo por Ano"),
        use_container_width=True
    )
    st.caption("🕒 *Linha do tempo do consumo, para tendências de anos diferentes*")

with tab3:
    st.subheader("🏆 Ranking de Viaturas")
    top_litros = df_filtro.groupby('PLACA')['TOTAL_LITROS'].sum().sort_values(ascending=False).head(20)
    st.plotly_chart(
        px.bar(top_litros, labels={'value': 'Litros', 'index': 'PLACA'}, title='Top 20 Viaturas em Litros'),
        use_container_width=True
    )
    top_valor = df_filtro.groupby('PLACA')['VALOR_TOTAL'].sum().sort_values(ascending=False).head(20)
    st.plotly_chart(
        px.bar(top_valor, labels={'value': 'R$', 'index': 'PLACA'}, title='Top 20 Viaturas em Valor'),
        use_container_width=True
    )
    st.markdown("> 🏅 *Veja quais viaturas mais consomem e mais gastam!*")

with tab4:
    st.subheader("🗺️ OPMs e Municípios")
    municipios_por_opm = df_opm.groupby("UNIDADE")['MUNICÍPIO'].nunique().reset_index()
    fig = px.choropleth(
        municipios_por_opm,
        locations="UNIDADE",
        locationmode="geojson-id",
        color="MUNICÍPIO",
        title="Quantidade de Municípios por OPM"
    )
    st.dataframe(municipios_por_opm.rename(columns={'MUNICÍPIO':'Nº Municípios'}))
    st.markdown("> 🔎 *Tabela mostra quantos municípios estão sob cada OPM.*")

st.divider()

# --- Dashboard de Frotas ---
st.markdown("## 🚘 Frota: Distribuição e Envelhecimento")
frota_agrup = df_frota_enriched.groupby("Frota").agg(
    Total_Veiculos = ("PLACA", "count"),
    Idade_Media = ("IDADE_FROTA", "mean"),
    Custo_Mensal_Total = ("CUSTO_PADRAO_MENSAL", "sum")
).reset_index()
col1, col2, col3 = st.columns(3)
col1.metric("Veículos Locados", int(frota_agrup[frota_agrup["Frota"]=="LOCADO"]["Total_Veiculos"].values[0]))
col2.metric("Veículos Próprios", int(frota_agrup[frota_agrup["Frota"]=="PRÓPRIO"]["Total_Veiculos"].values[0]))
col3.metric("Custo Total Frota (R$/mês)", f'R$ {frota_agrup["Custo_Mensal_Total"].sum():,.2f}'.replace(",", "v").replace(".", ",").replace("v", "."))

st.plotly_chart(
    px.bar(frota_agrup, x="Frota", y="Total_Veiculos", color="Frota", title="Distribuição da Frota"),
    use_container_width=True
)
st.plotly_chart(
    px.box(df_frota_enriched, x="Frota", y="IDADE_FROTA", color="Frota", points="all", title="Envelhecimento da Frota"),
    use_container_width=True
)

st.caption("🚙 *Frota dividida por tipo, com custo e envelhecimento!*")

st.divider()

# --- Detalhamento dos Abastecimentos (Tabela Final) ---
st.markdown("### 📋 Detalhamento dos Abastecimentos (com filtros aplicados)")
st.dataframe(
    df_filtro[[
        "PLACA", "UNIDADE", "COMBUSTIVEL_DOMINANTE", "TOTAL_LITROS", "VALOR_TOTAL",
        "Frota", "PADRAO", "MARCA", "MODELO", "CUSTO_PADRAO_MENSAL", "CARACTERIZACAO", "IDADE_FROTA", "ANO"
    ]],
    use_container_width=True,
    height=450
)

st.markdown("> 📝 *Use os filtros laterais para refinar a tabela acima!*")

st.info("Qualquer sugestão de melhoria, clique no menu ☰ no canto superior direito e envie seu feedback para a equipe DLOG!")

