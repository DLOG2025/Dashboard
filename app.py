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
    "Selecione Unidades:", df_abast['UNIDADE'].unique(),
    default=df_abast['UNIDADE'].unique()
)
combustiveis = st.sidebar.multiselect(
    "Selecione Combustíveis:", df_abast['COMBUSTIVEL_DOMINANTE'].unique(),
    default=df_abast['COMBUSTIVEL_DOMINANTE'].unique()
)

# Aplica filtros
mask = (
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
)
df = df_abast[mask].copy()

# Merge com dados de frota
df = df.merge(
    df_frota[['PLACA','Frota','PADRAO','CARACTERIZACAO','CUSTO_PADRAO_MENSAL']],
    on='PLACA', how='left'
)
# Preenche valores ausentes
df['Frota'] = df['Frota'].fillna('NÃO ENCONTRADO')
df['PADRAO'] = df['PADRAO'].fillna('N/D')
df['CARACTERIZACAO'] = df['CARACTERIZACAO'].fillna('N/D')
df['CUSTO_PADRAO_MENSAL'] = df['CUSTO_PADRAO_MENSAL'].fillna(0)

# Cálculos adicionais
# custo total = combustível + locação
df['CUSTO_TOTAL_VEICULO'] = df['VALOR_TOTAL'] + df['CUSTO_PADRAO_MENSAL']
# número de OPMs únicos por viatura
df['OPMs_Únicas'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

# Função para truncar valores (sem arredondamento)
def truncar(x, casas=2):
    fator = 10 ** casas
    return math.floor(x * fator) / fator

# Criação de abas
tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Visão Geral", "🚘 Frota por OPM", "📍 OPMs & Municípios", "📋 Detalhamento"
])

# ----- ABA 1: Visão Geral -----
with tab1:
    st.subheader("✨ Indicadores Principais")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    total_veh = df['PLACA'].nunique()
    total_litro = df['TOTAL_LITROS'].sum()
    total_gasto = df['VALOR_TOTAL'].sum()
    media_litro = df.groupby('PLACA')['TOTAL_LITROS'].sum().mean()
    media_gasto = df.groupby('PLACA')['VALOR_TOTAL'].sum().mean()
    c1.metric("Registros", f"{len(df):,}")
    c2.metric("Viaturas", f"{total_veh}")
    c3.metric("Total Litros", f"{truncar(total_litro):,.2f} L")
    c4.metric("Total Gasto (R$)", f"R$ {truncar(total_gasto):,.2f}")
    c5.metric("Média Litros/Viatura", f"{truncar(media_litro):,.2f} L")
    c6.metric("Média Gasto/Viatura", f"R$ {truncar(media_gasto):,.2f}")
    st.divider()
    # Gráfico de Consumo por Unidade
    fig1 = px.bar(
        df.groupby('UNIDADE')['TOTAL_LITROS'].sum().reset_index(),
        x='TOTAL_LITROS', y='UNIDADE', orientation='h',
        labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'},
        title='Consumo por Unidade'
    )
    st.plotly_chart(fig1, use_container_width=True)
    # Top 5 viaturas
    st.subheader("🚀 Top 5 Viaturas (Litros)")
    top5 = df.groupby('PLACA')['TOTAL_LITROS'].sum() \
             .sort_values(ascending=False).head(5).reset_index()
    top5['TOTAL_LITROS'] = top5['TOTAL_LITROS'].apply(truncar)
    top5 = top5.rename(columns={'TOTAL_LITROS':'Litros'})
    st.table(top5)

# ----- ABA 2: Frota por OPM -----
with tab2:
    st.subheader("🚘 Contagem de Frota por OPM e Tipo")
    # Tabela de próprias/locadas
    frota_counts = df_frota.groupby(['OPM','Frota']).size().unstack(fill_value=0)
    frota_counts = frota_counts.rename(columns={'PRÓPRIO':'PRÓPRIAS/JUSTIÇA','LOCADO':'LOCADAS'})
    frota_counts['TOTAL'] = frota_counts.sum(axis=1)
    st.dataframe(frota_counts.reset_index(), use_container_width=True)
    st.divider()
    # Tabela de caracterização
    char_counts = df_frota.groupby(['OPM','CARACTERIZACAO']).size().unstack(fill_value=0)
    char_counts['TOTAL'] = char_counts.sum(axis=1)
    st.subheader("📋 Caracterização da Frota por OPM")
    st.dataframe(char_counts.reset_index(), use_container_width=True)
    st.divider()
    # Gráfico de distribuição
    st.subheader("🌐 Gráfico de Barras: Contagem por OPM e Tipo")
    dist = frota_counts.reset_index().melt(
        id_vars=['OPM'], value_vars=['PRÓPRIAS/JUSTIÇA','LOCADAS'],
        var_name='Tipo', value_name='Contagem'
    )
    fig2 = px.bar(
        dist, x='OPM', y='Contagem', color='Tipo', barmode='group',
        labels={'Contagem':'# Veículos','OPM':'Batalhão'},
        title='Veículos por OPM e Tipo'
    )
    st.plotly_chart(fig2, use_container_width=True)

