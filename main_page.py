import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="Long Châu Labelling Tool",
    initial_sidebar_state="expanded",
)

from auth import authentication_component
from label_page import labelling_component

if __name__ == "__main__":
    authentication_component()

    labelling_component()

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 3rem;
                padding-bottom: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
                # margin-top: -2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )
