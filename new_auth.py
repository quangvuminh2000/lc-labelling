import streamlit as st
import streamlit_authenticator as stauth

import yaml
from yaml.loader import SafeLoader

# ? CONSTANTS
CONFIG_DATA_PATH_LOCAL = "./data/auth.csv"
CONFIG_DATA_PATH_GCS = "lc_labelling_bucket/auth/auth.csv"
CONFIG_PATH_LOCAL = "./config/auth.yaml"
CONFIG_PATH_GCS = "lc_labelling_bucket/auth/auth.yaml"

# * IMPORT CONFIGS
with open(CONFIG_PATH_LOCAL) as file:
    config = yaml.load(file, Loader=SafeLoader)


# ? II. LOGIN
def login_form(authenticator: stauth.Authenticate):
    authenticator.login("LOGIN", "main")

    if st.session_state["authentication_status"] is False:
        if authenticator.username == "":
            st.warning("Please enter your username and password", icon="⚠️")
        else:
            st.error("Username/password is incorrect", icon="🔒")


# * LOGGING IN
def authentication_component():
    print("AUTH")
    # * CREATE AUTHENTICATOR OBJECT
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        config["preauthorized"],
    )

    # * LOGIN SUCCESSFULLY
    login_form(authenticator)

    st.markdown(
        """
        <style>
        #login{
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .st-emotion-cache-r421ms.e10yg2by1{
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .st-emotion-cache-7ym5gk.ef3psqc7{
            width: -webkit-fill-available;
            background-color: #B9D4EB;
            margin-top: 30px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .block-container.st-emotion-cache-1y4p8pa.ea3mdgi4{
            width: 450px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("authentication_status", None):
        st.sidebar.write(f"Welcome **{st.session_state['name']}**")
        authenticator.logout("Logout", "sidebar", key="logout_btn")


if __name__ == "__main__":
    authentication_component()
