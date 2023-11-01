import streamlit as st
import streamlit_authenticator as stauth
from st_files_connection import FilesConnection

import yaml
from yaml.loader import SafeLoader

from os import environ as env
from dotenv import load_dotenv
import pandas as pd

from mailer import Mailer

from utils import save_data_gcs

load_dotenv()

# ? CONSTANTS
CONFIG_DATA_PATH_LOCAL = "./data/auth.csv"
CONFIG_DATA_PATH_GCS = "lc_labelling_bucket/auth/auth.csv"
CONFIG_PATH_LOCAL = "./config/auth.yaml"
CONFIG_PATH_GCS = "lc_labelling_bucket/auth/auth.yaml"

# * IMPORT CONFIGS
with open(CONFIG_PATH_LOCAL) as file:
    config = yaml.load(file, Loader=SafeLoader)


# ? HELPERS
def update_config():
    with st.spinner("Saving your profile..."):
        with open(CONFIG_PATH_LOCAL, "w") as file:
            yaml.dump(config, file, default_flow_style=False)
        # ? Save authentication file & auth data
        conn = st.connection("gcs", type=FilesConnection)

        save_data_gcs(CONFIG_PATH_LOCAL, CONFIG_PATH_GCS, conn)

        usernames = list(config["credentials"]["usernames"].keys())
        passwords = [config["credentials"]["usernames"][user]["password"] for user in usernames]
        emails = [config["credentials"]["usernames"][user]["email"] for user in usernames]
        names = [config["credentials"]["usernames"][user]["name"] for user in usernames]

        config_df = pd.DataFrame({
            "username": usernames,
            "email": emails,
            "name": names,
            "password": passwords
        })

        config_df.to_csv(CONFIG_DATA_PATH_LOCAL, index=False)
        save_data_gcs(CONFIG_DATA_PATH_LOCAL, CONFIG_DATA_PATH_GCS, conn)


def send_email(receiver_mail: str, subject: str, message: str):
    mail = Mailer(email=env["ADMIN_EMAIL"], password=env["ADMIN_PASSWORD"])
    mail.send(
        receiver=receiver_mail,
        sender_name="LC-LABELLING-CDP",
        no_reply=True,
        subject=subject,
        message=message,
    )


# * RENDER THE LOGIN WIDGET


# ? II. LOGIN
def login_form(authenticator):
    authenticator.login("Login", "main")

    if st.session_state["authentication_status"] is False:
        if authenticator.username == "":
            st.warning("Please enter your username and password", icon="⚠️")
        else:
            st.error("Username/password is incorrect", icon="🔒")


# ? III. RESET PASSWORD
def reset_password_form(authenticator: stauth.Authenticate):
    try:
        if authenticator.reset_password(
            st.session_state["username"], "Reset password", "sidebar"
        ):
            st.success("Password modified successfully")
            update_config()
    except Exception as e:
        st.error(e)


# ? IV. REGISTER USER
def register_user_form(authenticator: stauth.Authenticate):
    try:
        if authenticator.register_user("Register user", preauthorization=False):
            st.success("User registered successfully")
            update_config()
    except Exception as e:
        st.error(e)


# ? V. FORGOT PASSWORD
def forgot_password_form(authenticator):
    try:
        (
            username_of_forgotten_password,
            email_of_forgotten_password,
            new_random_password,
        ) = authenticator.forgot_password("Forgot password")
        if username_of_forgotten_password:
            new_pwd_message = f"Here is your new password: {new_random_password}, Please sign in and change it as soon as possible"
            send_email(
                receiver_mail=email_of_forgotten_password,
                subject="PASSWORD FORGOTTEN",
                message=new_pwd_message,
            )
            st.success(
                "New password sent successfully to your email, please check your registered email"
            )
            update_config()
        elif username_of_forgotten_password is not None:
            st.error("Username not found")

    except Exception as e:
        st.error(e)


# ? VI. FORGOT USERNAME
def forgot_username_form(authenticator):
    try:
        (
            username_of_forgotten_username,
            email_of_forgotten_username,
        ) = authenticator.forgot_username("Forgot username")
        if username_of_forgotten_username:
            username_message = (
                f"Here is your username: {username_of_forgotten_username}"
            )
            send_email(
                receiver_mail=email_of_forgotten_username,
                subject="USERNAME FORGOTTEN",
                message=username_message,
            )
            st.success(
                "Username sent successfully to your email, please check your registered email"
            )
        elif email_of_forgotten_username != "":
            st.error("Email not found")
    except Exception as e:
        st.error(e)


# ? VII. UPDATE USER DETAILS
def update_user_details(authenticator: stauth.Authenticate):
    if st.session_state["authentication_status"]:
        try:
            if authenticator.update_user_details(
                st.session_state["username"], "Update user details", location="sidebar"
            ):
                st.success("Entries updated successfully")
                update_config()
        except Exception as e:
            st.error(e)


# * LOGGING IN
def authentication_component():
    # * CREATE AUTHENTICATOR OBJECT
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        config["preauthorized"],
    )

    if (not st.session_state["authentication_status"]) and (
        not st.session_state["name"]
    ):
        st.header("Welcome to LC Labelling Tool")
        st.subheader("Please choose one")

        un_auth_page_names_to_funcs = {
            "Sign In": login_form,
            "Sign Up": register_user_form,
            "Forgot Password": forgot_password_form,
            "Forgot Username": forgot_username_form,
        }

        un_auth_page = st.selectbox(
            "Choose one of the following",
            placeholder="Choose your option...",
            label_visibility="hidden",
            options=un_auth_page_names_to_funcs.keys(),
            key="un_auth_selection",
            index=None,
        )

        if un_auth_page:
            un_auth_page_names_to_funcs[un_auth_page](authenticator)

    # * LOGIN SUCCESSFULLY
    if st.session_state["authentication_status"]:
        st.sidebar.write(f"Welcome **{st.session_state['name']}**")
        authenticator.logout("Logout", "sidebar", key="logout_btn")
        auth_page_names_to_funcs = {
            "Reset Password": reset_password_form,
            "Update User Details": update_user_details,
        }

        st.sidebar.subheader("Settings")
        auth_page = st.sidebar.selectbox(
            "Settings",
            placeholder="Choose your option...",
            options=auth_page_names_to_funcs.keys(),
            key="auth_selection",
            index=None,
            label_visibility="collapsed"
        )

        if auth_page:
            auth_page_names_to_funcs[auth_page](authenticator)

        # # ? Save authentication file & auth data
        # conn = st.connection("gcs", type=FilesConnection)

        # save_data_gcs(CONFIG_PATH_LOCAL, CONFIG_PATH_GCS, conn)

        # usernames = list(config["credentials"]["usernames"].keys())
        # passwords = [config["credentials"]["usernames"][user]["password"] for user in usernames]
        # emails = [config["credentials"]["usernames"][user]["email"] for user in usernames]
        # names = [config["credentials"]["usernames"][user]["name"] for user in usernames]

        # config_df = pd.DataFrame({
        #     "username": usernames,
        #     "email": emails,
        #     "name": names,
        #     "password": passwords
        # })

        # config_df.to_csv(CONFIG_DATA_PATH_LOCAL, index=False)
        # save_data_gcs(CONFIG_DATA_PATH_LOCAL, CONFIG_DATA_PATH_GCS, conn)


if __name__ == "__main__":
    authentication_component()
