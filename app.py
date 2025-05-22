import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import math
import unicodedata

# Configuração da página e título
st.set_page_config(page_title="DASHBOARD_VIATURAS_DLOG", layout="wide")
st.title("🚓 DASHBOARD_VIATURAS_DLOG - DLOG")

# URLs dos arquivos no GitHub
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"
URL_PADROES = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/PADR%C3%95ES_LOCADOS.xlsx"

@st.cache_data
# Carrega dados apenas uma vez
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota = pd.read_excel(URL_FROTA)
    df_opm = pd.read_excel(URL_OPM)
    df_padroes = pd.read_excel(URL_PADROES)
    return df_abast, df_frota, df_opm, df_padroes

# Carregamento dos dados
df_abast, df_frota, df_opm, df_padroes = load_data()

# Normalização de acentos e padronização de texto
def normalize_text(s):
    if pd.isna(s): return s
    nk = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in nk if not unicodedata.combining(c))

# Unificação de nomes de OPM
def unify_opm(name):
    if pd.isna(name): return name
    s = normalize_text(name).upper().replace(' ', '')
    # Exemplo: unificar CPMI variantes
    if 'CPMI' in s or 'CPM/I' in s or (s.startswith('3') and 'CPM' in s):
        return '3ª CPMI'
    return normalize_text(name)

# Aplica unificação em colunas relevantes
df_abast['UNIDADE'] = df_abast['UNIDADE'].apply(unify_opm)
if 'OPM' in df_frota.columns:
    df_frota['OPM'] = df_frota['OPM'].apply(unify_opm)
df_opm['UNIDADE'] = df_opm['UNIDADE'].apply(unify_opm)

# Padroniza PLACA (remove traços e espaços, converte para maiúsculas)
for df in (df_abast, df_frota):
    df['PLACA'] = df['PLACA'].astype(str).str.upper().str.replace('-', '').str.replace(' ', '')

# Sidebar: filtros de unidade e combustível
st.sidebar.header("🎯 Filtros")
unidades = st.sidebar.multiselect(
    "Selecione Unidades:", sorted(df_abast['UNIDADE'].unique()),
    default=sorted(df_abast['UNIDADE'].unique())
)
combustiveis = st.sidebar.multiselect(
    "Selecione Combustíveis:", sorted(df_abast['COMBUSTIVEL_DOMINANTE'].unique()),
    default=sorted(df_abast['COMBUSTIVEL_DOMINANTE'].unique())
)

# Filtra dados de abastecimento
df = df_abast[
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
].copy()

# Prepara custos de locação a partir de PADRÕES
# Ajusta colunas em df_padroes: primeira é padrão, segunda é valor
padroes_cols = list(df_padroes.columns)
id_col, val_col = padroes_cols[0], padroes_cols[1]
df_padroes.rename(columns={id_col: 'PADRAO', val_col: 'CUSTO_LOCACAO_PADRAO'}, inplace=True)
# Trunca valor padrão
df_padroes['CUSTO_LOCACAO_PADRAO'] = df_padroes['CUSTO_LOCACAO_PADRAO'].apply(lambda x: float(str(x).replace('R$','').replace(',','.')))

# Merge frota com padrões
df_frota = df_frota.merge(
    df_padroes[['PADRAO','CUSTO_LOCACAO_PADRAO']], on='PADRAO', how='left'
)
# Em veículos não locados, custo padrão = 0
mask_loc = df_frota['Frota'].str.upper() == 'LOCADO'
df_frota['CUSTO_PADRAO_MENSAL'] = 0.0
df_frota.loc[mask_loc, 'CUSTO_PADRAO_MENSAL'] = df_frota.loc[mask_loc, 'CUSTO_LOCACAO_PADRAO']

# Remove coluna auxiliar
df_frota.drop(columns=['CUSTO_LOCACAO_PADRAO'], inplace=True)

# Merge de df com dados de frota
merge_cols = ['PLACA','OPM','Frota','PADRAO','CARACTERIZACAO','CUSTO_PADRAO_MENSAL']
df = df.merge(df_frota[merge_cols], on='PLACA', how='left')
# Preenche nulos
df['Frota'] = df['Frota'].fillna('NÃO ENCONTRADO')
df['PADRAO'] = df['PADRAO'].fillna('N/D')
df['CARACTERIZACAO'] = df['CARACTERIZACAO'].fillna('N/D')

