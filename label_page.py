import streamlit as st
import pandas as pd

from st_files_connection import FilesConnection
from st_aggrid import AgGrid, GridUpdateMode, ColumnsAutoSizeMode, DataReturnMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

from streamlit_extras.metric_cards import style_metric_cards

from utils import save_data_gcs, load_data_gcs, get_data_gcs
from datetime import datetime

from components.status_filter import status_filter

TRANSACTION_PATH = "lc_labelling_bucket/cdp/cdp_transaction_sample.csv"
OUTPUT_PATH = "lc_labelling_bucket/cdp/cdp_tagging_sample.csv"
LABELLING_PERMISSION = "lc_labelling_bucket/cdp/permission.csv"
LABEL_PATH = "lc_labelling_bucket/cdp/labels/total_labels_{}_alpha.csv"
LOCAL_LABEL_PATH = "./data/total_labels_{}_alpha.csv"
PENDING_CUSTOMER_PATH = "lc_labelling_bucket/cdp/labels/pending_{}.csv"
LOCAL_PENDING_CUSTOMER_PATH = "./data/pending_{}.csv"
LABEL_STATUS_PATH = "lc_labelling_bucket/cdp/status/label_status_{}.csv"
LOCAL_LABEL_STATUS_PATH = "./data/label_status_{}.csv"
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


def save_data_local_cloud(
    df: pd.DataFrame, local_path: str, cloud_path: str, conn: FilesConnection
):
    df.to_csv(
        local_path,
        index=False,
    )
    save_data_gcs(
        local_path,
        cloud_path,
        conn=conn,
    )


@st.cache_data
def load_all_data(_conn: FilesConnection):
    with st.spinner("Loading..."):
        trans_df = load_data_gcs(TRANSACTION_PATH, _conn)
        outputs_df = load_data_gcs(OUTPUT_PATH, _conn)

    return trans_df, outputs_df


def color_importance(series: pd.Series):
    return series.apply(lambda x: f"background-color: {IMPORTANCE_COLOR_CODES[x]}")


def aggrid_table(df: pd.DataFrame, edit_col, pre_selected=None):
    gd = GridOptionsBuilder.from_dataframe(df)
    pre_selected_dict = {}
    if pre_selected is not None:
        pre_selected_dict = dict(zip(pre_selected, range(len(pre_selected))))
    gd.configure_selection(
        selection_mode="multiple",
        use_checkbox=True,
        pre_selected_rows=pre_selected_dict,
        groupSelectsFiltered=False,
    )
    gd.configure_columns(edit_col, editable=True)
    gd.configure_auto_height(False)
    gd.configure_grid_options(rowStyle={"lineHeight": "0px"})
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
        height=250,
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


