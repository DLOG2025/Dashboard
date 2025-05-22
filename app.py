import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import math
import unicodedata
import re

PAGE_TITLE = "🚓 DASHBOARD_VIATURAS - DLOG"
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

# ---------- URLs dos arquivos ----------
URL_ABAST = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Abastecimentos_Consolidados.xlsx"
URL_FROTA = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/Frota_Master_Enriched.xlsx"
URL_OPM = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/OPM_Municipios_Enriched.xlsx"
URL_PADROES = "https://github.com/DLOG2025/Dashboard/raw/refs/heads/main/PADR%C3%95ES_LOCADOS.xlsx"

@st.cache_data
def load_data():
    df_abast = pd.read_excel(URL_ABAST)
    df_frota = pd.read_excel(URL_FROTA)
    df_opm = pd.read_excel(URL_OPM)
    df_padroes = pd.read_excel(URL_PADROES)
    return df_abast, df_frota, df_opm, df_padroes

df_abast, df_frota, df_opm, df_padroes = load_data()

# ---------- Ajuste colunas df_opm ----------
df_opm.rename(columns={'MUNICÍPIO':'MUNICIPIO', 'MUNICÍPIO_REFERÊNCIA':'MUNICIPIO_REFERENCIA'}, inplace=True)

def normalize_text(s):
    if pd.isna(s): return s
    nk = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in nk if not unicodedata.combining(c))

def unify_opm(name):
    if pd.isna(name): return name
    raw = normalize_text(name)
    # remove letras ou ordinais grudados ao número
    raw = re.sub(r'(?<=\d)[A-Za-zºª°]+', '', raw)
    # unifica CPMI variantes
    raw = re.sub(r'(?i)\bC\W*P\W*M\W*I\b', 'CPMI', raw)
    raw = raw.replace('/', ' ')
    raw = re.sub(r'[^A-Za-z0-9 ]', ' ', raw)
    s = ' '.join(raw.split()).upper()
    m = re.match(r'^(\d+)\s*BPM$', s)
    if m:
        return f"{int(m.group(1))} BPM"
    if re.search(r'\d+\s*SECAO\s*EMG', s):
        num = re.search(r'(\d+)', s).group(1)
        return f"{num}ª SECAO EMG"
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

# ---------- Pré-processamento ----------
df_abast['UNIDADE'] = df_abast['UNIDADE'].apply(unify_opm)
df_frota['OPM'] = df_frota['OPM'].apply(unify_opm)
df_abast['PLACA'] = df_abast['PLACA'].apply(clean_plate)
df_frota['PLACA'] = df_frota['PLACA'].apply(clean_plate)

# Filtros
st.sidebar.header('🎯 Filtros')
unidades = st.sidebar.multiselect(
    'Selecione OPM abastecimento:',
    sorted(df_abast['UNIDADE'].dropna().unique()),
    default=sorted(df_abast['UNIDADE'].dropna().unique())
)
combustiveis = st.sidebar.multiselect(
    'Selecione Combustíveis:',
    sorted(df_abast['COMBUSTIVEL_DOMINANTE'].dropna().unique()),
    default=sorted(df_abast['COMBUSTIVEL_DOMINANTE'].dropna().unique())
)
df = df_abast[
    df_abast['UNIDADE'].isin(unidades) &
    df_abast['COMBUSTIVEL_DOMINANTE'].isin(combustiveis)
].copy()

# padrões locação
idc, valc = df_padroes.columns[0], df_padroes.columns[1]
df_padroes.rename(columns={idc:'PADRAO', valc:'CUSTO_LOCACAO_PADRAO'}, inplace=True)
df_padroes['CUSTO_LOCACAO_PADRAO'] = df_padroes['CUSTO_LOCACAO_PADRAO'].apply(parse_currency)
df_frota = df_frota.merge(df_padroes[['PADRAO','CUSTO_LOCACAO_PADRAO']], on='PADRAO', how='left')
mask_loc = df_frota['Frota'].str.upper()=='LOCADO'
df_frota['CUSTO_PADRAO_MENSAL'] = 0.0
df_frota.loc[mask_loc,'CUSTO_PADRAO_MENSAL'] = df_frota.loc[mask_loc,'CUSTO_LOCACAO_PADRAO']
if 'CUSTO_LOCACAO_PADRAO' in df_frota.columns: df_frota.drop(columns=['CUSTO_LOCACAO_PADRAO'], inplace=True)