# Cálculos adicionais
# custo total = combustível + locação
df['CUSTO_TOTAL_VEICULO'] = df['VALOR_TOTAL'] + df['CUSTO_PADRAO_MENSAL']
# número de frotas onde abasteceu
df['Num_Frotas'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

# Função para truncar valores (sem arredondamento)
def truncar(x, casas=2):
    fator = 10 ** casas
    try:
        return math.floor(float(x) * fator) / fator
    except:
        return x

# Cria abas
tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Visão Geral", "🚘 Frota por OPM", "📍 OPMs & Municípios", "📋 Detalhamento"
])

# ----- ABA 1: Visão Geral -----
with tab1:
    st.subheader("✨ Indicadores Principais")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    total_veh = df['PLACA'].nunique()
    total_lit = df['TOTAL_LITROS'].sum()
    total_val = df['VALOR_TOTAL'].sum()
    media_lit = df.groupby('PLACA')['TOTAL_LITROS'].sum().mean()
    media_val = df.groupby('PLACA')['VALOR_TOTAL'].sum().mean()
    c1.metric("Registros", f"{len(df):,}")
    c2.metric("Viaturas", f"{total_veh}")
    c3.metric("Total Litros", f"{truncar(total_lit):,.2f} L")
    c4.metric("Total Gasto (R$)", f"R$ {truncar(total_val):,.2f}")
    c5.metric("Média Litros/Viatura", f"{truncar(media_lit):,.2f} L")
    c6.metric("Média Gasto/Viatura", f"R$ {truncar(media_val):,.2f}")
    st.divider()
    fig = px.bar(
        df.groupby('UNIDADE')['TOTAL_LITROS'].sum().reset_index().sort_values('TOTAL_LITROS', ascending=False),
        x='TOTAL_LITROS', y='UNIDADE', orientation='h',
        labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'}, title='Consumo por Unidade'
    )
    st.plotly_chart(fig, use_container_width=True)

# ----- ABA 2: Frota por OPM -----
with tab2:
    st.subheader("🚘 Frota por OPM")
    # Tabela: Próprias/Justiça vs Locadas
    tbl = df_frota.groupby(['OPM','Frota']).size().unstack(fill_value=0)
    # renomeia
    if 'PRÓPRIO' in tbl.columns:
        tbl.rename(columns={'PRÓPRIO':'PRÓPRIAS/JUSTIÇA'}, inplace=True)
    if 'LOCADO' in tbl.columns:
        tbl.rename(columns={'LOCADO':'LOCADAS'}, inplace=True)
    tbl['TOTAL'] = tbl.sum(axis=1)
    st.subheader("📋 Contagem de Veículos")
    st.dataframe(tbl.reset_index(), use_container_width=True)
    st.divider()
    # Caracterização
    char = df_frota.groupby(['OPM','CARACTERIZACAO']).size().unstack(fill_value=0)
    char['TOTAL'] = char.sum(axis=1)
    st.subheader("📋 Caracterização da Frota por OPM")
    st.dataframe(char.reset_index(), use_container_width=True)
    st.divider()
    # Gráfico
    dist = tbl.reset_index().melt(id_vars='OPM', var_name='Tipo', value_name='Contagem')
    fig2 = px.bar(
        dist, x='OPM', y='Contagem', color='Tipo', barmode='group',
        labels={'Contagem':'# Veículos','OPM':'Batalhão'},
        title='Veículos por OPM e Tipo'
    )
    st.plotly_chart(fig2, use_container_width=True)