# ----- ABA 3: OPMs & Municípios -----
with tab3:
    st.subheader("📍 OPMs & Municípios")
    # Municípios do interior (exclui Maceió)
    interior = df_opm[
        (df_opm['TIPO_LOCAL'].str.lower()=='município') &
        (df_opm['MUNICÍPIO']!='Maceió')
    ]
    inter = interior.groupby('UNIDADE')['MUNICÍPIO'].nunique().reset_index(name='Municípios')
    inter = inter.rename(columns={'UNIDADE':'OPM'})
    # Bairros de Maceió
    bairros = df_opm[
        (df_opm['TIPO_LOCAL'].str.lower()=='bairro') &
        (df_opm['MUNICÍPIO_REFERÊNCIA']=='Maceió')
    ]
    bair = bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Bairros')
    bair = bair.rename(columns={'UNIDADE':'OPM'})
    # Viaturas por OPM
    veh = df_frota.groupby('OPM')['PLACA'].nunique().reset_index(name='Viaturas')
    # Combina tudo
    summary = veh.merge(inter, on='OPM', how='left').merge(bair, on='OPM', how='left')
    summary[['Municípios','Bairros']] = summary[['Municípios','Bairros']].fillna(0).astype(int)
    summary['Vtr/Município'] = (summary['Viaturas']/summary['Municípios']).replace(np.inf,0).round(2)
    summary['Vtr/Bairro'] = (summary['Viaturas']/summary['Bairros']).replace(np.inf,0).round(2)
    st.dataframe(summary, use_container_width=True)
    st.divider()
    # Sugestão de redistribuição
    st.subheader("📈 Sugestão de Redistribuição")
    interior_sum = summary[summary['Municípios']>0]
    media_vtr = interior_sum['Vtr/Município'].mean()
    interior_sum['Diferença'] = interior_sum['Vtr/Município'] - media_vtr
    maior = interior_sum.loc[interior_sum['Diferença'].idxmax()]
    menor = interior_sum.loc[interior_sum['Diferença'].idxmin()]
    reloc = math.floor((maior['Diferença'] - menor['Diferença'])/2)
    st.markdown(f"- Média de viaturas/município: **{truncar(media_vtr):.2f}**")
    st.markdown(f"- **{maior['OPM']}** está **{truncar(maior['Diferença']):.2f}** acima da média.")
    st.markdown(f"- **{menor['OPM']}** está **{truncar(menor['Diferença']):.2f}** abaixo da média.")
    if reloc>0:
        st.markdown(f"→ Sugere-se realocar **{reloc}** viatura(s) de {maior['OPM']} para {menor['OPM']}.")

# ----- ABA 4: Detalhamento -----
with tab4:
    # Ranking completo com valores e posição
    rank = df.groupby('PLACA').agg(
        Litros=('TOTAL_LITROS','sum'),
        Valor=('VALOR_TOTAL','sum')
    ).reset_index().sort_values('Litros', ascending=False).reset_index(drop=True)
    rank['Posição'] = rank.index + 1
    # Trunca e formata
    rank['Litros'] = rank['Litros'].apply(truncar)
    rank['Valor'] = rank['Valor'].apply(truncar)
    rank_display = rank.copy()
    rank_display['Litros'] = rank_display['Litros'].apply(lambda x: f"{x:,.2f}")
    rank_display['Valor'] = rank_display['Valor'].apply(lambda x: f"R$ {x:,.2f}")
    st.subheader("📋 Ranking Completo de Viaturas")
    st.dataframe(rank_display[['Posição','PLACA','Litros','Valor']], use_container_width=True)
    st.divider()
    # Top 20 viaturas
    st.subheader("🔝 Top 20 Viaturas por Consumo")
    st.dataframe(rank_display.head(20)[['Posição','PLACA','Litros','Valor']], use_container_width=True)
    st.divider()
    # Viaturas em múltiplas OPMs: placa + lista de OPMs
    st.subheader("🚨 Viaturas em Múltiplas OPMs")
    multi = df.groupby('PLACA')['UNIDADE'].apply(lambda x: sorted(x.unique())).reset_index(name='OPMs_List')
    multi['OPMs_Únicas'] = multi['OPMs_List'].apply(len)
    multi = multi[multi['OPMs_Únicas']>1]
    st.dataframe(multi[['PLACA','OPMs_Únicas','OPMs_List']], use_container_width=True)
    st.divider()
    # Tabela de detalhamento final
    st.subheader("📂 Tabela de Detalhamento Completo")
    df_disp = df.rename(columns={
        'COMBUSTIVEL_DOMINANTE':'Combustível','TOTAL_LITROS':'Litros',
        'VALOR_TOTAL':'Valor R$','CUSTO_PADRAO_MENSAL':'Custo Locação',
        'CUSTO_TOTAL_VEICULO':'Custo Total','OPMs_Únicas':'OPMs Únicas',
        'PADRAO':'Padrão','CARACTERIZACAO':'Caracterização'
    })[[
        'PLACA','UNIDADE','Combustível','Litros','Valor R$','Custo Locação',
        'Custo Total','Frota','Padrão','Caracterização','OPMs Únicas'
    ]]
    # Trunca e formata colunas numéricas
    for col in ['Litros','Valor R$','Custo Locação','Custo Total']:
        df_disp[col] = df_disp[col].apply(truncar).apply(lambda x: f"{x:,.2f}")
    st.table(df_disp)

st.info("🔧 Ajuste os filtros laterais conforme necessário.")