# merge final com frota
merge_cols = ['PLACA','OPM','Frota','PADRAO','CARACTERIZACAO','CUSTO_PADRAO_MENSAL']
df = df.merge(df_frota[merge_cols], on='PLACA', how='left')
df.fillna({'Frota':'NÃO LOCALIZADO','PADRAO':'N/D','CARACTERIZACAO':'N/D'}, inplace=True)
df['Nº de frotas abastecidas'] = df.groupby('PLACA')['UNIDADE'].transform('nunique')

# ---------- Criação de abas ----------
t1, t2, t3, t4 = st.tabs([
    '🔎 Visão Geral','🚘 Frota por OPM','📍 OPMs & Municípios','📋 Detalhamento'
])

# -------- VISÃO GERAL --------
with t1:
    st.subheader('✨ Indicadores Principais')
    veh = df['PLACA'].nunique()
    lit = df['TOTAL_LITROS'].sum()
    val = df['VALOR_TOTAL'].sum()
    avg_l = df.groupby('PLACA')['TOTAL_LITROS'].sum().mean()
    avg_v = df.groupby('PLACA')['VALOR_TOTAL'].sum().mean()
    c = st.columns(6)
    c[0].metric('Registros',f'{len(df):,}')
    c[1].metric('Viaturas',f'{veh}')
    c[2].metric('Total Litros',f'{truncar(lit):,.2f} L')
    c[3].metric('Total Gasto (R$)',f'R$ {truncar(val):,.2f}')
    c[4].metric('Média Litros/Viatura',f'{truncar(avg_l):,.2f} L')
    c[5].metric('Média Gasto/Viatura',f'R$ {truncar(avg_v):,.2f}')

    st.divider()
    # Consumo por Unidade
    consumo_unidade = df.groupby('UNIDADE')['TOTAL_LITROS'].sum().reset_index()
    fig_litros = px.bar(
        consumo_unidade.sort_values('TOTAL_LITROS', ascending=False),
        x='TOTAL_LITROS', y='UNIDADE', orientation='h',
        labels={'TOTAL_LITROS': 'Litros', 'UNIDADE': 'Unidade'},
        title='Consumo por Unidade (Litros)'
    )
    st.plotly_chart(fig_litros, use_container_width=True)

    # Gasto por Unidade
    gasto_unidade = df.groupby('UNIDADE')['VALOR_TOTAL'].sum().reset_index()
    fig_valor = px.bar(
        gasto_unidade.sort_values('VALOR_TOTAL', ascending=False),
        x='VALOR_TOTAL', y='UNIDADE', orientation='h',
        labels={'VALOR_TOTAL': 'Valor R$', 'UNIDADE': 'Unidade'},
        title='Gasto por Unidade (R$)'
    )
    st.plotly_chart(fig_valor, use_container_width=True)

    st.divider()
    st.subheader('🚗 Top 20 Viaturas por Consumo (Litros)')
    top20_litros = df.groupby('PLACA').agg(
        Litros=('TOTAL_LITROS', 'sum'),
        Valor=('VALOR_TOTAL', 'sum'),
        Unidade=('UNIDADE', 'first')
    ).reset_index().sort_values('Litros', ascending=False).head(20)
    top20_litros['Litros'] = top20_litros['Litros'].apply(truncar).map(lambda x: f"{x:,.2f}")
    top20_litros['Valor'] = top20_litros['Valor'].apply(truncar).map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(top20_litros[['PLACA', 'Unidade', 'Litros', 'Valor']].fillna('NÃO LOCALIZADO'), use_container_width=True)

    st.divider()
    st.subheader('🚗 Top 20 Viaturas por Valor Gasto (R$)')
    top20_valor = df.groupby('PLACA').agg(
        Litros=('TOTAL_LITROS', 'sum'),
        Valor=('VALOR_TOTAL', 'sum'),
        Unidade=('UNIDADE', 'first')
    ).reset_index().sort_values('Valor', ascending=False).head(20)
    top20_valor['Litros'] = top20_valor['Litros'].apply(truncar).map(lambda x: f"{x:,.2f}")
    top20_valor['Valor'] = top20_valor['Valor'].apply(truncar).map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(top20_valor[['PLACA', 'Unidade', 'Litros', 'Valor']].fillna('NÃO LOCALIZADO'), use_container_width=True)

