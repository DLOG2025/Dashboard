import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import math
import unicodedata
import re

# ---------- Configuração da página ----------
title = "🚓 DASHBOARD_VIATURAS_DLOG - DLOG"
st.set_page_config(page_title=title, layout="wide")
st.title(title)

# ---------- URLs dos arquivos ----------
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"
URL_PADROES = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/PADR%C3%95ES_LOCADOS.xlsx"

# ---------- Carrega dados com cache ----------
@st.cache_data
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota = pd.read_excel(URL_FROTA)
    df_opm = pd.read_excel(URL_OPM)
    df_padroes = pd.read_excel(URL_PADROES)
    return df_abast, df_frota, df_opm, df_padroes

# Carregamento
[df_abast, df_frota, df_opm, df_padroes] = load_data()

# ---------- Normalize nomes de colunas de OPM ----------
norm_cols = {col: unicodedata.normalize('NFKD', col).encode('ASCII','ignore').decode() for col in df_opm.columns}
df_opm.rename(columns=norm_cols, inplace=True)
df_opm.columns = [c.upper() for c in df_opm.columns]

# ---------- Funções utilitárias ----------
def normalize_text(s):
    if pd.isna(s): return s
    nk = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in nk if not unicodedata.combining(c))

def unify_opm(name):
    if pd.isna(name): return name
    raw = normalize_text(name)
    raw = re.sub(r'[ºª°]', '', raw)  # remove ordinais
    raw = re.sub(r'(?i)C\W*P\W*M\W*I', 'CPMI', raw)  # unifica CPMI variantes
    raw = raw.replace('/', ' ')
    raw = re.sub(r'[^A-Za-z0-9 ]', ' ', raw)
    s = ' '.join(raw.split()).upper()
    # BPM genérico
    m = re.match(r'^(\d+)\s*BPM$', s)
    if m:
        return f"{int(m.group(1))} BPM"
    # SECAO EMG
    if re.search(r'\d+\s*SECAO\s*EMG', s):
        num = re.search(r'(\d+)', s).group(1)
        return f"{num}ª SECAO EMG"
    # CPMI consolidado
    if 'CPMI' in s:
        return '3ª CPMI'
    return s

def clean_plate(x):
    return str(x).upper().replace('-', '').replace(' ', '')

def parse_currency(x):
    if pd.isna(x): return 0.0
    if isinstance(x, (int, float)): return float(x)
    s = re.sub(r'[^0-9,\.]', '', str(x))
    if s.count(',') and s.count('.'):
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def truncar(x, casas=2):
    try:
        f = 10 ** casas
        return math.floor(float(x) * f) / f
    except:
        return x

# ---------- Prepara dados ----------
for df in [df_abast, df_frota]:
    if 'UNIDADE' in df.columns:
        df['UNIDADE'] = df['UNIDADE'].apply(unify_opm)
    if 'OPM' in df.columns:
        df['OPM'] = df['OPM'].apply(unify_opm)

df_abast['PLACA'] = df_abast['PLACA'].apply(clean_plate)
df_frota['PLACA'] = df_frota['PLACA'].apply(clean_plate)

st.sidebar.header('🎯 Filtros')
unidades = st.sidebar.multiselect('Selecione Unidades:', sorted(df_abast['UNIDADE'].dropna().unique()), default=sorted(df_abast['UNIDADE'].dropna().unique()))
combustiveis = st.sidebar.multiselect('Selecione Combustíveis:', sorted(df_abast['COMBUSTIVEL_DOMINANTE'].dropna().unique()), default=sorted(df_abast['COMBUSTIVEL_DOMINANTE'].dropna().unique()))

df = df_abast[df_abast['UNIDADE'].isin(unidades) & df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)].copy()

# Padrões de locação
id_col, val_col = df_padroes.columns[0], df_padroes.columns[1]
df_padroes.rename(columns={id_col:'PADRAO', val_col:'CUSTO_LOCACAO_PADRAO'}, inplace=True)
df_padroes['CUSTO_LOCACAO_PADRAO'] = df_padroes['CUSTO_LOCACAO_PADRAO'].apply(parse_currency)

df_frota = df_frota.merge(df_padroes[['PADRAO','CUSTO_LOCACAO_PADRAO']], on='PADRAO', how='left')
mask_loc = df_frota['Frota'].str.upper() == 'LOCADO'
df_frota['CUSTO_PADRAO_MENSAL'] = 0.0
df_frota.loc[mask_loc,'CUSTO_PADRAO_MENSAL'] = df_frota.loc[mask_loc,'CUSTO_LOCACAO_PADRAO']
if 'CUSTO_LOCACAO_PADRAO' in df_frota.columns:
    df_frota.drop(columns=['CUSTO_LOCACAO_PADRAO'], inplace=True)

