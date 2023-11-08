from typing import List

import streamlit as st
from streamlit.type_util import LabelVisibility


def status_filter(
    status: List[str],
    sidebar: bool = False,
    name: str = "status_filter",
    placeholder: str = "Choose an option",
    name_visibility: LabelVisibility = "visible",
):
    if sidebar:
        holder = st.sidebar
    else:
        holder = st

    selected_status = holder.multiselect(
        label=name,
        options=status,
        placeholder=placeholder,
        label_visibility=name_visibility,
    )

    return selected_status
