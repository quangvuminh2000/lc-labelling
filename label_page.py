import streamlit as st
import pandas as pd

import streamlit.components.v1 as components

from st_files_connection import FilesConnection
from st_aggrid import AgGrid, GridUpdateMode, ColumnsAutoSizeMode, DataReturnMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

from streamlit_extras.metric_cards import style_metric_cards

from utils import save_data_gcs, load_data_gcs, get_data_gcs

from components.status_filter import status_filter

TRANSACTION_PATH = "lc_labelling_bucket/cdp/transaction_sample.csv"
OUTPUT_PATH = "lc_labelling_bucket/cdp/tagging_sample.csv"
LABEL_PATH = "lc_labelling_bucket/cdp/labels/total_labels_{}_alpha.csv"
LOCAL_LABEL_PATH = "./data/total_labels_{}_alpha.csv"
PENDING_CUSTOMER_PATH = "lc_labelling_bucket/cdp/labels/pending_{}.csv"
LOCAL_PENDING_CUSTOMER_PATH = "./data/pending_{}.csv"
COLOR_CODES = ["#c5dceb", "#d9d3e8", "#b0ddf1", "#d3ebf5", "#cfe6db", "#fdf2e6"]
IMPORTANCE_COLOR_CODES = {"Cao": "#0285B7", "Trung Bình": "#91C3D4", "Thấp": "#CFDFE6"}
DUOC_SI_COLS = ["duocsi_1", "duocsi_2"]
TOP_LIMIT = 10


def format_color_groups(df):
    x = df.copy()
    factors = list(x["Ngày mua"].unique())
    for i, factor in enumerate(factors):
        style = f"background-color: {COLOR_CODES[i]}"
        x.loc[x["Ngày mua"] == factor, :] = style
    return x


def load_cardcode_label(labeller_name: str):
    try:
        label_data = pd.read_csv(LOCAL_LABEL_PATH.format(labeller_name))
        cardcode_label = label_data["CardCode"].unique()

        return set(cardcode_label)
    except:
        return set()


def select_customer(cardcodes):
    # if len(cardcodes) > TOP_LIMIT:
    #     chosen_cardcodes = list(cardcodes)[:TOP_LIMIT]
    # else:
    #     chosen_cardcodes = cardcodes

    cardcode = st.sidebar.selectbox(
        "Chọn khách hàng",
        cardcodes,
        index=None,
        placeholder="Chọn mã khách hàng...",
        key="customer_selector",
        label_visibility="hidden",
    )

    return cardcode


def load_unlabeled_cardcodes(labeller_name: str, cardcode_total):
    labelled_cardcodes = load_cardcode_label(labeller_name)
    return cardcode_total - labelled_cardcodes


@st.cache_data
def load_all_data(_conn: FilesConnection):
    with st.spinner("Loading..."):
        trans_df = load_data_gcs(TRANSACTION_PATH, _conn)
        outputs_df = load_data_gcs(OUTPUT_PATH, _conn)

        # Filter by duoc si
        current_labeller = st.session_state["username"]
        mask_labeller = (trans_df[DUOC_SI_COLS] == current_labeller).any(axis="columns")
        trans_df = trans_df[mask_labeller]

    return trans_df, outputs_df


def color_importance(series: pd.Series):
    return series.apply(lambda x: f"background-color: {IMPORTANCE_COLOR_CODES[x]}")


def aggrid_table(df: pd.DataFrame, edit_col, pre_selected=None):
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_selection(
        selection_mode="multiple", use_checkbox=True, pre_selected_rows=pre_selected
    )
    gd.configure_columns(edit_col, editable=True)
    grid_options = gd.build()
    grid_options["defaultColDef"]["wrapText"] = True
    grid_options["defaultColDef"]["autoHeight"] = True
    grid_options["defaultColDef"]["resizable"] = True
    grid_options["defaultColDef"]["cellStyle"] = {"wordBreak": "normal"}
    outputs_grid = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
    )

    return outputs_grid