# -------- FROTA POR OPM --------
with t2:
    st.subheader('🚘 Frota por OPM')
    frota_opm = df_frota.groupby(['OPM', 'Frota']).agg(
        Qtde=('PLACA', 'nunique')
    ).reset_index()
    frota_pivot = frota_opm.pivot(index='OPM', columns='Frota', values='Qtde').fillna(0).astype(int)
    frota_pivot['TOTAL'] = frota_pivot.sum(axis=1)
    st.dataframe(frota_pivot.reset_index().fillna('NÃO LOCALIZADO'), use_container_width=True)

    st.divider()
    st.subheader('📋 Caracterização da Frota por OPM')
    char_opm = df_frota.groupby(['OPM', 'CARACTERIZACAO']).agg(
        Qtde=('PLACA', 'nunique')
    ).reset_index()
    char_pivot = char_opm.pivot(index='OPM', columns='CARACTERIZACAO', values='Qtde').fillna(0).astype(int)
    char_pivot['TOTAL'] = char_pivot.sum(axis=1)
    st.dataframe(char_pivot.reset_index().fillna('NÃO LOCALIZADO'), use_container_width=True)

    st.divider()
    st.subheader('🌳 Visualização Frota por OPM')
    frota_treemap = frota_pivot.reset_index()[['OPM', 'TOTAL']]
    fig_tree = px.treemap(frota_treemap, path=['OPM'], values='TOTAL',
        title='Distribuição Visual da Frota por OPM')
    st.plotly_chart(fig_tree, use_container_width=True)

