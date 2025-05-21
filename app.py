import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(
    page_title="Dashboard PMAL - Combustível",
    layout="wide"
)

@st.cache_data(ttl=3600)
def load_data():
    # Carrega apenas colunas essenciais para um dashboard leve
    df = pd.read_excel(
        "Abastecimentos_Consolidados.xlsx",
        usecols=["Placa","Unidade","TOTAL_LITROS","VALOR_TOTAL","Data"]
    )
    df.columns = df.columns.str.upper()
    df = df.rename(columns={
        "PLACA": "Placa",
        "UNIDADE": "OPM",
        "TOTAL_LITROS": "Litros",
        "VALOR_TOTAL": "Custo",
        "DATA": "Data"
    })
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df["Litros"] = pd.to_numeric(df["Litros"], errors="coerce").fillna(0)
    df["Custo"]  = pd.to_numeric(df["Custo"],  errors="coerce").fillna(0)
    return df

# Função principal
def main():
    st.title("📊 Dashboard Simples PMAL – Combustível")

    # Carrega dados
    df = load_data()

    # Sidebar: filtro de período
    st.sidebar.header("Filtros")
    min_date, max_date = df["Data"].min(), df["Data"].max()
    date_range = st.sidebar.date_input(
        "Período", [min_date, max_date], min_value=min_date, max_value=max_date
    )
    df = df[(df["Data"] >= pd.to_datetime(date_range[0])) & (df["Data"] <= pd.to_datetime(date_range[1]))]

    # KPIs básicos
    st.header("✅ KPIs")
    total_l = df["Litros"].sum()
    total_c = df["Custo"].sum()
    unique_veic = df["Placa"].nunique()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Litros (L)", f"{total_l:,.0f}")
    col2.metric("Total Gasto (R$)", f"R$ {total_c:,.2f}")
    col3.metric("Viaturas Únicas", unique_veic)

    # Consumo mensal simplificado
    st.header("📈 Consumo Mensal")
    monthly = (
        df.set_index("Data")["Litros"]
          .resample("M")
          .sum()
          .reset_index()
    )
    fig = px.line(monthly, x="Data", y="Litros", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # Tabela de amostra dos dados
    st.header("📋 Amostra de Dados")
    st.dataframe(df.head(10), use_container_width=True)

if __name__ == "__main__":
    main()
