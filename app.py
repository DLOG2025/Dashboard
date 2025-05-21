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

@st.cache_data
# Função para carregar dados uma única vez
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota_base = pd.read_excel(URL_FROTA_BASE)
    df_frota_enriched = pd.read_excel(URL_FROTA_ENRICHED)
    df_opm = pd.read_excel(URL_OPM_MUNICIPIOS)
    return df_abast, df_frota_base, df_frota_enriched, df_opm

df_abast, df_frota_base, df_frota_enriched, df_opm = load_data()

# Padronizar PLACA
for df in (df_abast, df_frota_base, df_frota_enriched):
    df['PLACA'] = df['PLACA'].astype(str).str.upper().str.replace('-', '').str.replace(' ', '')

# Sidebar: filtros básicos
st.sidebar.header("🎯 Filtros")
unidades = st.sidebar.multiselect(
    "Selecione Unidades:", df_abast['UNIDADE'].unique(),
    default=df_abast['UNIDADE'].unique()
)
combustiveis = st.sidebar.multiselect(
    "Selecione Combustíveis:", df_abast['COMBUSTIVEL_DOMINANTE'].unique(),
    default=df_abast['COMBUSTIVEL_DOMINANTE'].unique()
)

# Aplicar filtros ao df_abast
mask = (
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
)
df_abast_f = df_abast[mask].copy()

# Merge com dados de frota enriquecida
cols_merge = ['PLACA', 'Frota', 'PADRAO', 'CARACTERIZACAO', 'CUSTO_PADRAO_MENSAL']
df = df_abast_f.merge(
    df_frota_enriched[cols_merge],
    on='PLACA', how='left'
)
# Preenchimento de valores nulos
df['Frota'] = df['Frota'].fillna('NÃO ENCONTRADO')
df['PADRAO'] = df['PADRAO'].fillna('N/D')
df['CARACTERIZACAO'] = df['CARACTERIZACAO'].fillna('N/D')
df['CUSTO_PADRAO_MENSAL'] = df['CUSTO_PADRAO_MENSAL'].fillna(0)

# Calcular custo total do veículo (combustível + locação)
df['CUSTO_TOTAL_VEICULO'] = df['VALOR_TOTAL'] + df['CUSTO_PADRAO_MENSAL']

# Número de OPMs únicos por viatura
df['NUM_OPMS'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

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
    fig1 = px.bar(
        df.groupby('UNIDADE')['TOTAL_LITROS']
          .sum()
          .reset_index()
          .sort_values('TOTAL_LITROS', ascending=False),
        x='TOTAL_LITROS', y='UNIDADE', orientation='h',
        labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'},
        title='Litros por Unidade'
    )
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    st.subheader("🚘 Distribuição de Frota por OPM e Tipo")
    dist = (
        df_frota_enriched.groupby(['OPM', 'Frota'])
                          .size()
                          .reset_index(name='Contagem')
    )
    fig2 = px.treemap(
        dist, path=['OPM', 'Frota'], values='Contagem',
        title='Distribuição da Frota por OPM e Tipo'
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.divider()
    st.subheader("📊 Caracterização da Frota por OPM")
    char = (
        df_frota_enriched.groupby(['OPM', 'CARACTERIZACAO'])
                          .size()
                          .reset_index(name='Contagem')
    )
    fig3 = px.bar(
        char, x='OPM', y='Contagem', color='CARACTERIZACAO', barmode='group',
        title='Caracterização da Frota por OPM'
    )
    st.plotly_chart(fig3, use_container_width=True)

with tab3:
    st.subheader("📍 OPMs & Municípios")
    interior = df_opm[
        (df_opm['TIPO_LOCAL'].str.lower() == 'município') &
        (df_opm['MUNICÍPIO'] != 'Maceió')
    ]
    interior_count = (
        interior.groupby('UNIDADE')['MUNICÍPIO']
                .nunique()
                .reset_index(name='Municípios')
    )
    bairros = df_opm[
        (df_opm['TIPO_LOCAL'].str.lower() == 'bairro') &
        (df_opm['MUNICÍPIO_REFERÊNCIA'] == 'Maceió')
    ]
    bairros_count = (
        bairros.groupby('UNIDADE')['LOCAL']
               .nunique()
               .reset_index(name='Bairros')
    )
    vehicles = (
        df_frota_enriched.groupby('OPM')['PLACA']
                           .nunique()
                           .reset_index(name='Viaturas')
    )
    opm_summary = (
        vehicles
        .merge(interior_count, on='UNIDADE', how='left')
        .merge(bairros_count, on='UNIDADE', how='left')
    )
    opm_summary[['Municípios','Bairros']] = (
        opm_summary[['Municípios','Bairros']]
        .fillna(0)
        .astype(int)
    )
    opm_summary['V/Município'] = (
        (opm_summary['Viaturas'] / opm_summary['Municípios'])
        .round(2)
        .replace(np.inf, 0)
    )
    opm_summary['V/Bairro'] = (
        (opm_summary['Viaturas'] / opm_summary['Bairros'])
        .round(2)
        .replace(np.inf, 0)
    )
    st.dataframe(
        opm_summary.rename(columns={'UNIDADE':'OPM'}),
        use_container_width=True
    )

with tab4:
    st.subheader("🏅 Ranking e Detalhamento de Viaturas")
    # Cálculo de ranking total e top 20
    ranking = (
        df.groupby('PLACA')['TOTAL_LITROS']
          .sum()
          .sort_values(ascending=False)
          .reset_index(name='Litros')
    )
    top20 = ranking.head(20)

    # Exibir ranking completo
    st.subheader("📃 Ranking Completo de Viaturas por Consumo")
    st.dataframe(ranking, use_container_width=True)

    st.divider()
    # Exibir top 20
    st.subheader("🔝 Top 20 Viaturas que Mais Consumiram")
    st.dataframe(top20, use_container_width=True)

    st.divider()
    # Viaturas múltiplas OPMs
    st.subheader("🚨 Viaturas Abastecidas em Múltiplas OPMs")
    multi = (
        df.groupby('PLACA')['UNIDADE']
          .nunique()
          .reset_index(name='OPMs Únicas')
    )
    multi = multi[multi['OPMs Únicas'] > 1]
    if not multi.empty:
        st.dataframe(multi, use_container_width=True)
    else:
        st.markdown("Nenhuma viatura abasteceu em mais de uma OPM.")

    st.divider()
    # Tabela detalhada
    st.subheader("📋 Detalhamento de Abastecimentos")
    display_cols = [
        'PLACA', 'UNIDADE', 'Combustível', 'Litros', 'Valor R$',
        'Custo Locação R$', 'Custo Total R$', 'Frota', 'Padrão',
        'Caracterização', 'OPMs Únicas'
    ]
    df_display = df.rename(columns={
        'COMBUSTIVEL_DOMINANTE':'Combustível',
        'TOTAL_LITROS':'Litros',
        'VALOR_TOTAL':'Valor R$',
        'CUSTO_PADRAO_MENSAL':'Custo Locação R$',
        'CUSTO_TOTAL_VEICULO':'Custo Total R$',
        'NUM_OPMS':'OPMs Únicas',
        'PADRAO':'Padrão',
        'CARACTERIZACAO':'Caracterização'
    })[display_cols]
    st.dataframe(df_display, use_container_width=True, height=450)

st.info("🔧 Use os filtros laterais para ajustar a visualização.")
