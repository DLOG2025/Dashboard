import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuração da página
st.set_page_config(page_title="DASHBOARD_VIATURAS_DLOG", layout="wide")
st.title("🚓 DASHBOARD_VIATURAS_DLOG - DLOG")

# URLs dos arquivos no GitHub
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA_ENRICHED = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM_MUNICIPIOS = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"

@st.cache_data
# Carrega dados apenas uma vez
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota = pd.read_excel(URL_FROTA_ENRICHED)
    df_opm = pd.read_excel(URL_OPM_MUNICIPIOS)
    return df_abast, df_frota, df_opm

# Carregamento
df_abast, df_frota, df_opm = load_data()

# Padroniza PLACA em todos os dataframes
for df in (df_abast, df_frota):
    df['PLACA'] = df['PLACA'].astype(str).str.upper().str.replace('-', '').str.replace(' ', '')

# Sidebar de filtros
st.sidebar.header("🎯 Filtros")
unidades = st.sidebar.multiselect(
    "Selecione Unidades:", df_abast['UNIDADE'].unique(), default=df_abast['UNIDADE'].unique()
)
combustiveis = st.sidebar.multiselect(
    "Selecione Combustíveis:", df_abast['COMBUSTIVEL_DOMINANTE'].unique(),
    default=df_abast['COMBUSTIVEL_DOMINANTE'].unique()
)

# Aplica filtros de unidade e combustível
mask = (
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
)
df = df_abast[mask].copy()

# Merge com frota para obter tipo, padrão e custo
df = df.merge(
    df_frota[['PLACA', 'Frota', 'PADRAO', 'CARACTERIZACAO', 'CUSTO_PADRAO_MENSAL']],
    on='PLACA', how='left'
)
# Preenche valores ausentes
for col, fill in [('Frota','NÃO ENCONTRADO'), ('PADRAO','N/D'), ('CARACTERIZACAO','N/D')]:
    df[col] = df[col].fillna(fill)
df['CUSTO_PADRAO_MENSAL'] = df['CUSTO_PADRAO_MENSAL'].fillna(0)

# Calcula custo total do veículo
df['CUSTO_TOTAL_VEICULO'] = df['VALOR_TOTAL'] + df['CUSTO_PADRAO_MENSAL']

# Conta OPMs distintos por viatura
df['OPMs_Únicas'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

# Cria abas
tabs = st.tabs(["🔎 Visão Geral", "🚘 Frota por OPM", "📍 OPMs & Municípios", "📋 Detalhamento"])

with tabs[0]:  # Visão Geral
    st.subheader("✨ Indicadores Principais")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Registros", f"{len(df):,}")
    r2.metric("Viaturas Únicas", df['PLACA'].nunique())
    r3.metric("Total Litros", f"{df['TOTAL_LITROS'].sum():,.0f} L")
    r4.metric("Gasto Total (R$)", f"R$ {df['VALOR_TOTAL'].sum():,.2f}")
    st.divider()
    fig = px.bar(
        df.groupby('UNIDADE')['TOTAL_LITROS'].sum().reset_index(),
        x='TOTAL_LITROS', y='UNIDADE', orientation='h',
        labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'},
        title='Consumo por Unidade'
    )
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:  # Distribuição de Frota por OPM
    st.subheader("🚘 Distribuição da Frota por OPM e Caracterização")
    dist = df_frota.groupby(['OPM', 'Frota']).size().reset_index(name='Contagem')
    fig = px.bar(
        dist, x='OPM', y='Contagem', color='Frota', barmode='group',
        labels={'Contagem':'# Veículos','OPM':'Batalhão'},
        title='Veículos por OPM e Tipo'
    )
    st.plotly_chart(fig, use_container_width=True)
    st.divider()
    st.subheader("📊 Caracterização por OPM")
    char = df_frota.groupby(['OPM', 'CARACTERIZACAO']).size().reset_index(name='Contagem')
    fig2 = px.bar(
        char, x='OPM', y='Contagem', color='CARACTERIZACAO', barmode='stack',
        labels={'Contagem':'# Veículos','OPM':'Batalhão'},
        title='Caracterização da Frota'
    )
    st.plotly_chart(fig2, use_container_width=True)

with tabs[2]:  # OPMs & Municípios
    st.subheader("📍 OPMs & Municípios")
    # Municípios do interior (exclui Maceió)
    interior = df_opm[(df_opm['TIPO_LOCAL'].str.lower()=='município') & (df_opm['MUNICÍPIO']!='Maceió')]
    inter = interior.groupby('UNIDADE')['MUNICÍPIO'].nunique().reset_index(name='Municípios')
    inter.rename(columns={'UNIDADE':'OPM'}, inplace=True)
    # Bairros de Maceió
    bairros = df_opm[(df_opm['TIPO_LOCAL'].str.lower()=='bairro') & (df_opm['MUNICÍPIO_REFERÊNCIA']=='Maceió')]
    bair = bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Bairros')
    bair.rename(columns={'UNIDADE':'OPM'}, inplace=True)
    # Viaturas por OPM
    veh = df_frota.groupby('OPM')['PLACA'].nunique().reset_index(name='Viaturas')
    # Combina
    summary = veh.merge(inter, on='OPM', how='left').merge(bair, on='OPM', how='left')
    summary[['Municípios','Bairros']] = summary[['Municípios','Bairros']].fillna(0).astype(int)
    summary['V/ Município'] = (summary['Viaturas']/summary['Municípios']).replace(np.inf,0).round(2)
    summary['V/ Bairro'] = (summary['Viaturas']/summary['Bairros']).replace(np.inf,0).round(2)
    st.dataframe(summary, use_container_width=True)

with tabs[3]:  # Detalhamento
    st.subheader("📋 Ranking Completo de Viaturas")
    rank = df.groupby('PLACA')['TOTAL_LITROS'].sum().reset_index(name='Litros').sort_values('Litros', ascending=False)
    st.dataframe(rank, use_container_width=True)
    st.divider()
    st.subheader("🔝 Top 20 Viaturas por Consumo")
    st.dataframe(rank.head(20), use_container_width=True)
    st.divider()
    st.subheader("🚨 Viaturas em Múltiplas OPMs")
    multi = df.groupby('PLACA')['UNIDADE'].nunique().reset_index(name='OPMs Únicas')
    multi = multi[multi['OPMs Únicas']>1]
    if not multi.empty:
        st.dataframe(multi, use_container_width=True)
    else:
        st.write("Nenhuma viatura abasteceu em mais de uma OPM.")
    st.divider()
    st.subheader("📂 Tabela de Detalhamento")
    df_disp = df.rename(columns={
        'COMBUSTIVEL_DOMINANTE':'Combustível', 'TOTAL_LITROS':'Litros',
        'VALOR_TOTAL':'Valor R$', 'CUSTO_PADRAO_MENSAL':'Custo Locação R$',
        'CUSTO_TOTAL_VEICULO':'Custo Total R$', 'OPMs_Únicas':'OPMs Únicas',
        'PADRAO':'Padrão', 'CARACTERIZACAO':'Caracterização'
    })[[
        'PLACA','UNIDADE','Combustível','Litros','Valor R$','Custo Locação R$',
        'Custo Total R$','Frota','Padrão','Caracterização','OPMs Únicas'
    ]]
    st.table(df_disp)

st.info("🔧 Ajuste os filtros laterais conforme necessário.")
