import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from urllib.parse import urlparse

# Constrói URLs raw do GitHub
def build_raw_url(repo_url: str, filename: str) -> str:
    url = repo_url.rstrip('/').rstrip('.git')
    parts = urlparse(url).path.strip('/').split('/')
    if len(parts) != 2:
        raise ValueError("URL inválida. Deve ser https://github.com/usuario/repositorio")
    user, repo = parts
    return f"https://raw.githubusercontent.com/{user}/{repo}/main/{filename}"

@st.cache_data(ttl=3600)
def load_data(repo_url: str) -> pd.DataFrame:
    files = {
        'abast': 'Abastecimentos_Consolidados.xlsx',
        'frota': 'Frota_Master_Enriched.xlsx',
        'opm':   'OPM_Municipios_Enriched.xlsx'
    }
    try:
        url_abast = build_raw_url(repo_url, files['abast'])
        url_frota = build_raw_url(repo_url, files['frota'])
        url_opm   = build_raw_url(repo_url, files['opm'])
        ab = pd.read_excel(url_abast)
        fr = pd.read_excel(url_frota)
        op = pd.read_excel(url_opm)
    except Exception as e:
        st.error(f"Falha ao carregar os arquivos do GitHub: {e}")
        st.stop()

    # Detecta e padroniza placa
    def detect_and_clean_plate(df: pd.DataFrame) -> pd.DataFrame:
        placa_col = next((c for c in df.columns if 'placa' in c.lower()), None)
        if placa_col is None:
            raise KeyError("Não foi encontrada coluna de placa.")
        df = df.rename(columns={placa_col: 'Placa'})
        df['Placa'] = df['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)
        return df

    ab = detect_and_clean_plate(ab)
    fr = detect_and_clean_plate(fr)

    # Une abastecimentos e frota
    df = ab.merge(fr, on='Placa', how='left')

    # Detecta colunas de OPM, latitude e longitude
    opm_col = next((c for c in op.columns if 'opm' in c.lower()), None)
    lat_col = next((c for c in op.columns if 'lat' in c.lower()), None)
    lon_col = next((c for c in op.columns if 'lon' in c.lower()), None)
    if not opm_col or not lat_col or not lon_col:
        raise KeyError("Arquivo de OPM precisa ter colunas de OPM, latitude e longitude.")
    op = op.rename(columns={opm_col: 'OPM', lat_col: 'Latitude', lon_col: 'Longitude'})
    df = df.merge(op[['OPM', 'Latitude', 'Longitude']], on='OPM', how='left')

    # Detecta coluna de data
    date_col = next((c for c in df.columns if 'data' in c.lower()), None)
    if date_col is None:
        raise KeyError("Não foi encontrada coluna de data.")
    df['Data'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['Data'])
    return df

# Função principal
def main():
    st.set_page_config(
        page_title="Dashboard PMAL - Combustível",
        page_icon="⛽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.sidebar.header("Configuração")
    repo_url = st.sidebar.text_input(
        "🔗 URL do repositório GitHub:",
        value="https://github.com/DLOG2025/Dashboard"
    )
    if not repo_url:
        st.sidebar.warning("Informe a URL do seu repositório GitHub.")
        return

    df = load_data(repo_url)

    # Filtros de data e OPM
    st.sidebar.header("Filtros")
    min_date, max_date = df['Data'].min(), df['Data'].max()
    data_selec = st.sidebar.date_input(
        "Período de Abastecimento", [min_date, max_date],
        min_value=min_date, max_value=max_date
    )
    df = df[(df['Data'] >= pd.to_datetime(data_selec[0])) & (df['Data'] <= pd.to_datetime(data_selec[1]))]

    opms = sorted(df['OPM'].dropna().unique())
    sel_opm = st.sidebar.multiselect("Selecione OPM(s)", opms, default=opms)
    df = df[df['OPM'].isin(sel_opm)]

    # Abas do dashboard
    tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Série Temporal", "Geoespacial", "Anomalias"])
    # Identifica colunas de volume de combustível
    sum_cols = [c for c in df.columns if any(x in c.lower() for x in ['gasolina','álcool','alcool','diesel'])]

    with tab1:
        st.subheader("KPIs Principais")
        total_l = df[sum_cols].sum().sum()
        total_custo = df['Custo'].sum() if 'Custo' in df.columns else np.nan
        media_viatura = df.groupby('Placa')[sum_cols].sum().mean().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Litros (L)", f"{total_l:,.0f}")
        c2.metric("Total Gasto (R$)", f"R$ {total_custo:,.2f}")
        c3.metric("Média por Viatura (L)", f"{media_viatura:,.1f}")
        st.divider()
        st.subheader("Distribuição de Combustíveis")
        df_kpi = df[sum_cols].sum().reset_index().rename(columns={'index': 'Combustível', 0: 'Litros'})
        st.plotly_chart(px.pie(df_kpi, names='Combustível', values='Litros', hole=0.4), use_container_width=True)

    with tab2:
        st.subheader("Consumo Mensal")
        df_m = df.groupby(pd.Grouper(key='Data', freq='M'))[sum_cols].sum().reset_index()
        st.plotly_chart(px.line(df_m, x='Data', y=sum_cols, markers=True), use_container_width=True)

    with tab3:
        st.subheader("Mapa de Heatmap por OPM")
        midpoint = (df['Latitude'].mean(), df['Longitude'].mean())
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=6),
            layers=[pdk.Layer('HeatmapLayer', data=df, get_position='[Longitude, Latitude]', radius=20000, opacity=0.6)]
        ))

    with tab4:
        st.subheader("Anomalias de Consumo")
        df['Total_L'] = df[sum_cols].sum(axis=1)
        z = (df['Total_L'] - df['Total_L'].mean()) / df['Total_L'].std()
        anomal = df[z.abs() > 2]
        st.metric("Total Registros", len(df), delta=f"{len(anomal)} anomalias detectadas")
        st.dataframe(anomal.sort_values('Total_L', ascending=False), use_container_width=True)

    if st.sidebar.button("🎉 Balões"):
        st.balloons()

    st.markdown("---")
    st.markdown("_Dashboard 100% online, sem uploads manuais._")

# Executa o app
if __name__ == '__main__':
    main()
