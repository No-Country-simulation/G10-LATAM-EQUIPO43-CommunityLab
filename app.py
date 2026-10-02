"""Interfaz de curaduría: streamlit run app.py"""
import json

import streamlit as st

from communitylab.agent import procesar

st.set_page_config(page_title="CommunityLab", page_icon="🚀", layout="wide")
st.title("🚀 CommunityLab – Curaduría de contenido")

archivo = st.file_uploader("Sube un JSON de interacciones (o usa el de ejemplo)", type="json")
if archivo:
    payload = json.load(archivo)
else:
    with open("data/sample_input.json", encoding="utf-8") as f:
        payload = json.load(f)

with st.expander("Interacciones de entrada"):
    st.json(payload)

if st.button("⚙️ Procesar comunidad", type="primary"):
    with st.spinner("Analizando y generando activos..."):
        st.session_state["res"] = procesar(payload)
        st.session_state["aprobados"] = set()

res = st.session_state.get("res")
if res:
    r = res["resumen_comunidad"]
    c1, c2 = st.columns(2)
    c1.metric("Interacciones", r["total_interacciones_procesadas"])
    c2.metric("Sentimiento", r["sentimiento_predominante"])
    st.write("**Temas:** " + ", ".join(r["temas_principales"]))
    st.dataframe(res["analisis_detallado"], use_container_width=True)

    st.subheader("Activos generados")
    for nombre, activo in res["activos_distribucion_generados"].items():
        with st.container(border=True):
            st.markdown(f"#### {nombre}")
            for campo, valor in activo.items():
                activo[campo] = st.text_area(campo, valor, key=f"{nombre}-{campo}")
            if st.button("✅ Aprobar", key=f"ok-{nombre}"):
                st.session_state["aprobados"].add(nombre)
            if nombre in st.session_state["aprobados"]:
                st.success("Aprobado")

    o = res["almacenamiento_oci"]
    (st.success if o["status"] == "guardado_con_exito" else st.warning)(
        f"OCI → bucket `{o['bucket']}` / `{o['ruta_objeto']}`: {o['status']}"
    )
