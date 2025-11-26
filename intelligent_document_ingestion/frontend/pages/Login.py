import streamlit as st
import requests

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

st.title("🔐 Login to Document Portal")


username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if not username or not password:
        st.error("Please enter both username and password")
    else:
        try:
            print("Attempting to log in...")
            res = requests.post(
                "http://localhost:8000/auth/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            print("Login response status:", res.status_code)
            if res.status_code == 200:
                data = res.json()
                st.session_state["access_token"] = data["accessToken"]
                st.session_state["user_id"] = data["userId"]
                st.session_state["role"] = data["role"]

                st.success("Logged in successfully!")
                st.switch_page("streamlit_app.py")
            else:
                st.error(res.json().get("detail", "Login failed"))
        except Exception:
            st.error("Unable to reach backend")


if st.session_state.get("access_token"):
    st.switch_page("streamlit_app.py")
