import streamlit as st

from auth import authentication_component
from label_page import labelling_component

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Long Châu Labelling Tool")

    authentication_component()

    labelling_component()
