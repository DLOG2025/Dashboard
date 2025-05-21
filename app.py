import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from urllib.parse import urlparse

# Constrói URLs raw do GitHub para dois arquivos
def build_raw_url(repo_url: str, filename: str) -> str:
    url = repo_url.rstrip('/').rstrip('.git')
    parts = urlparse(url).path.strip('/').split('/')
    if len(parts) != 2:
        raise ValueError("URL inválida. Deve ser https://github.com/usuario/repositorio")
    user, repo = parts
    return f"https://raw.githubusercontent.com/{user}/{repo}/main/{filename}"

@st.cache_data(ttl=3600)
def load_data(repo_url: str) -> pd.DataFrame:
    # Nomes dos arquivos no repositório
    files = {
        'abast': 'Abastecimentos_Consolidados.xlsx',
        'frota': 'Frota_Master_Enriched.xlsx'
    }
    try:
        url_abast = build_raw_url(repo_url, files['abast'])
        url_frota = build_raw_url(repo_url, files['frota'])
        ab = pd.read_excel(url_abast)
        fr = pd.read_excel(url_frota)
    except Exception as e:
        st.error(f"Falha ao carregar arquivos: {e}")
        st.stop()

    # Padroniza coluna de placa
    def detect_plate(df):
        col = next((c for c in df.columns if 'placa' in c.lower()), None)
        if not col:
            raise KeyError("Não foi encontrada coluna de placa.")
        df = df.rename(columns={col: 'Placa'})
        df['Placa'] = df['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)
        return df

    ab = detect_plate(ab)
    fr = detect_plate(fr)

    # Merge de abastecimentos e frota
    df = ab.merge(fr, on='Placa', how='left')

    # Detecta coluna de data
    date_col = next((c for c in df.columns if 'data' in c.lower()), None)
    if not date_col:
        st.error("Não foi encontrada coluna de data.")
        st.stop()
    df['Data'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['Data'])

    # Normaliza litros e custo
    if 'TOTAL_LITROS' in df.columns:
        df['Litros'] = df['TOTAL_LITROS']
    else:
        df['Litros'] = df.filter(like='Lts').sum(axis=1)
    if 'VALOR_TOTAL' in df.columns:
        df['Custo'] = df['VALOR_TOTAL']
    elif 'Custo' in df.columns:
        df['Custo'] = df['Custo']
    else:
        df['Custo'] = 0
    return df

# Função principal
def main():
    st.set_page_config(page_title="Dashboard PMAL - Combustível", page_icon="⛽️", layout="wide")
    st.title("📊 Dashboard Online - Consumo de Combustível PMAL")

    repo_url = st.sidebar.text_input("🔗 URL do repositório GitHub com os arquivos:",
                                   "https://github.com/DLOG2025/Dashboard")
    if not repo_url:
        st.sidebar.warning("Informe a URL do repositório GitHub.")
        return

    df = load_data(repo_url)

    # Filtros de data
    st.sidebar.header("Filtros")
    min_date, max_date = df['Data'].min(), df['Data'].max()
    sel_dates = st.sidebar.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)
    df = df[(df['Data'] >= pd.to_datetime(sel_dates[0])) & (df['Data'] <= pd.to_datetime(sel_dates[1]))]

    # Abas do dashboard
    tab1, tab2, tab3 = st.tabs(["Visão Geral", "Série Temporal", "Anomalias"])

    with tab1:
        st.subheader("KPIs Principais")
        total_l = df['Litros'].sum()
        total_c = df['Custo'].sum()
        media_v = df.groupby('Placa')['Litros'].sum().mean()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Litros (L)", f"{total_l:,.0f}")
        c2.metric("Total Gasto (R$)", f"R$ {total_c:,.2f}")
        c3.metric("Média por Viatura (L)", f"{media_v:,.1f}")
        st.divider()
        st.subheader("Distribuição de Litros vs Custo")
        fig = px.scatter(df, x='Litros', y='Custo', hover_data=['Placa'])
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Consumo Mensal")
        monthly = df.groupby(pd.Grouper(key='Data', freq='M')).agg({'Litros':'sum','Custo':'sum'}).reset_index()
        fig2 = px.line(monthly, x='Data', y=['Litros','Custo'], markers=True)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Detecção de Anomalias")
        df['Z'] = (df['Litros'] - df['Litros'].mean())/df['Litros'].std()
        anomal = df[df['Z'].abs() > 2]
        st.metric("Total Registros", len(df), delta=f"{len(anomal)} anomalias")
        st.dataframe(anomal[['Data','Placa','Litros','Custo']], use_container_width=True)

    if st.sidebar.button("🎉 Balões"):
        st.balloons()

    st.markdown("---")
    st.markdown("_Dashboard sem mapeamento, 100% online e simples de usar._")

if __name__ == '__main__':
    main()
