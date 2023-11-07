import streamlit as st
import pandas as pd

from st_files_connection import FilesConnection
from st_aggrid import AgGrid, GridUpdateMode, ColumnsAutoSizeMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

from utils import save_data_gcs, load_data_gcs, get_data_gcs

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
    chosen_cardcodes = cardcodes

    cardcode = st.selectbox(
        f"Chọn CardCode khách hàng (:blue[còn lại {len(chosen_cardcodes)} KH])",
        chosen_cardcodes,
        index=None,
        placeholder="Chọn cardcode...",
        key="customer_selector",
    )

    return cardcode


def load_unlabeled_cardcodes(labeller_name: str, cardcode_total):
    labelled_cardcodes = load_cardcode_label(labeller_name)
    return cardcode_total - labelled_cardcodes


st.cache_data


def load_all_data(conn: FilesConnection):
    with st.spinner("Loading..."):
        trans_df = load_data_gcs(TRANSACTION_PATH, conn)
        outputs_df = load_data_gcs(OUTPUT_PATH, conn)

        # Filter by duoc si
        current_labeller = st.session_state["username"]
        mask_labeller = (trans_df[DUOC_SI_COLS] == current_labeller).any(axis="columns")
        trans_df = trans_df[mask_labeller]

    return trans_df, outputs_df


def color_importance(series: pd.Series):
    return series.apply(lambda x: f"background-color: {IMPORTANCE_COLOR_CODES[x]}")


def aggrid_table(df: pd.DataFrame):
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_selection(selection_mode="multiple", use_checkbox=True)
    gd.configure_columns("Phản hồi", editable=True)
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
        enable_enterprise_modules=False
    )

    return outputs_grid


def labelling_component():
    if not st.session_state.to_dict().get("authentication_status", None):
        pass
        # st.warning("Hãy đăng nhập để sử dụng dịch vụ")
    else:
        labeller_username = st.session_state["username"]
        col_x_1, col_x_2, _ = st.columns([1, 2, 3])
        col1, col2 = st.columns([1, 1])
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
        pending_cardcodes = postponed_df["CardCode"].unique()

        with col_x_1:
            st.write(
                """<style>
                .st-emotion-cache-1r6slb0 {
                    align-self: end;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.subheader("Chọn khách hàng")
            cardcode = select_customer(cardcodes)
            with col_x_2:
                st.warning(
                    "Chỉ hiển thị ***khách hàng chưa label*** hoặc ***khách hàng pending***",
                    icon="⚠️",
                )

        # with col1:
        show_input_cols = [
            "date",
            "item_name",
            "ingredients",
            "unitname",
        ]
        trans_df: pd.DataFrame = trans_df[trans_df["customer_id"] == cardcode][
            show_input_cols
        ]

        # print(outputs_df[outputs_df["importance_level"] == "Cao"])
        st.subheader(f"Input - Chi tiết đơn hàng theo ngày")
        st.write(
            """<style>
            .st-emotion-cache-ocqkz7.e1f1d6gn4{
                align-items: start;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        th_props = [
            ("font-size", "14px"),
            ("font-weight", "bold"),
            ("color", "#000000"),
            ("background-color", "#f7ffff"),
        ]
        table_styles = [dict(selector="th", props=th_props)]
        st.dataframe(
            trans_df.rename(
                columns={
                    "date": "Ngày mua",
                    "item_name": "Tên thuốc",
                    "ingredients": "Hoạt chất",
                    "unitname": "Đơn vị",
                }
            )
            .style.apply(format_color_groups, axis=None)
            .set_table_styles(table_styles),
            hide_index=True,
            use_container_width=True,
            height=300,
        )

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

        with st.form("label_form", clear_on_submit=True):
            st.subheader("Output - Đánh giá theo KH")
            output_col_1, output_col_2 = st.columns(2)

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
                    columns={"lv1_name": "Tên chuyên khoa", "response": "Phản hồi"}
                )
                grid_output_lv1 = aggrid_table(outputs_lv1)

            with output_col_2:
                outputs_lv2 = outputs_lv2.rename(
                    columns={"lv2_name": "Tên nhóm bệnh", "response": "Phản hồi"}
                )
                grid_output_lv2 = aggrid_table(outputs_lv2)

            col_form_1, col_form_2, col_form_3 = st.columns([2, 2, 4])
            with col_form_1:
                postponed = st.form_submit_button(
                    "**PENDING**", type="secondary", use_container_width=True
                )

            with col_form_2:
                submitted = st.form_submit_button(
                    "**SAVE**", type="primary", use_container_width=True
                )

            with col_form_3:
                if submitted:
                    if cardcode is None:
                        st.warning("Hãy chọn 1 cardcode")
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

                        df_submit.loc[lv1_disagree_index, "specialty_labels"] = True
                        df_submit.loc[lv2_disagree_index, "disease_group_labels"] = True

                        if cardcode not in label_df["CardCode"]:
                            label_df = pd.concat(
                                [df_submit, label_df], ignore_index=True
                            )
                        else:
                            label_df = label_df[label_df["CardCode"] != cardcode]
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
                                        PENDING_CUSTOMER_PATH.format(labeller_username),
                                        conn=conn,
                                    )
                            st.rerun()
                elif postponed:
                    if cardcode is None:
                        st.warning("Hãy chọn 1 cardcode")
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

                        df_pending.loc[lv1_disagree_index, "specialty_labels"] = True
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

                        with st.spinner("Saving postponed data..."):
                            postponed_df.to_csv(
                                LOCAL_PENDING_CUSTOMER_PATH.format(labeller_username),
                                index=False,
                            )
                            save_data_gcs(
                                LOCAL_PENDING_CUSTOMER_PATH.format(labeller_username),
                                PENDING_CUSTOMER_PATH.format(labeller_username),
                                conn=conn,
                            )

        st.subheader("Pending - Danh sách KH")
        try:
            with st.spinner("Loading label data..."):
                # get_data_gcs(
                #     LABEL_PATH.format(labeller_username),
                #     LOCAL_LABEL_PATH.format(labeller_username),
                #     conn,
                # )
                label_df = pd.read_csv(LOCAL_LABEL_PATH.format(labeller_username))[
                    ["CardCode"]
                ]
        except:
            label_df = pd.DataFrame(
                columns=[
                    "CardCode",
                ]
            )

        label_df["status"] = "COMPLETE"
        label_df = label_df.drop_duplicates(subset=["CardCode"])

        try:
            with st.spinner("Loading pending data..."):
                # get_data_gcs(
                #     PENDING_CUSTOMER_PATH.format(labeller_username),
                #     LOCAL_PENDING_CUSTOMER_PATH.form(labeller_username),
                #     conn,
                # )
                postponed_df = pd.read_csv(
                    LOCAL_PENDING_CUSTOMER_PATH.format(labeller_username)
                )[["CardCode"]]
        except:
            postponed_df = pd.DataFrame(
                columns=[
                    "CardCode",
                ]
            )
        postponed_df["status"] = "PENDING"
        postponed_df = postponed_df.drop_duplicates(subset=["CardCode"])

        all_label_df = (
            pd.concat([label_df, postponed_df], ignore_index=True)
            .sort_values(by=["status"], ascending=[False])
            .drop_duplicates(subset=["CardCode"])
            .sort_values(by=["CardCode"], ascending=[True])
        )
        st.dataframe(all_label_df, use_container_width=True, hide_index=True)