# -------- OPMs & MUNICÍPIOS --------
with t3:
    st.subheader('📍 OPMs & Municípios')
    df_opm.rename(columns={'MUNICÍPIO':'MUNICIPIO', 'MUNICÍPIO_REFERÊNCIA':'MUNICIPIO_REFERENCIA'}, inplace=True)
    df_opm['TIPO_NORM'] = df_opm['TIPO_LOCAL'].apply(lambda x: normalize_text(x).lower() if pd.notna(x) else '')
    df_opm['MUNI_NORM'] = df_opm['MUNICIPIO'].apply(lambda x: normalize_text(x).upper() if pd.notna(x) else '')
    df_opm['MUNI_REF_NORM'] = df_opm['MUNICIPIO_REFERENCIA'].apply(lambda x: normalize_text(x).upper() if pd.notna(x) else '')
    interior = df_opm[(df_opm['TIPO_NORM']=='municipio') & (df_opm['MUNI_NORM']!='MACEIO')]
    muni = interior.groupby('UNIDADE')['MUNICIPIO'].nunique().reset_index(name='Municípios')
    muni.rename(columns={'UNIDADE':'OPM'},inplace=True)
    bairros = df_opm[(df_opm['TIPO_NORM']=='bairro') & (df_opm['MUNI_REF_NORM']=='MACEIO')]
    bair = bairros.groupby('UNIDADE')['LOCAL'].nunique().reset_index(name='Bairros')
    bair.rename(columns={'UNIDADE':'OPM'},inplace=True)
    vehs = df_frota.groupby('OPM')['PLACA'].nunique().reset_index(name='Viaturas')
    summary = vehs.merge(muni,on='OPM',how='left').merge(bair,on='OPM',how='left')
    summary[['Municípios','Bairros']] = summary[['Municípios','Bairros']].fillna(0).astype(int)
    summary['Vtr/Município'] = (summary['Viaturas']/summary['Municípios']).replace(np.inf,0).round(2)
    summary['Vtr/Bairro'] = (summary['Viaturas']/summary['Bairros']).replace(np.inf,0).round(2)
    st.dataframe(summary.fillna('NÃO LOCALIZADO'),use_container_width=True)

    st.divider()
    st.subheader('📈 Múltiplas Sugestões de Redistribuição')

    valid = summary[summary['Municípios']>0].copy()
    if valid.empty:
        st.write('Não há dados suficientes para sugestão.')
    else:
        valid['Dif'] = valid['Vtr/Município'] - valid['Vtr/Município'].mean()
        st.markdown(f"- Média Vtr/Município: **{truncar(valid['Vtr/Município'].mean()):.2f}**")

        # SUGESTÃO 1: Todos acima para todos abaixo da média
        acima = valid[valid['Dif'] > 0].sort_values('Dif', ascending=False)
        abaixo = valid[valid['Dif'] < 0].sort_values('Dif')
        transferencias = []
        for idx_b, row_b in abaixo.iterrows():
            diff_abaixo = abs(row_b['Dif'])
            for idx_a, row_a in acima.iterrows():
                diff_acima = acima.at[idx_a, 'Dif']
                if diff_acima > 0 and diff_abaixo > 0:
                    mover = int(min(diff_acima, diff_abaixo))
                    if mover > 0:
                        transferencias.append(
                            f"→ Sugerido transferir **{mover} viatura(s)** de **{row_a['OPM']}** para **{row_b['OPM']}**."
                        )
                        acima.at[idx_a, 'Dif'] -= mover
                        valid.at[idx_b, 'Dif'] += mover
                        diff_abaixo -= mover
        if transferencias:
            for t in transferencias:
                st.markdown(t)
        else:
            st.info('Nenhuma transferência adicional sugerida além do ajuste médio.')

        st.divider()
        # SUGESTÃO 2: Quem está acima/abaixo da média
        st.markdown("#### 📝 Resumo Viaturas por OPM (Município)")
        resumo = valid[['OPM', 'Viaturas', 'Municípios', 'Vtr/Município', 'Dif']].copy()
        resumo['Situação'] = np.where(resumo['Dif'] > 0, 'Acima da média', 'Abaixo da média')
        st.dataframe(resumo.sort_values('Dif', ascending=False).fillna('NÃO LOCALIZADO'), use_container_width=True)

        # SUGESTÃO 3: Cobertura menor que 1 viatura por município
        st.markdown("#### 🛑 OPMs com menos de 1 viatura por município:")
        crit_mun = resumo[(resumo['Municípios'] > 0) & (resumo['Vtr/Município'] < 1)]
        if crit_mun.empty:
            st.write("Nenhuma OPM com cobertura inferior a 1 viatura por município.")
        else:
            st.dataframe(crit_mun[['OPM','Municípios','Viaturas','Vtr/Município']].fillna('NÃO LOCALIZADO'), use_container_width=True)

    # SUGESTÃO 4: Análise por bairros (somente para OPMs de MACEIO)
    st.divider()
    st.markdown("#### 📝 Resumo Viaturas por OPM (Bairros de Maceió)")
    resumo_bairros = summary[summary['Bairros'] > 0].copy()
    resumo_bairros['Dif_bairro'] = resumo_bairros['Vtr/Bairro'] - resumo_bairros['Vtr/Bairro'].mean()
    resumo_bairros['Situação'] = np.where(resumo_bairros['Dif_bairro'] > 0, 'Acima da média', 'Abaixo da média')
    st.dataframe(resumo_bairros[['OPM', 'Viaturas', 'Bairros', 'Vtr/Bairro', 'Dif_bairro', 'Situação']].sort_values('Dif_bairro', ascending=False).fillna('NÃO LOCALIZADO'), use_container_width=True)

    st.markdown("#### 🛑 OPMs com menos de 1 viatura por bairro:")
    crit_bairro = resumo_bairros[(resumo_bairros['Bairros'] > 0) & (resumo_bairros['Vtr/Bairro'] < 1)]
    if crit_bairro.empty:
        st.write("Nenhuma OPM com cobertura inferior a 1 viatura por bairro.")
    else:
        st.dataframe(crit_bairro[['OPM','Bairros','Viaturas','Vtr/Bairro']].fillna('NÃO LOCALIZADO'), use_container_width=True)

    # DOWNLOAD
    st.divider()
    st.markdown("#### ⬇️ Baixar Resumo de Viaturas por OPM")
    resumo_csv = resumo.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar CSV Municípios", data=resumo_csv, file_name="redistribuicao_opm_municipios.csv", mime='text/csv')

    resumo_bairros_csv = resumo_bairros.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar CSV Bairros", data=resumo_bairros_csv, file_name="redistribuicao_opm_bairros.csv", mime='text/csv')

