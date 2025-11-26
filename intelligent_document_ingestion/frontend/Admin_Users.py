import streamlit as st
if st.session_state.get("role") != "admin":
    st.error("⛔ Unauthorized — Admin access only")
    st.stop()
