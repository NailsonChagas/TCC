import matplotlib.pyplot as plt
import streamlit as st
from buck_converter import BuckConverterCCM, CCMError

# Configuração da página
st.set_page_config(
    page_title="Simulador Conversor Buck CCM",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("", unsafe_allow_html=True)

# Parâmetros de Projeto
st.markdown("**Parâmetros de Projeto**")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    Vs = st.number_input("Vs [V]", value=50.0, min_value=1.0, step=1.0)
with col2:
    Vo = st.number_input("Vo [V]", value=25.0, min_value=1.0, step=1.0)
with col3:
    Po = st.number_input("Po [W]", value=100.0, min_value=1.0, step=5.0)
with col4:
    delta_iL = st.number_input("ΔiL [A]", value=0.5, min_value=0.001, step=0.01)
with col5:
    delta_Vo = st.number_input("ΔVo [V]", value=0.05, min_value=0.001, step=0.01)
with col6:
    fs = st.number_input("fs [Hz]", value=50000.0, min_value=100.0, step=1000.0)

st.markdown("**Parâmetros de Simulação**")
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    N = st.number_input("N", value=100, min_value=1, step=10, help="fs_sim = N × fs")
with col2:
    sim_time_ms = st.number_input("Tempo [ms]", value=1.0, min_value=0.01, step=0.1)

# Projeto e simulação
try:
    buck = BuckConverterCCM.from_design_parameters(
        Vs=Vs, Vo=Vo, Po=Po, delta_iL=delta_iL, delta_Vo=delta_Vo, fs=fs
    )

    st.success(
        f"**CCM**  |  "
        f"L = {buck.L * 1e6:.2f} µH  |  "
        f"C = {buck.C * 1e6:.2f} µF  |  "
        f"R = {buck.R:.2f} Ω  |  "
        f"D = {buck.D:.3f}"
    )

    sim_time = sim_time_ms / 1000.0
    time, iL, vC = buck.simulate(N=int(N), sim_time=sim_time)

    # Gráficos lado a lado
    col1, col2 = st.columns(2)

    with col1:
        fig1, ax1 = plt.subplots(figsize=(7, 2.7))
        ax1.plot(time * 1e3, iL, linewidth=1.2)
        ax1.set_xlabel("Tempo (ms)")
        ax1.set_ylabel("i_L (A)")
        ax1.set_title("Corrente no Indutor")
        ax1.grid(True, linestyle="--", alpha=0.5)
        fig1.tight_layout()
        st.pyplot(fig1, width="stretch")

    with col2:
        fig2, ax2 = plt.subplots(figsize=(7, 2.7))
        ax2.plot(time * 1e3, vC, linewidth=1.2)
        ax2.set_xlabel("Tempo (ms)")
        ax2.set_ylabel("v_C (V)")
        ax2.set_title("Tensão de Saída")
        ax2.grid(True, linestyle="--", alpha=0.5)
        fig2.tight_layout()
        st.pyplot(fig2, width="stretch")

except CCMError as e:
    st.error(f"**Projeto inválido — operação em DCM detectada**\n\n{e}")