merge_cols = ['PLACA','OPM','Frota','PADRAO','CARACTERIZACAO','CUSTO_PADRAO_MENSAL']
df = df.merge(df_frota[merge_cols], on='PLACA', how='left')
df.fillna({'Frota':'NÃO LOCALIZADO','PADRAO':'N/D','CARACTERIZACAO':'N/D'}, inplace=True)
df['Nº de frotas abastecidas'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

# ---------- Abas ----------
t1, t2, t3, t4 = st.tabs(['🔎 Visão Geral','🚘 Frota por OPM','📍 OPMs & Municípios','📋 Detalhamento'])

# Visão Geral
t1.subheader('✨ Indicadores Principais')
total_veh = df['PLACA'].nunique()
total_lit = df['TOTAL_LITROS'].sum()
total_val = df['VALOR_TOTAL'].sum()
avg_lit = df.groupby('PLACA')['TOTAL_LITROS'].sum().mean()
avg_val = df.groupby('PLACA')['VALOR_TOTAL'].sum().mean()
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric('Registros',f'{len(df):,}')
c2.metric('Viaturas',f'{total_veh}')
c3.metric('Total Litros',f'{truncar(total_lit):,.2f} L')
c4.metric('Total Gasto (R$)',f'R$ {truncar(total_val):,.2f}')
c5.metric('Média Litros/Viatura',f'{truncar(avg_lit):,.2f} L')
c6.metric('Média Gasto/Viatura',f'R$ {truncar(avg_val):,.2f}')
st.divider()
fig = px.bar(df.groupby('UNIDADE')['TOTAL_LITROS'].sum().reset_index().sort_values('TOTAL_LITROS',ascending=False), x='TOTAL_LITROS', y='UNIDADE', orientation='h', labels={'TOTAL_LITROS':'Litros','UNIDADE':'Unidade'}, title='Consumo por Unidade')
st.plotly_chart(fig,use_container_width=True)

# Frota por OPM
with t2:
    st.subheader('🚘 Frota por OPM')
    tbl = df_frota.groupby(['OPM','Frota']).size().unstack(fill_value=0)
    if 'PRÓPRIO' in tbl.columns: tbl.rename(columns={'PRÓPRIO':'PRÓPRIAS/JUSTIÇA'}, inplace=True)
    if 'LOCADO' in tbl.columns: tbl.rename(columns={'LOCADO':'LOCADAS'}, inplace=True)
    tbl['TOTAL'] = tbl.sum(axis=1)
    st.dataframe(tbl.reset_index().fillna('NÃO LOCALIZADO'),use_container_width=True)
    st.divider()
    char = df_frota.groupby(['OPM','CARACTERIZACAO']).size().unstack(fill_value=0)
    char['TOTAL']=char.sum(axis=1)
    st.dataframe(char.reset_index().fillna('NÃO LOCALIZADO'),use_container_width=True)
    st.divider()
    dist = tbl.reset_index().melt(id_vars='OPM',var_name='Tipo',value_name='Contagem')
    fig2 = px.bar(dist,x='OPM',y='Contagem',color='Tipo',barmode='group',labels={'Contagem':'# Veículos','OPM':'Batalhão'},title='Veículos por OPM e Tipo')
    st.plotly_chart(fig2,use_container_width=True)

# OPMs & Municípios
with t3:
    st.subheader('📍 OPMs & Municípios')
    df_opm['TIPO_NORM']=df_opm['TIPO_LOCAL'].apply(lambda x: normalize_text(x).lower() if pd.notna(x) else '')
    df_opm['MUNI_NORM']=df_opm['MUNICIPIO'].apply(lambda x: normalize_text(x) if pd.notna(x) else '')
    df_opm['MUNI_REF_NORM']=df_opm['MUNICIPIO_REFERENCIA'].apply(lambda x: normalize_text(x) if pd.notna(x) else '')
    interior=df_opm[(df_opm['TIPO_NORM']=='municipio')&(df_opm['MUNI_NORM']!='MACEIO')]
    muni=interior.groupby('UNIDADE')['MUNICIPIO'].nunique().reset_index(name='Municípios')
    muni.rename(columns={'UNIDADE':'OPM'},inplace=True)
    bairros=df_opm[(df_opm['TIPO_NORM']=='bairro')&(df_opm['MUNI_REF_NORM']=='MACEIO')]
    bair=bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Bairros')
    bair.rename(columns={'UNIDADE':'OPM'},inplace=True)
    vehs=df_frota.groupby('OPM')['PLACA'].nunique().reset_index(name='Viaturas')
    summary=vehs.merge(muni,on='OPM',how='left').merge(bair,on='OPM',how='left')