def labelling_component(authenticator):
    if not st.session_state.to_dict().get("authentication_status", None):
        pass
    else:
        labeller_username = st.session_state["username"]
        conn = st.connection("gcs", type=FilesConnection)
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        st.write(
            """
            <style>
            body > div#root:nth-child(2) > div:nth-child(1) > div.withScreencast:nth-child(1) > div > div.stApp.stAppEmbeddingId-s3wfzjqwcokm.streamlit-wide.st-emotion-cache-fg4pbf.erw9t6i1 > div.appview-container.st-emotion-cache-1wrcr25.ea3mdgi6:nth-child(2) > section.main.st-emotion-cache-uf99v8.ea3mdgi5:nth-child(2) > div.block-container.st-emotion-cache-z5fcl4.ea3mdgi4:nth-child(1) > div.st-emotion-cache-1wmy9hl.e1f1d6gn0 > div.st-emotion-cache-1y9ui5k.e1f1d6gn1 > div.element-container.st-emotion-cache-b0j709.e1f1d6gn3:nth-child(1) {
                display: none;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ? Static data
        permission_df = load_data_gcs(LABELLING_PERMISSION, conn)

        trans_df, outputs_df = load_all_data(conn)

        # Filter by duoc si
        current_labeller = st.session_state["username"]
        start_idx, end_idx = (
            permission_df[permission_df["user_name"] == current_labeller][
                ["start_idx", "end_idx"]
            ]
            .values[0]
            .tolist()
        )
        trans_df = trans_df[trans_df["customer_id"].between(start_idx, end_idx)]
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

        # ? Status data
        try:
            with st.spinner("Loading status data..."):
                get_data_gcs(
                    LABEL_STATUS_PATH.format(labeller_username),
                    LOCAL_LABEL_STATUS_PATH.format(labeller_username),
                    conn,
                )
                status_df = pd.read_csv(
                    LOCAL_LABEL_STATUS_PATH.format(labeller_username)
                )
        except:
            status_df = pd.DataFrame(columns=["customer_id", "status", "last_update"])
            status_df["customer_id"] = trans_df["customer_id"].unique()
            status_df["status"] = "Chưa hoàn tất"
            status_df["last_update"] = today_str

        total_cardcodes = set(trans_df["customer_id"].unique())
        cardcodes = load_unlabeled_cardcodes(labeller_username, total_cardcodes)
        labelled_cardcodes = load_cardcode_label(labeller_username)
        pending_cardcodes = set(postponed_df["CardCode"].unique())
        unlabeled_cardcodes = total_cardcodes - labelled_cardcodes - pending_cardcodes

        # ? Status cards
        (
            col_status,
            col_warning,
            col_status_labeled,
            col_status_pending,
            col_status_unlabeled,
        ) = st.columns([2, 2, 1, 1, 1])
        st.session_state["n_unlabeled_cardcodes"] = len(cardcodes) - len(
            pending_cardcodes
        )
        st.session_state["n_labeled_cardcodes"] = len(total_cardcodes) - len(cardcodes)
        st.session_state["n_pending_cardcodes"] = len(pending_cardcodes)
        col_status_unlabeled.metric(
            label=":orange[Chưa hoàn tất]",
            value=f'{st.session_state["n_unlabeled_cardcodes"]:,}',
        )
        col_status_labeled.metric(
            label=":green[Hoàn tất]",
            value=f'{st.session_state["n_labeled_cardcodes"]:,}',
        )
        col_status_pending.metric(
            label=":grey[Suy nghĩ lại]",
            value=f'{st.session_state["n_pending_cardcodes"]:,}',
        )
        style_metric_cards(border_radius_px=10)

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

        back_btn_col, next_btn_col = st.sidebar.columns([1, 1])
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

        col_status.write(f"MÃ KHÁCH HÀNG: **{cardcode}**")
        col_status.write(f"TRẠNG THÁI KHÁCH HÀNG: **{cardcode_status}**")

        st.header("Kết luận (output)")
        output_col_1, output_col_2 = st.columns(2)

        pre_selected_specialties = None
        pre_selected_disease_groups = None

        if cardcode in labelled_cardcodes:
            outputs_df: pd.DataFrame = label_df[
                label_df["CardCode"] == cardcode
            ].reset_index(drop=True)

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
        elif cardcode in pending_cardcodes:
            outputs_df: pd.DataFrame = postponed_df[
                postponed_df["CardCode"] == cardcode
            ].reset_index(drop=True)

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

        with st.sidebar.form("label_form", clear_on_submit=True):
            # col_form_1, _, col_form_2, col_form_3 = st.columns([4, 1, 1, 1])
            # with col_form_1:
            #     is_postponed = st.checkbox("Suy nghĩ lại")
            # col_form_1.write(f"MÃ KHÁCH HÀNG: **{cardcode}**")
            # col_form_1.write(f"TRẠNG THÁI KHÁCH HÀNG: **{cardcode_status}**")
            # with col_form_2:
            is_postponed = st.checkbox("Suy nghĩ lại")

            # with col_form_3:
            submitted = st.form_submit_button(
                "**SAVE**", type="primary", use_container_width=True
            )

            st.write(
                """
                <style>
                    div[data-testid="stCheckbox"] {
                        border: 1px;
                        height: 40px;
                        font-size: 50px;
                        background: white;
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                        border-radius: 5px;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )

            if submitted:
                if cardcode is None:
                    st.sidebar.warning("Hãy chọn 1 cardcode")
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
                        trash_dict = {
                            "None": None,
                            "NaN": None,
                            "none": None,
                        }
                        df_pending["specialty_responses"].replace(
                            trash_dict, inplace=True
                        )
                        df_pending["disease_group_responses"].replace(
                            trash_dict, inplace=True
                        )

                        df_pending.loc[lv1_disagree_index, "specialty_labels"] = True
                        df_pending.loc[
                            lv2_disagree_index, "disease_group_labels"
                        ] = True

                        if cardcode not in pending_cardcodes:
                            postponed_df = pd.concat(
                                [df_pending, postponed_df], ignore_index=True
                            ).drop_duplicates(ignore_index=True)
                        else:
                            postponed_df = postponed_df[
                                postponed_df["CardCode"] != cardcode
                            ]
                            postponed_df = pd.concat(
                                [df_pending, postponed_df], ignore_index=True
                            ).drop_duplicates(ignore_index=True)

                        with st.spinner("Saving postponed data...", cache=True):
                            save_data_local_cloud(
                                postponed_df,
                                local_path=LOCAL_PENDING_CUSTOMER_PATH.format(
                                    labeller_username
                                ),
                                cloud_path=PENDING_CUSTOMER_PATH.format(
                                    labeller_username
                                ),
                                conn=conn,
                            )
                            status_df = pd.concat(
                                [
                                    pd.DataFrame(
                                        {
                                            "customer_id": [cardcode],
                                            "status": ["Suy nghĩ lại"],
                                            "last_update": [
                                                datetime.now().strftime(
                                                    "%Y-%m-%d %H:%M:%S"
                                                )
                                            ],
                                        }
                                    ),
                                    status_df,
                                ],
                                ignore_index=True,
                            ).sort_values(
                                by="customer_id", ignore_index=True, ascending=True
                            )
                            save_data_local_cloud(
                                status_df,
                                local_path=LOCAL_LABEL_STATUS_PATH.format(
                                    labeller_username
                                ),
                                cloud_path=LABEL_STATUS_PATH.format(labeller_username),
                                conn=conn,
                            )
                            if cardcode in labelled_cardcodes:
                                # Remove from pending list
                                label_df = label_df[label_df["CardCode"] != cardcode]
                                with st.spinner("Saving postponed data..."):
                                    save_data_local_cloud(
                                        label_df,
                                        local_path=LOCAL_LABEL_PATH.format(
                                            labeller_username
                                        ),
                                        cloud_path=LABEL_PATH.format(labeller_username),
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
                        df_submit.loc[lv2_disagree_index, "disease_group_labels"] = True

                        if (
                            df_submit.loc[lv1_disagree_index, "specialty_responses"]
                            .isna()
                            .sum()
                            != 0
                        ) or (
                            df_submit.loc[lv2_disagree_index, "disease_group_labels"]
                            .isna()
                            .sum()
                            != 0
                        ):
                            col_warning.warning(
                                "Mỗi ô không đồng ý phải có bình luận tương ứng"
                            )
                        else:
                            if cardcode not in labelled_cardcodes:
                                label_df = pd.concat(
                                    [df_submit, label_df], ignore_index=True
                                ).drop_duplicates(ignore_index=True)
                            else:
                                label_df = label_df[label_df["CardCode"] != cardcode]
                                label_df = pd.concat(
                                    [df_submit, label_df], ignore_index=True
                                ).drop_duplicates(ignore_index=True)

                            with st.spinner("Saving data..."):
                                save_data_local_cloud(
                                    label_df,
                                    local_path=LOCAL_LABEL_PATH.format(
                                        labeller_username
                                    ),
                                    cloud_path=LABEL_PATH.format(labeller_username),
                                    conn=conn,
                                )
                                status_df = pd.concat(
                                    [
                                        pd.DataFrame(
                                            {
                                                "customer_id": [cardcode],
                                                "status": ["Hoàn tất"],
                                                "last_update": [
                                                    datetime.now().strftime(
                                                        "%Y-%m-%d %H:%M:%S"
                                                    )
                                                ],
                                            }
                                        ),
                                        status_df,
                                    ],
                                    ignore_index=True,
                                ).sort_values(
                                    by="customer_id", ignore_index=True, ascending=True
                                )
                                save_data_local_cloud(
                                    status_df,
                                    local_path=LOCAL_LABEL_STATUS_PATH.format(
                                        labeller_username
                                    ),
                                    cloud_path=LABEL_STATUS_PATH.format(
                                        labeller_username
                                    ),
                                    conn=conn,
                                )

                                if cardcode in pending_cardcodes:
                                    # Remove from pending list
                                    postponed_df = postponed_df[
                                        postponed_df["CardCode"] != cardcode
                                    ]
                                    with st.spinner("Saving postponed data..."):
                                        save_data_local_cloud(
                                            postponed_df,
                                            local_path=LOCAL_PENDING_CUSTOMER_PATH.format(
                                                labeller_username
                                            ),
                                            cloud_path=PENDING_CUSTOMER_PATH.format(
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
        st.header(f"Chi tiết :blue[{trans_df['bill_id'].nunique()} đơn hàng] (input)")

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

        authenticator.logout("Logout", "sidebar", key="logout_btn")

        st.write(
            """<style>
            div#gridToolBar {
                display: none;
            },
            </style>
            """,
            unsafe_allow_html=True,
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
