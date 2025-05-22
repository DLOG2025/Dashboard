import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import math

# Configuração da página e título
st.set_page_config(page_title="DASHBOARD_VIATURAS_DLOG", layout="wide")
st.title("🚓 DASHBOARD_VIATURAS_DLOG - DLOG")

# URLs dos arquivos no GitHub
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"

@st.cache_data
# Função para carregar dados apenas uma vez
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota = pd.read_excel(URL_FROTA)
    df_opm = pd.read_excel(URL_OPM)
    return df_abast, df_frota, df_opm

# Carregamento dos dados
df_abast, df_frota, df_opm = load_data()

# Padroniza PLACA (remove traços e espaços, converte para maiúsculas)
for df in (df_abast, df_frota):
    df['PLACA'] = df['PLACA'].astype(str).str.upper().str.replace('-', '').str.replace(' ', '')

# Sidebar: filtros de unidade e combustível
st.sidebar.header("🎯 Filtros")
unidades = st.sidebar.multiselect(
    "Selecione Unidades:", df_abast['UNIDADE'].unique(), default=list(df_abast['UNIDADE'].unique())
)
combustiveis = st.sidebar.multiselect(
    "Selecione Combustíveis:", df_abast['COMBUSTIVEL_DOMINANTE'].unique(),
    default=list(df_abast['COMBUSTIVEL_DOMINANTE'].unique())
)

# Aplica filtros
df_filtered = df_abast[
    df_abast['UNIDADE'].isin(unidades) & df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
].copy()

# Merge com dados de frota
merge_cols = ['PLACA','Frota','PADRAO','CARACTERIZACAO','CUSTO_PADRAO_MENSAL']
df = df_filtered.merge(df_frota[merge_cols], on='PLACA', how='left')
df['Frota'].fillna('NÃO ENCONTRADO', inplace=True)
df['PADRAO'].fillna('N/D', inplace=True)
df['CARACTERIZACAO'].fillna('N/D', inplace=True)
df['CUSTO_PADRAO_MENSAL'].fillna(0, inplace=True)

# Cálculos adicionais
df['CUSTO_TOTAL_VEICULO'] = df['VALOR_TOTAL'] + df['CUSTO_PADRAO_MENSAL']
df['OPMs_Únicas'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

def truncar(x, casas=2):
    fator = 10 ** casas
    return math.floor(x * fator) / fator

# Abas
tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Visão Geral", "🚘 Frota por OPM", "📍 OPMs & Municípios", "📋 Detalhamento"
])

# Visão Geral
with tab1:
    st.subheader("✨ Indicadores Principais")
    total_veh = df['PLACA'].nunique()
    total_litros = df['TOTAL_LITROS'].sum()
    total_gasto = df['VALOR_TOTAL'].sum()
    media_litros = df.groupby('PLACA')['TOTAL_LITROS'].sum().mean()
    media_gasto = df.groupby('PLACA')['VALOR_TOTAL'].sum().mean()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Registros", f"{len(df):,}")
    c2.metric("Viaturas", f"{total_veh}")
    c3.metric("Total Litros", f"{truncar(total_litros):,.2f} L")
    c4.metric("Total Gasto (R$)", f"R$ {truncar(total_gasto):,.2f}")
    c5.metric("Média Litros/Viatura", f"{truncar(media_litros):,.2f} L")
    c6.metric("Média Gasto/Viatura", f"R$ {truncar(media_gasto):,.2f}")
    st.divider()
    fig = px.bar(
        df.groupby('UNIDADE')['TOTAL_LITROS'].sum().reset_index().sort_values('TOTAL_LITROS', ascending=False),
        x='TOTAL_LITROS', y='UNIDADE', orientation='h',
        labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'}, title='Consumo por Unidade'
    )
    st.plotly_chart(fig, use_container_width=True)

# Frota por OPM
with tab2:
    st.subheader("🚘 Frota por OPM")
    # Tabela: Próprias/Justiça vs Locadas
    table_frota = (df_frota.groupby(['OPM','Frota'])
                   .size().unstack(fill_value=0))
    # Renomear colunas de frota
    table_frota.rename(columns={c: ('PRÓPRIAS/JUSTIÇA' if 'PRÓPR' in c else 'LOCADAS') for c in table_frota.columns}, inplace=True)
    table_frota['TOTAL'] = table_frota.sum(axis=1)
    st.dataframe(table_frota.reset_index(), use_container_width=True)
    st.divider()
    # Tabela: Caracterização
    table_char = df_frota.groupby(['OPM','CARACTERIZACAO']).size().unstack(fill_value=0)
    table_char['TOTAL'] = table_char.sum(axis=1)
    st.subheader("📋 Caracterização da Frota")
    st.dataframe(table_char.reset_index(), use_container_width=True)
    st.divider()
    # Gráfico agrupado
    df_bar = table_frota.reset_index().melt(id_vars='OPM', var_name='Tipo', value_name='Contagem')
    fig2 = px.bar(df_bar, x='OPM', y='Contagem', color='Tipo', barmode='group',
                  labels={'Contagem':'# Veículos','OPM':'Batalhão'},
                  title='Veículos por OPM e Tipo de Frota')
    st.plotly_chart(fig2, use_container_width=True)

