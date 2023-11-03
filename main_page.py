import streamlit as st

from auth import authentication_component
from label_page import labelling_component

from pprint import pprint

if __name__ == "__main__":
    # st.set_page_config(
    #     layout="wide",
    #     page_title="Long Châu Labelling Tool",
    #     initial_sidebar_state="collapsed",
    # )

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
            .block-container.st-emotion-cache-z5fcl4.ea3mdgi4{
                width: 40%;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # pprint(st.session_state.to_dict())
    if st.session_state.get("authentication_state", None):
        labelling_component()
    authentication_component()
