import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Estética Enterprise e Simetria
st.set_page_config(page_title="Control Tower - Atendimento", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp { background-color: #0e1117; color: #ffffff; font-family: 'Roboto', sans-serif; }
    
    /* Scorecards com Altura Fixa e Simetria */
    div[data-testid="stMetric"] { 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        padding: 20px !important; 
        border-radius: 8px;
        min-height: 150px;
        display: flex;
        flex-direction: column;
    }

    div[data-testid="stMetricLabel"] { 
        color: #c9d1d9 !important; 
        font-size: 0.85rem !important; 
        text-transform: uppercase;
        margin-bottom: 12px !important;
        order: -1;
    }

    div[data-testid="stMetric"] > div:nth-child(2) {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 15px !important;
    }

    div[data-testid="stMetricValue"] { 
        color: #ffffff !important; 
        font-size: 2.2rem !important; 
        font-weight: 700 !important;
        line-height: 1 !important;
    }

    div[data-testid="stMetricDelta"] {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.95rem !important;
        margin-top: 0 !important;
    }

    h1, h2, h3 { color: #ffffff !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

try:
    # 2. Conexão e Limpeza de Snapshots (8h, 12h, 17h)
    conn = st.connection("postgresql", type="sql")
    df_raw = conn.query("SELECT * FROM sla_atendimento;", ttl="5m")

    # Tratamento de Tipagem
    df_raw['data_snapshot'] = pd.to_datetime(df_raw['data_snapshot']).dt.date
    df_raw['dias_atraso'] = pd.to_numeric(df_raw['dias_atraso'], errors='coerce').fillna(0).astype(int)

    # LÓGICA DE DEDUPLICAÇÃO: Mantém apenas o registro mais recente (maior ID) de cada card por dia
    # Isso impede que o volume triplique nas métricas diárias
    df = df_raw.sort_values('id', ascending=False).drop_duplicates(subset=['id_card', 'data_snapshot']).copy()

    # 3. Lógica de SLA: 4 dias para Atendimento
    def categorizar_atendimento(dias):
        if dias == 4: return "ALERTA"
        elif dias > 4: return "ATRASADO"
        else: return "OK"
    df['status'] = df['dias_atraso'].apply(categorizar_atendimento)

    st.sidebar.title("Atendimento Intelligence")
    page = st.sidebar.radio("Navegação", ["Operacional (Daily)", "Planejamento (Capacidade)"])
    
    datas_unicas = sorted(df['data_snapshot'].unique(), reverse=True)
    if not datas_unicas: 
        st.info("Aguardando os primeiros dados do n8n na tabela sla_atendimento...")
        st.stop()

    # --- PÁGINA 1: OPERACIONAL ---
    if page == "Operacional (Daily)":
        data_sel = st.sidebar.selectbox("Snapshot do Dia", datas_unicas, index=0)
        df_view = df[df['data_snapshot'] == data_sel]

        delta_val = 0
        if len(datas_unicas) > 1:
            vol_ant = len(df[df['data_snapshot'] == datas_unicas[1]])
            delta_val = len(df_view) - vol_ant

        st.title("Control Tower Atendimento")
        st.write(f"Análise baseada na última atualização disponível para o dia {data_sel.strftime('%d/%m/%Y')}")
        st.write("---")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fila Atendimento", len(df_view), delta=f"{delta_val}", delta_color="inverse")
        perc = df_view['status'].value_counts(normalize=True) * 100
        c2.metric("OK (<4d)", f"{perc.get('OK', 0):.1f}%")
        c3.metric("Alerta (4d)", f"{perc.get('ALERTA', 0):.1f}%")
        c4.metric("Atrasado (>4d)", f"{perc.get('ATRASADO', 0):.1f}%")

        col_l, col_r = st.columns(2, gap="large")
        with col_l:
            st.subheader("Gargalos por Operadora")
            ranking = df_view.groupby('operadora')['dias_atraso'].mean().round(0).astype(int).reset_index()
            ranking = ranking.nlargest(10, 'dias_atraso').sort_values('dias_atraso')
            fig = px.bar(ranking, x='dias_atraso', y='operadora', orientation='h', template="plotly_dark", text='dias_atraso')
            fig.update_traces(marker_color='#58a6ff', textposition='inside')
            fig.update_layout(margin=dict(l=0, r=40, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("Saúde do Fluxo")
            fig_pie = px.pie(df_view, names='status', hole=0.6, template="plotly_dark",
                            color='status', color_discrete_map={'OK': '#238636', 'ALERTA': '#d29922', 'ATRASADO': '#f85149'})
            fig_pie.update_layout(margin=dict(l=40, r=0, t=10, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.write("---")
        st.subheader("Detalhamento de Exceções")
        df_acao = df_view[df_view['status'] != "OK"].sort_values('dias_atraso', ascending=False)
        
        # Inclusão da coluna 'corretora' após 'operadora'
        st.dataframe(df_acao[['nome_empresa', 'operadora', 'corretora', 'fila_atual', 'dias_atraso', 'status']].style.applymap(
            lambda x: 'background-color: #3e1c1c; color: #ff7b72' if x > 4 else ('background-color: #3e331c; color: #d29922' if x == 4 else ''),
            subset=['dias_atraso']
        ), use_container_width=True, hide_index=True)

    # --- PÁGINA 2: PLANEJAMENTO (CAPACIDADE) ---
    elif page == "Planejamento (Capacidade)":
        st.title("Planejamento e Tendências")
        st.write("---")

        opcoes_janela = {"7 dias": 7, "15 dias": 15, "30 dias": 30, "60 dias": 60}
        janela_label = st.sidebar.selectbox("Período de Análise", list(opcoes_janela.keys()), index=2)
        n_dias = opcoes_janela[janela_label]

        df_hist = df[df['data_snapshot'].isin(datas_unicas[:n_dias])]

        st.subheader(f"Evolução de Volume — {janela_label}")
        df_vol = df_hist.groupby('data_snapshot').size().reset_index(name='volume').sort_values('data_snapshot')
        fig_vol = px.area(df_vol, x='data_snapshot', y='volume', template="plotly_dark")
        fig_vol.update_traces(line_color='#58a6ff', fillcolor='rgba(88, 166, 255, 0.2)')
        fig_vol.update_xaxes(tickformat="%d/%m/%Y", dtick="D1", tickangle=0, title="")
        st.plotly_chart(fig_vol, use_container_width=True)

        st.subheader("Eficiência do Atendimento (Média de Dias)")
        df_delay = df_hist.groupby('data_snapshot')['dias_atraso'].mean().reset_index().sort_values('data_snapshot')
        fig_delay = px.line(df_delay, x='data_snapshot', y='dias_atraso', template="plotly_dark", markers=True)
        fig_delay.update_traces(line_color='#f85149')
        fig_delay.update_xaxes(tickformat="%d/%m/%Y", dtick="D1", tickangle=0, title="")
        st.plotly_chart(fig_delay, use_container_width=True)

except Exception as e:
    st.error(f"Erro técnico na conexão: {e}")