# OPMs & Municípios
with tab3:
    st.subheader("📍 OPMs & Municípios")
    # Municípios interior
    interior = df_opm[(df_opm['TIPO_LOCAL'].str.lower()=='município') & (df_opm['MUNICÍPIO']!='Maceió')]
    muni = interior.groupby('UNIDADE')['MUNICÍPIO'].nunique().reset_index(name='Municípios')
    muni.rename(columns={'UNIDADE':'OPM'}, inplace=True)
    # Bairros Maceió
    bairros = df_opm[(df_opm['TIPO_LOCAL'].str.lower()=='bairro') & (df_opm['MUNICÍPIO_REFERÊNCIA']=='Maceió')]
    bair = bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Bairros')
    bair.rename(columns={'UNIDADE':'OPM'}, inplace=True)
    # Viaturas por OPM
    veh = df_frota.groupby('OPM')['PLACA'].nunique().reset_index(name='Viaturas')
    # Merge
    summary = veh.merge(muni, on='OPM', how='left').merge(bair, on='OPM', how='left')
    summary[['Municípios','Bairros']] = summary[['Municípios','Bairros']].fillna(0).astype(int)
    summary['Vtr/Município'] = (summary['Viaturas']/summary['Municípios']).replace(np.inf,0).round(2)
    summary['Vtr/Bairro'] = (summary['Viaturas']/summary['Bairros']).replace(np.inf,0).round(2)
    st.dataframe(summary, use_container_width=True)
    st.divider()
    # Redistribuição sugerida
    st.subheader("📈 Sugestão de Redistribuição")
    valid = summary[summary['Municípios']>0]
    mean_vtr = valid['Vtr/Município'].mean()
    valid['Diferença'] = valid['Vtr/Município'] - mean_vtr
    high = valid.loc[valid['Diferença'].idxmax()]
    low = valid.loc[valid['Diferença'].idxmin()]
    moves = math.floor((high['Diferença'] - low['Diferença'])/2)
    st.markdown(f"- Média Vtr/Município: **{truncar(mean_vtr):.2f}**")
    st.markdown(f"- OPM **{high['OPM']}** está **{truncar(high['Diferença']):.2f}** acima da média.")
    st.markdown(f"- OPM **{low['OPM']}** está **{truncar(low['Diferença']):.2f}** abaixo da média.")
    if moves>0:
        st.markdown(f"→ Realocar **{moves}** viatura(s) de {high['OPM']} para {low['OPM']}.")

# Detalhamento
with tab4:
    st.subheader("📋 Ranking e Detalhamento")
    # Ranking completo
    rank = df.groupby('PLACA').agg(
        Litros=('TOTAL_LITROS','sum'),
        Valor=('VALOR_TOTAL','sum')
    ).reset_index().sort_values('Litros', ascending=False).reset_index(drop=True)
    rank['Posição'] = rank.index + 1
    rank[['Litros','Valor']] = rank[['Litros','Valor']].applymap(truncar)
    rank_disp = rank.copy()
    rank_disp['Litros'] = rank_disp['Litros'].map(lambda x: f"{x:,.2f}")
    rank_disp['Valor'] = rank_disp['Valor'].map(lambda x: f"R$ {x:,.2f}")
    st.subheader("📃 Ranking Completo")
    st.dataframe(rank_disp[['Posição','PLACA','Litros','Valor']], use_container_width=True)
    st.divider()
    # Top 20
    st.subheader("🔝 Top 20 por Consumo")
    st.dataframe(rank_disp.head(20)[['Posição','PLACA','Litros','Valor']], use_container_width=True)
    st.divider()
    # Multiplas OPMs
    st.subheader("🚨 Múltiplas OPMs")
    multi = df.groupby('PLACA')['UNIDADE'].apply(lambda x: sorted(x.unique())).reset_index(name='OPMs')
    multi['Count'] = multi['OPMs'].apply(len)
    multi = multi[multi['Count']>1]
    st.dataframe(multi[['PLACA','OPMs','Count']], use_container_width=True)
    st.divider()
    # Tabela detalhada
    disp = df.rename(columns={
        'COMBUSTIVEL_DOMINANTE':'Combustível', 'TOTAL_LITROS':'Litros',
        'VALOR_TOTAL':'Valor R$', 'CUSTO_PADRAO_MENSAL':'Custo Locação',
        'CUSTO_TOTAL_VEICULO':'Custo Total', 'OPMs_Únicas':'OPMs Únicas',
        'PADRAO':'Padrão','CARACTERIZACAO':'Caracterização'
    })[[
        'PLACA','UNIDADE','Combustível','Litros','Valor R$',
        'Custo Locação','Custo Total','Frota','Padrão','Caracterização','OPMs Únicas'
    ]]
    for col in ['Litros','Valor R$','Custo Locação','Custo Total']:
        disp[col] = disp[col].apply(truncar).map(lambda x: f"{x:,.2f}")
    st.table(disp)

st.info("🔧 Ajuste filtros conforme necessário.")
