import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuração da página
st.set_page_config(page_title="DASHBOARD_VIATURAS_DLOG", layout="wide")
st.title("🚓 DASHBOARD_VIATURAS_DLOG - DLOG")

# URLs dos arquivos no GitHub
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA_BASE = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Base.xlsx"
URL_FROTA_ENRICHED = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM_MUNICIPIOS = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"

# Função para carregar e armazenar em cache
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota_base = pd.read_excel(URL_FROTA_BASE)
    df_frota_enriched = pd.read_excel(URL_FROTA_ENRICHED)
    df_opm = pd.read_excel(URL_OPM_MUNICIPIOS)
    return df_abast, df_frota_base, df_frota_enriched, df_opm

@st.cache_data
# Carrega os dados uma única vez
def get_data():
    return load_data()

df_abast, df_frota_base, df_frota_enriched, df_opm = get_data()

# Padronizar placas (remover traços/espaços e colocar maiúsculas)
def padroniza_placa(x):
    return str(x).upper().replace('-', '').replace(' ', '')
for df in (df_abast, df_frota_base, df_frota_enriched):
    df['PLACA'] = df['PLACA'].apply(padroniza_placa)

# Sidebar: filtros básicos
st.sidebar.header("🎯 Filtros")
unidades = st.sidebar.multiselect(
    "Selecione Unidades:", df_abast['UNIDADE'].unique(), default=df_abast['UNIDADE'].unique()
)
combustiveis = st.sidebar.multiselect(
    "Selecione Combustíveis:", df_abast['COMBUSTIVEL_DOMINANTE'].unique(),
    default=df_abast['COMBUSTIVEL_DOMINANTE'].unique()
)

# Aplicar filtros ao df_abast
df_abast_f = df_abast[
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
].copy()

# Mesclar com dados de frota enriquecida (para ter Frota, PADRAO, CARACTERIZACAO)
df = df_abast_f.merge(
    df_frota_enriched[['PLACA', 'Frota', 'PADRAO', 'CARACTERIZACAO']],
    on='PLACA', how='left'
)
# Preencher valores faltantes
df['Frota'] = df['Frota'].fillna('NÃO ENCONTRADO')
df['PADRAO'] = df['PADRAO'].fillna('N/D')
df['CARACTERIZACAO'] = df['CARACTERIZACAO'].fillna('N/D')

# Criar abas
tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Visão Geral", "🚘 Distribuição de Frota", "📍 OPMs & Municípios", "📋 Detalhamento"
])

with tab1:
    st.subheader("✨ Indicadores Principais")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 Registros", f"{len(df):,}")
    c2.metric("🚔 Viaturas Únicas", df['PLACA'].nunique())
    c3.metric("⛽ Total Litros", f"{df['TOTAL_LITROS'].sum():,.0f} L")
    c4.metric(
        "💰 Gasto Total (R$)",
        f"R$ {df['VALOR_TOTAL'].sum():,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    )
    st.divider()
    st.plotly_chart(
        px.bar(
            df.groupby('UNIDADE')['TOTAL_LITROS']
              .sum()
              .reset_index()
              .sort_values('TOTAL_LITROS', ascending=False),
            x='TOTAL_LITROS', y='UNIDADE', orientation='h',
            labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'},
            title='Litros por Unidade'
        ),
        use_container_width=True
    )

with tab2:
    st.subheader("🚘 Distribuição de Frota por OPM e Tipo")
    # Distribuição por OPM e tipo de frota
    dist = df_frota_enriched.groupby(['OPM', 'Frota']).size().reset_index(name='Contagem')
    fig = px.bar(
        dist, x='OPM', y='Contagem', color='Frota',
        title='Veículos por OPM e Tipo de Frota',
        labels={'Contagem':'# Veículos','OPM':'Batalhão'}
    )
    st.plotly_chart(fig, use_container_width=True)
    st.divider()
    st.subheader("📊 Caracterização da Frota por OPM")
    # Caracterização empilhada
    char = df_frota_enriched.groupby(['OPM', 'CARACTERIZACAO']).size().reset_index(name='Contagem')
    fig2 = px.bar(
        char, x='OPM', y='Contagem', color='CARACTERIZACAO', barmode='stack',
        title='Caracterização da Frota por OPM',
        labels={'Contagem':'# Veículos','OPM':'Batalhão'}
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("📍 OPMs e Municípios do Interior")
    interior = df_opm[df_opm['TIPO_LOCAL'].str.lower() == 'município']
    interior_count = interior.groupby('UNIDADE')['MUNICÍPIO'].nunique().reset_index(name='Nº Municípios')
    st.dataframe(interior_count, use_container_width=True)
    st.divider()
    st.subheader("🏙️ Bairros de Maceió por OPM")
    bairros = df_opm[df_opm['TIPO_LOCAL'].str.lower() == 'bairro']
    bairros_count = bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Nº Bairros')
    st.dataframe(bairros_count, use_container_width=True)

with tab4:
    st.subheader("📋 Detalhamento de Abastecimentos")
    cols = [
        'PLACA', 'UNIDADE', 'COMBUSTIVEL_DOMINANTE', 'TOTAL_LITROS', 'VALOR_TOTAL',
        'Frota', 'PADRAO', 'CARACTERIZACAO'
    ]
    st.dataframe(df[cols], use_container_width=True, height=450)

st.info("🔧 Use os filtros laterais para ajustar a visualização conforme seu interesse!")
