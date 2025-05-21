import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk

# Função principal
def main():
    # Configuração da página
    st.set_page_config(
        page_title="Dashboard PMAL - Combustível",
        page_icon="⛽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Título
    st.title("📊 Dashboard Online de Combustível PMAL")
    st.markdown("Ferramenta 100% online para análise e monitoramento de consumo de combustível da frota.")

    # Sidebar: uploads e filtros
    st.sidebar.header("📥 Upload de Arquivos")
    file_abast = st.sidebar.file_uploader("Abastecimentos Consolidados (Excel)", type=["xlsx"], key="abast")
    file_frota = st.sidebar.file_uploader("Frota Master Enriched (Excel)", type=["xlsx"], key="frota")
    file_opm = st.sidebar.file_uploader("OPM Municípios Enriched (Excel)", type=["xlsx"], key="opm")

    if not file_abast or not file_frota or not file_opm:
        st.sidebar.warning("Faça upload de todos os três arquivos para visualizar o dashboard.")
        return

    @st.cache_data(ttl=3600)
    def load_data(abast, frota, opm):
        ab = pd.read_excel(abast)
        fr = pd.read_excel(frota)
        op = pd.read_excel(opm)
        # Padronizar placas
        ab['Placa'] = ab['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)
        fr['Placa'] = fr['Placa'].astype(str).str.upper().str.replace('[^A-Z0-9]', '', regex=True)
        # Unir dados
        df = ab.merge(fr, on='Placa', how='left')
        df = df.merge(op[['OPM','Latitude','Longitude']], on='OPM', how='left')
        # Data
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'])
        else:
            for c in df.columns:
                if 'data' in c.lower():
                    df['Data'] = pd.to_datetime(df[c])
                    break
        return df

    df = load_data(file_abast, file_frota, file_opm)

    # Filtros
    st.sidebar.header("📅 Filtros de Período e OPM")
    min_date, max_date = df['Data'].min(), df['Data'].max()
    data_selec = st.sidebar.date_input(
        "Período de Abastecimento", [min_date, max_date],
        min_value=min_date, max_value=max_date
    )
    df = df[(df['Data'] >= pd.to_datetime(data_selec[0])) & (df['Data'] <= pd.to_datetime(data_selec[1]))]
    opms = df['OPM'].unique().tolist()
    sel_opm = st.sidebar.multiselect("Selecione OPM(s)", opms, default=opms)
    df = df[df['OPM'].isin(sel_opm)]

    # Layout por abas
    tab1, tab2, tab3, tab4 = st.tabs(["✅ Visão Geral","⏳ Série Temporal","🗺️ Geoespacial","🚨 Anomalias"])

    with tab1:
        st.subheader("KPIs Principais")
        total_l = df[['Gasolina (Lts)','Álcool (Lts)','Diesel (Lts)','Diesel S10 (Lts)']].sum().sum()
        total_custo = df['Custo'].sum() if 'Custo' in df.columns else np.nan
        media_viatura = df.groupby('Placa')[['Gasolina (Lts)','Álcool (Lts)','Diesel (Lts)','Diesel S10 (Lts)']].sum().mean().sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Litros (L)", f"{total_l:,.0f}")
        c2.metric("Total Gasto (R$)", f"R$ {total_custo:,.2f}")
        c3.metric("Média por Viatura (L)", f"{media_viatura:,.1f}")
        st.divider()
        st.subheader("Distribuição de Combustíveis")
        df_kpi = df[['Gasolina (Lts)','Álcool (Lts)','Diesel (Lts)','Diesel S10 (Lts)']].sum().reset_index().rename(columns={'index':'Combustível', 0:'Litros'})
        fig = px.pie(df_kpi, names='Combustível', values='Litros', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Consumo Mensal")
        df_m = df.groupby(pd.Grouper(key='Data', freq='M'))[['Gasolina (Lts)','Álcool (Lts)','Diesel (Lts)','Diesel S10 (Lts)']].sum().reset_index()
        fig2 = px.line(df_m, x='Data', y=df_m.columns[1:], markers=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("*Passe o mouse sobre as linhas para detalhes*")

    with tab3:
        st.subheader("Mapa de Heatmap por OPM")
        midpoint = (float(df['Latitude'].mean()), float(df['Longitude'].mean()))
        deck = pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=6),
            layers=[
                pdk.Layer(
                    'HeatmapLayer',
                    data=df,
                    get_position='[Longitude, Latitude]',
                    radius=20000,
                    opacity=0.6,
                )
            ],
        )
        st.pydeck_chart(deck)

    with tab4:
        st.subheader("Anomalias de Consumo")
        df['Total_L'] = df[['Gasolina (Lts)','Álcool (Lts)','Diesel (Lts)','Diesel S10 (Lts)']].sum(axis=1)
        z = (df['Total_L'] - df['Total_L'].mean()) / df['Total_L'].std()
        df['Anomalia'] = z.abs() > 2
        anomal = df[df['Anomalia']]
        st.metric("Total Registros", len(df), delta=f"{len(anomal)} anomalias detectadas")
        st.dataframe(anomal.sort_values('Total_L', ascending=False), use_container_width=True)

    # Efeitos Visuais
    if st.sidebar.button("🎉 Celebrar Resultados"):
        st.balloons()

    st.markdown("---")
    st.markdown("_Dashboard desenvolvido por sua equipe de TI, 100% online e interativo._")

# Entrada do script
if __name__ == '__main__':
    main()