# -------- DETALHAMENTO --------
with t4:
    st.subheader('📋 Tabela Final Detalhada')
    disp_full = df.rename(columns={
        'OPM':'CARGA',
        'UNIDADE':'OPM ABASTECIMENTO',
        'COMBUSTIVEL_DOMINANTE':'Combustível',
        'TOTAL_LITROS':'Litros',
        'VALOR_TOTAL':'Valor R$',
        'PADRAO':'Padrão',
        'CARACTERIZACAO':'Caracterização',
        'Nº de frotas abastecidas':'Nº de frotas abastecidas'
    })[[
        'PLACA','CARGA','OPM ABASTECIMENTO','Combustível','Litros','Valor R$','Frota','Padrão','Caracterização','Nº de frotas abastecidas'
    ]]
    for col in ['Litros','Valor R$']:
        disp_full[col] = disp_full[col].apply(truncar).map(lambda x: f"{x:,.2f}")
    st.dataframe(disp_full.fillna('NÃO LOCALIZADO'), use_container_width=True, height=500)

    st.divider()
    st.subheader('🔄 Viaturas Abastecendo em Múltiplas OPMs')
    multi_opm = df.groupby('PLACA')['UNIDADE'].nunique().reset_index()
    multi_opm = multi_opm[multi_opm['UNIDADE'] > 1]
    if not multi_opm.empty:
        multi_frotas = df[df['PLACA'].isin(multi_opm['PLACA'])]
        table_multi = multi_frotas.groupby('PLACA').agg(
            OPMs=('UNIDADE', lambda x: ', '.join(sorted(set(x))))
        ).reset_index()
        st.dataframe(table_multi, use_container_width=True)
    else:
        st.info('Nenhuma viatura abasteceu em mais de uma OPM no período filtrado.')

    st.divider()
    st.subheader('🏆 Ranking Geral das Viaturas')
    rank_geral = df.groupby('PLACA').agg(
        Litros=('Litros', lambda x: x.sum() if np.issubdtype(x.dtype, np.number) else 0),
        Valor=('Valor R$', lambda x: x.sum() if np.issubdtype(x.dtype, np.number) else 0),
        OPM=('CARGA', 'first')
    ).reset_index().sort_values('Litros', ascending=False)
    rank_geral['Posição'] = range(1, len(rank_geral)+1)
    rank_geral['Litros'] = pd.to_numeric(rank_geral['Litros'], errors='coerce').fillna(0).apply(truncar).map(lambda x: f"{x:,.2f}")
    rank_geral['Valor'] = pd.to_numeric(rank_geral['Valor'], errors='coerce').fillna(0).apply(truncar).map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(rank_geral[['Posição','PLACA','OPM','Litros','Valor']].fillna('NÃO LOCALIZADO'), use_container_width=True)

st.info('🔧 Ajuste filtros conforme necessário.')