def grid_clickable(df: pd.DataFrame):
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_selection()
    selection = AgGrid(
        df,
        gridOptions=gd.build(),
        update_mode=GridUpdateMode.MODEL_CHANGED,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
    )

    return selection


def change_metric_color(wgt_txt, wch_color="#000000"):
    html_str = (
        """
        <script>
            var elements = window.parent.document.querySelectorAll('*'), i;
            for (i = 0; i < elements.length; ++i) { if (elements[i].innerText == |wgt_txt|) elements[i].style.color = '"""
        + wch_color
        + """'; }
        </script>
        """
    )

    html_str = html_str.replace("|wgt_txt|", "'" + wgt_txt + "'")
    components.html(f"{html_str}", height=0, width=0)


def labelling_component():
    if not st.session_state.to_dict().get("authentication_status", None):
        pass
    else:
        labeller_username = st.session_state["username"]
        (
            col_status_labeled,
            col_status_pending,
            col_status_unlabeled,
        ) = st.columns([1, 1, 1])
        conn = st.connection("gcs", type=FilesConnection)

        # ? Static data
        trans_df, outputs_df = load_all_data(conn)
        # ? Label data
        try:
            with st.spinner("Loading label data..."):
                get_data_gcs(
                    LABEL_PATH.format(labeller_username),
                    LOCAL_LABEL_PATH.format(labeller_username),
                    conn,
                )
                label_df = pd.read_csv(LOCAL_LABEL_PATH.format(labeller_username))
        except:
            label_df = pd.DataFrame(
                columns=[
                    "CardCode",
                    "specialties",
                    "specialty_labels",
                    "specialty_responses",
                    "disease_groups",
                    "disease_group_labels",
                    "disease_group_responses",
                ]
            )

        # ? Pending data
        try:
            with st.spinner("Loading pending data..."):
                get_data_gcs(
                    PENDING_CUSTOMER_PATH.format(labeller_username),
                    LOCAL_PENDING_CUSTOMER_PATH.format(labeller_username),
                    conn,
                )
                postponed_df = pd.read_csv(
                    LOCAL_PENDING_CUSTOMER_PATH.format(labeller_username)
                )
        except:
            postponed_df = pd.DataFrame(
                columns=[
                    "CardCode",
                    "specialties",
                    "specialty_labels",
                    "specialty_responses",
                    "disease_groups",
                    "disease_group_labels",
                    "disease_group_responses",
                ]
            )

        total_cardcodes = set(trans_df["customer_id"].unique())
        cardcodes = load_unlabeled_cardcodes(labeller_username, total_cardcodes)
        labelled_cardcodes = load_cardcode_label(labeller_username)
        pending_cardcodes = set(postponed_df["CardCode"].unique())
        unlabeled_cardcodes = total_cardcodes - labelled_cardcodes - pending_cardcodes

        # ? Status cards
        st.session_state["n_unlabeled_cardcodes"] = len(cardcodes) - len(
            pending_cardcodes
        )
        st.session_state["n_labeled_cardcodes"] = len(total_cardcodes) - len(cardcodes)
        st.session_state["n_pending_cardcodes"] = len(pending_cardcodes)
        col_status_unlabeled.metric(
            label="Chưa hoàn tất",
            value=f'{st.session_state["n_unlabeled_cardcodes"]:,}',
        )
        col_status_labeled.metric(
            label="Hoàn tất", value=f'{st.session_state["n_labeled_cardcodes"]:,}'
        )
        col_status_pending.metric(
            label="Suy nghĩ lại", value=f'{st.session_state["n_pending_cardcodes"]:,}'
        )
        style_metric_cards(border_radius_px=10)
        change_metric_color(f'{st.session_state["n_labeled_cardcodes"]:,}', "#92C580")
        change_metric_color(f'{st.session_state["n_pending_cardcodes"]:,}', "#949494")
        change_metric_color(f'{st.session_state["n_unlabeled_cardcodes"]:,}', "#F9B064")

        st.write(
            """
            <style>
            iframe[data-testid="stIFrame"] {
                display: none;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.write(
            """<style>
            .st-emotion-cache-1r6slb0 {
                align-self: end;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.sidebar.header("1. Trạng thái khách hàng")
        status_list = ["Hoàn tất", "Suy nghĩ lại", "Chưa hoàn tất"]
        customer_status = status_filter(
            status_list,
            sidebar=True,
            name="Trạng thái khách hàng",
            placeholder="Chọn trạng thái",
            name_visibility="hidden",
        )

        st.sidebar.header("2. Danh sách khách hàng")
        filtered_cardcodes = set()

        if customer_status == []:
            filtered_cardcodes = total_cardcodes
        else:
            if "Hoàn tất" in customer_status:
                filtered_cardcodes.update(labelled_cardcodes)
            if "Suy nghĩ lại" in customer_status:
                filtered_cardcodes.update(pending_cardcodes)
            if "Chưa hoàn tất" in customer_status:
                filtered_cardcodes.update(unlabeled_cardcodes)

        _, back_btn_col, next_btn_col, _ = st.columns([2, 1, 1, 2])

        st.write(
            """<style>
            [data-testid="baseButton-secondary"] {
                margin-top: 1rem;
                height: 56px;
                width: -webkit-fill-available;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )
        filtered_cardcodes = sorted(list(filtered_cardcodes))
        cardcode = select_customer(filtered_cardcodes)
        # print(cardcode)

        cardcode_status = None
        if cardcode in labelled_cardcodes:
            cardcode_status = "Hoàn tất"
        elif cardcode in unlabeled_cardcodes:
            cardcode_status = "Chưa hoàn tất"
        elif cardcode in pending_cardcodes:
            cardcode_status = "Suy nghĩ lại"

        # * WITH BUTTON
        def increase_cardcode():
            if len(filtered_cardcodes) == 0:
                st.session_state["customer_selector"] = None
            else:
                if not st.session_state["customer_selector"]:
                    st.session_state["customer_selector"] = filtered_cardcodes[0]
                else:
                    current_idx = filtered_cardcodes.index(
                        st.session_state["customer_selector"]
                    )
                    if current_idx < len(filtered_cardcodes) - 1:
                        st.session_state["customer_selector"] = filtered_cardcodes[
                            current_idx + 1
                        ]
                    else:
                        st.session_state["customer_selector"] = filtered_cardcodes[0]

        def decrease_cardcode():
            if len(filtered_cardcodes) == 0:
                st.session_state["customer_selector"] = None
            else:
                if not st.session_state["customer_selector"]:
                    st.session_state["customer_selector"] = list(filtered_cardcodes)[0]
                else:
                    current_idx = filtered_cardcodes.index(
                        st.session_state["customer_selector"]
                    )
                    if current_idx > 0:
                        st.session_state["customer_selector"] = filtered_cardcodes[
                            current_idx - 1
                        ]
                    else:
                        st.session_state["customer_selector"] = filtered_cardcodes[-1]

        next_btn_col.button("**NEXT**", key="btn_next", on_click=increase_cardcode)
        st.write(
            """
            <style>
            div.stButton > button:btn_next {
                background-color: #d6d2d2
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        back_btn_col.button(
            "**PREVIOUS**", key="btn_previous", on_click=decrease_cardcode
        )

        # * OUTPUT & FORM

        # with col2:
        st.write(
            """<style>
            [data-testid="stHorizontalBlock"] {
                align-items: center;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.write(
            """<style>
            [data-testid="stVerticalBlock"] {
                gap: 0;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.write(
            """<style>
            [data-testid="baseButton-primaryFormSubmit"] {
                height: 56px;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.write(
            """<style>
            [data-testid="baseButton-secondaryFormSubmit"] {
                height: 56px;
                background-color: #D9D9D9;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.write(
            """<style>
            .st-emotion-cache-11y67dz.e1f1d6gn1{
                display: block;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.write(
            """<style>
            [data-testid="stForm"]{
                border: none;
                padding-left: unset;
                padding-right: unset;
            },
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.form("label_form", clear_on_submit=True):
            col_form_1, col_form_2, col_form_3, col_form_4 = st.columns([2, 2, 2, 2])
            # with col_form_1:
            #     is_postponed = st.checkbox("Suy nghĩ lại")
            col_form_1.metric("Mã khách hàng", value=cardcode)
            col_form_2.metric("Trạng thái khách hàng", value=cardcode_status)
            with col_form_3:
                is_postponed = st.checkbox("Suy nghĩ lại")

            with col_form_4:
                submitted = st.form_submit_button(
                    "**SAVE**", type="primary", use_container_width=True
                )

            st.subheader("Output - Đánh giá theo KH")
            output_col_1, output_col_2 = st.columns(2)

            pre_selected_specialties = None
            pre_selected_disease_groups = None

            if cardcode in labelled_cardcodes:
                outputs_df: pd.DataFrame = label_df[label_df["CardCode"] == cardcode]

                pre_selected_specialties = outputs_df[
                    outputs_df["specialty_labels"]
                ].index.to_list()
                pre_selected_disease_groups = outputs_df[
                    outputs_df["disease_group_labels"]
                ].index.to_list()

                outputs_lv1 = outputs_df[["specialties", "specialty_responses"]].rename(
                    columns={
                        "specialties": "lv1_name",
                        "specialty_responses": "response",
                    }
                )
                outputs_lv2 = outputs_df[
                    ["disease_groups", "disease_group_responses"]
                ].rename(
                    columns={
                        "disease_groups": "lv2_name",
                        "disease_group_responses": "response",
                    }
                )
            else:
                outputs_df: pd.DataFrame = outputs_df[
                    outputs_df["customer_id"] == cardcode
                ][
                    [
                        "lv1_name",
                        "lv2_name",
                    ]
                ]
                outputs_lv1 = outputs_df[["lv1_name"]].copy()
                outputs_lv1["response"] = None
                outputs_lv2 = outputs_df[["lv2_name"]].copy()
                outputs_lv2["response"] = None

            with output_col_1:
                outputs_lv1 = outputs_lv1.rename(
                    columns={
                        "lv1_name": "Tên chuyên khoa",
                        "response": "Phản hồi chuyên khoa",
                    }
                )
                grid_output_lv1 = aggrid_table(
                    outputs_lv1,
                    "Phản hồi chuyên khoa",
                    pre_selected=pre_selected_specialties,
                )

            with output_col_2:
                outputs_lv2 = outputs_lv2.rename(
                    columns={
                        "lv2_name": "Tên nhóm bệnh",
                        "response": "Phản hồi nhóm bệnh",
                    }
                )
                grid_output_lv2 = aggrid_table(
                    outputs_lv2,
                    "Phản hồi nhóm bệnh",
                    pre_selected=pre_selected_disease_groups,
                )

            with col_form_3:
                if submitted:
                    if cardcode is None:
                        st.warning("Hãy chọn 1 cardcode")
                    else:
                        if is_postponed:
                            (
                                specialties,
                                specialty_responses,
                            ) = grid_output_lv1.data.to_dict(orient="list").values()
                            (
                                disease_groups,
                                disease_group_responses,
                            ) = grid_output_lv2.data.to_dict(orient="list").values()
                            lv1_disagree_index = [
                                item["_selectedRowNodeInfo"]["nodeRowIndex"]
                                for item in grid_output_lv1["selected_rows"]
                            ]
                            lv2_disagree_index = [
                                item["_selectedRowNodeInfo"]["nodeRowIndex"]
                                for item in grid_output_lv2["selected_rows"]
                            ]

                            df_pending = pd.DataFrame(
                                {
                                    "specialties": specialties,
                                    "specialty_responses": specialty_responses,
                                    "disease_groups": disease_groups,
                                    "disease_group_responses": disease_group_responses,
                                }
                            )
                            df_pending["CardCode"] = cardcode
                            df_pending["specialty_labels"] = False
                            df_pending["disease_group_labels"] = False

                            df_pending.loc[
                                lv1_disagree_index, "specialty_labels"
                            ] = True
                            df_pending.loc[
                                lv2_disagree_index, "disease_group_labels"
                            ] = True

                            if cardcode not in pending_cardcodes:
                                postponed_df = pd.concat(
                                    [df_pending, postponed_df], ignore_index=True
                                )
                            else:
                                postponed_df = postponed_df[
                                    postponed_df["CardCode"] != cardcode
                                ]
                                postponed_df = pd.concat(
                                    [df_pending, postponed_df], ignore_index=True
                                )

                            with st.spinner("Saving postponed data...", cache=True):
                                postponed_df.to_csv(
                                    LOCAL_PENDING_CUSTOMER_PATH.format(
                                        labeller_username
                                    ),
                                    index=False,
                                )
                                save_data_gcs(
                                    LOCAL_PENDING_CUSTOMER_PATH.format(
                                        labeller_username
                                    ),
                                    PENDING_CUSTOMER_PATH.format(labeller_username),
                                    conn=conn,
                                )
                                if cardcode in labelled_cardcodes:
                                    # Remove from pending list
                                    label_df = label_df[
                                        label_df["CardCode"] != cardcode
                                    ]
                                    with st.spinner("Saving postponed data..."):
                                        label_df.to_csv(
                                            LOCAL_LABEL_PATH.format(labeller_username),
                                            index=False,
                                        )
                                        save_data_gcs(
                                            LOCAL_LABEL_PATH.format(labeller_username),
                                            LABEL_PATH.format(labeller_username),
                                            conn=conn,
                                        )
                                        st.session_state["n_labeled_cardcodes"] -= 1

                                st.session_state["n_unlabeled_cardcodes"] -= 1
                                st.session_state["n_pending_cardcodes"] += 1
                        else:
                            (
                                specialties,
                                specialty_responses,
                            ) = grid_output_lv1.data.to_dict(orient="list").values()
                            (
                                disease_groups,
                                disease_group_responses,
                            ) = grid_output_lv2.data.to_dict(orient="list").values()

                            lv1_disagree_index = [
                                item["_selectedRowNodeInfo"]["nodeRowIndex"]
                                for item in grid_output_lv1["selected_rows"]
                            ]
                            lv2_disagree_index = [
                                item["_selectedRowNodeInfo"]["nodeRowIndex"]
                                for item in grid_output_lv2["selected_rows"]
                            ]

                            df_submit = pd.DataFrame(
                                {
                                    "specialties": specialties,
                                    "specialty_responses": specialty_responses,
                                    "disease_groups": disease_groups,
                                    "disease_group_responses": disease_group_responses,
                                }
                            )
                            df_submit["CardCode"] = cardcode
                            df_submit["specialty_labels"] = False
                            df_submit["disease_group_labels"] = False
                            trash_dict = {
                                "None": None,
                                "NaN": None,
                                "none": None,
                            }
                            df_submit["specialty_responses"].replace(
                                trash_dict, inplace=True
                            )
                            df_submit["disease_group_responses"].replace(
                                trash_dict, inplace=True
                            )

                            df_submit.loc[lv1_disagree_index, "specialty_labels"] = True
                            df_submit.loc[
                                lv2_disagree_index, "disease_group_labels"
                            ] = True

                            if (
                                df_submit.loc[lv1_disagree_index, "specialty_responses"]
                                == "None"
                            ).sum() != 0 or (
                                df_submit.loc[
                                    lv2_disagree_index, "disease_group_labels"
                                ]
                                == "None"
                            ).sum() != 0:
                                st.warning(
                                    "Mỗi ô không đồng ý phải có bình luận tương ứng"
                                )
                            else:
                                if cardcode not in label_df["CardCode"]:
                                    label_df = pd.concat(
                                        [df_submit, label_df], ignore_index=True
                                    )
                                else:
                                    label_df = label_df[
                                        label_df["CardCode"] != cardcode
                                    ]
                                    label_df = pd.concat(
                                        [df_submit, label_df], ignore_index=True
                                    )

                                with st.spinner("Saving data..."):
                                    label_df.to_csv(
                                        LOCAL_LABEL_PATH.format(labeller_username),
                                        index=False,
                                    )
                                    save_data_gcs(
                                        LOCAL_LABEL_PATH.format(labeller_username),
                                        LABEL_PATH.format(labeller_username),
                                        conn=conn,
                                    )
                                    if cardcode in pending_cardcodes:
                                        # Remove from pending list
                                        postponed_df = postponed_df[
                                            postponed_df["CardCode"] != cardcode
                                        ]
                                        with st.spinner("Saving postponed data..."):
                                            postponed_df.to_csv(
                                                LOCAL_PENDING_CUSTOMER_PATH.format(
                                                    labeller_username
                                                ),
                                                index=False,
                                            )
                                            save_data_gcs(
                                                LOCAL_PENDING_CUSTOMER_PATH.format(
                                                    labeller_username
                                                ),
                                                PENDING_CUSTOMER_PATH.format(
                                                    labeller_username
                                                ),
                                                conn=conn,
                                            )
                                            st.session_state["n_pending_cardcodes"] -= 1

                                    st.session_state["n_unlabeled_cardcodes"] -= 1
                                    st.session_state["n_labeled_cardcodes"] += 1
                    st.rerun()
        # with col1:
        show_input_cols = ["date", "item_name", "ingredients", "unitname"]
        trans_df: pd.DataFrame = trans_df[trans_df["customer_id"] == cardcode]
        # print(outputs_df[outputs_df["importance_level"] == "Cao"])
        st.subheader(
            f"Input - Chi tiết đơn hàng theo ngày ( :blue[{trans_df['bill_id'].nunique()} đơn hàng])"
        )

        trans_df = trans_df[show_input_cols]

        st.dataframe(
            trans_df.rename(
                columns={
                    "date": "Ngày mua",
                    "item_name": "Tên thuốc",
                    "ingredients": "Hoạt chất",
                    "unitname": "Đơn vị",
                }
            ).style.apply(format_color_groups, axis=None),
            hide_index=True,
            use_container_width=True,
            height=300,
        )

        # st.subheader("Danh sách KH đã dán nhãn")
        # try:
        #     with st.spinner("Loading label data..."):
        #         # get_data_gcs(
        #         #     LABEL_PATH.format(labeller_username),
        #         #     LOCAL_LABEL_PATH.format(labeller_username),
        #         #     conn,
        #         # )
        #         label_df = pd.read_csv(LOCAL_LABEL_PATH.format(labeller_username))[
        #             ["CardCode"]
        #         ]
        # except:
        #     label_df = pd.DataFrame(
        #         columns=[
        #             "CardCode",
        #         ]
        #     )

        # label_df["status"] = "COMPLETE"
        # label_df = label_df.drop_duplicates(subset=["CardCode"])

        # try:
        #     with st.spinner("Loading pending data..."):
        #         # get_data_gcs(
        #         #     PENDING_CUSTOMER_PATH.format(labeller_username),
        #         #     LOCAL_PENDING_CUSTOMER_PATH.form(labeller_username),
        #         #     conn,
        #         # )
        #         postponed_df = pd.read_csv(
        #             LOCAL_PENDING_CUSTOMER_PATH.format(labeller_username)
        #         )[["CardCode"]]
        # except:
        #     postponed_df = pd.DataFrame(
        #         columns=[
        #             "CardCode",
        #         ]
        #     )
        # postponed_df["status"] = "PENDING"
        # postponed_df = postponed_df.drop_duplicates(subset=["CardCode"])

        # all_label_df = pd.concat(
        #     [label_df, postponed_df], ignore_index=True
        # ).sort_values(by=["status", "CardCode"], ascending=[False, True])

        # st.dataframe(
        #     all_label_df.rename(columns={"CardCode": "Mã khách hàng"}),
        #     use_container_width=False,
        #     hide_index=True,
        # )