# ----- ABA 3: OPMs & Municípios -----
with tab3:
    st.subheader("📍 OPMs & Municípios")
    interior = df_opm[(df_opm['TIPO_LOCAL'].str.lower()=='municipio') & (df_opm['MUNICIPIO']!='Maceio')]
    muni = interior.groupby('UNIDADE')['MUNICIPIO'].nunique().reset_index(name='Municípios')
    muni.rename(columns={'UNIDADE':'OPM'}, inplace=True)
    bairros = df_opm[(df_opm['TIPO_LOCAL'].str.lower()=='bairro') & (df_opm['MUNICIPIO_REFERENCIA']=='Maceio')]
    bair = bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Bairros')
    bair.rename(columns={'UNIDADE':'OPM'}, inplace=True)
    veh = df_frota.groupby('OPM')['PLACA'].nunique().reset_index(name='Viaturas')
    summary = veh.merge(muni, on='OPM', how='left').merge(bair, on='OPM', how='left')
    summary[['Municípios','Bairros']] = summary[['Municípios','Bairros']].fillna(0).astype(int)
    summary['Vtr/Município'] = (summary['Viaturas']/summary['Municípios']).replace(np.inf,0).round(2)
    summary['Vtr/Bairro'] = (summary['Viaturas']/summary['Bairros']).replace(np.inf,0).round(2)
    st.dataframe(summary, use_container_width=True)
    st.divider()
    st.subheader("📈 Sugestão de Redistribuição")
    valid = summary[summary['Municípios']>0]
    mean_vtr = valid['Vtr/Município'].mean()
    valid['Dif'] = valid['Vtr/Município'] - mean_vtr
    high = valid.loc[valid['Dif'].idxmax()]
    low = valid.loc[valid['Dif'].idxmin()]
    moves = math.floor((high['Dif'] - low['Dif'])/2)
    st.markdown(f"- Média Vtr/Município: **{truncar(mean_vtr):.2f}**")
    st.markdown(f"- OPM **{high['OPM']}** está **{truncar(high['Dif']):.2f}** acima da média.")
    st.markdown(f"- OPM **{low['OPM']}** está **{truncar(low['Dif']):.2f}** abaixo da média.")
    if moves>0:
        st.markdown(f"→ Realocar **{moves}** viatura(s) de {high['OPM']} para {low['OPM']}.")

# ----- ABA 4: Detalhamento -----
with tab4:
    st.subheader("📋 Ranking e Detalhamento")
    # Ranking completo com OPM
    base_rank = df.groupby('PLACA').agg(
        Litros=('TOTAL_LITROS','sum'),
        Valor=('VALOR_TOTAL','sum')
    ).reset_index().sort_values('Litros', ascending=False)
    # inclui OPM do veículo
    opm_map = df_frota[['PLACA','OPM']].drop_duplicates()
    base_rank = base_rank.merge(opm_map, on='PLACA', how='left')
    base_rank['Posição'] = base_rank.index + 1
    base_rank[['Litros','Valor']] = base_rank[['Litros','Valor']].applymap(truncar)
    disp_rank = base_rank.copy()
    disp_rank['Litros'] = disp_rank['Litros'].map(lambda x: f"{x:,.2f}")
    disp_rank['Valor'] = disp_rank['Valor'].map(lambda x: f"R$ {x:,.2f}")
    st.subheader("📃 Ranking Completo")
    st.dataframe(disp_rank[['Posição','PLACA','OPM','Litros','Valor']], use_container_width=True)
    st.divider()
    # Top 20
    st.subheader("🔝 Top 20 por Consumo")
    st.dataframe(disp_rank.head(20)[['Posição','PLACA','OPM','Litros','Valor']], use_container_width=True)
    st.divider()
    # Abastecimento em múltiplas frotas
    st.subheader("🚨 Abastecimento em múltiplas frotas")
    multi = df.groupby('PLACA')['UNIDADE'].apply(lambda x: sorted(x.unique())).reset_index(name='Frotas')
    multi['Nº de frotas abastecidas'] = multi['Frotas'].apply(len)
    multi = multi[multi['Nº de frotas abastecidas']>1]
    st.dataframe(multi[['PLACA','Frotas','Nº de frotas abastecidas']], use_container_width=True)
    st.divider()
    # Tabela final detalhada
    disp = df.rename(columns={
        'COMBUSTIVEL_DOMINANTE':'Combustível','TOTAL_LITROS':'Litros',
        'VALOR_TOTAL':'Valor R$', 'CUSTO_PADRAO_MENSAL':'Custo Locação',
        'CUSTO_TOTAL_VEICULO':'Custo Total','Num_Frotas':'Nº de frotas abastecidas',
        'PADRAO':'Padrão','CARACTERIZACAO':'Caracterização','OPM':'OPM'
    })[[
        'Posição' if False else 'PLACA','OPM','UNIDADE','Combustível','Litros','Valor R$',
        'Custo Locação','Custo Total','Frota','Padrão','Caracterização','Nº de frotas abastecidas'
    ]]
    # truncagem e formatação
    for col in ['Litros','Valor R$','Custo Locação','Custo Total']:
        disp[col] = disp[col].apply(truncar).map(lambda x: f"{x:,.2f}")
    st.table(disp)

st.info("🔧 Ajuste filtros conforme necessário.")
