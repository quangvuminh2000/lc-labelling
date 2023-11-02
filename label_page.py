import streamlit as st
import pandas as pd
import numpy as np

from st_files_connection import FilesConnection

from utils import save_data_gcs, load_data_gcs

TRANSACTION_PATH = "lc_labelling_bucket/cdp/transactions.csv"
OUTPUT_PATH = "lc_labelling_bucket/cdp/outputs_topn.csv"
LABEL_PATH = "lc_labelling_bucket/cdp/total_labels.csv"
LOCAL_LABEL_PATH = "./data/total_labels.csv"
COLOR_CODES = ["#8bb9d6", "#b2a7d0", "#60bae3", "#a7d6eb", "#9fcdb6", "#fce5cd"]
TOP_LIMIT = 10


def format_color_groups(df):
    x = df.copy()
    factors = list(x["Ngày mua"].unique())
    colors = np.random.choice(COLOR_CODES, size=len(factors), replace=False)
    for i, factor in enumerate(factors):
        style = f"background-color: {colors[i]}"
        x.loc[x["Ngày mua"] == factor, :] = style
    return x


def load_cardcode_label(labeller_name: str):
    try:
        label_data = pd.read_csv(LOCAL_LABEL_PATH)
        cardcode_label = (label_data.query(f'username == "{labeller_name}"'))[
            "CardCode"
        ].unique()

        return set(cardcode_label)
    except:
        return set()


def select_customer(cardcodes):
    if len(cardcodes) > TOP_LIMIT:
        chosen_cardcodes = list(cardcodes)[:TOP_LIMIT]
    else:
        chosen_cardcodes = cardcodes

    cardcode = st.selectbox(
        "Chọn CardCode khách hàng",
        chosen_cardcodes,
        index=None,
        placeholder="Chọn cardcode...",
        key="customer_selector",
    )

    return cardcode


def load_unlabeled_cardcodes(labeller_name: str, cardcode_total):
    labelled_cardcodes = load_cardcode_label(labeller_name)
    return cardcode_total - labelled_cardcodes


def load_all_data(conn: FilesConnection):
    trans_df = load_data_gcs(TRANSACTION_PATH, conn)
    outputs_df = load_data_gcs(OUTPUT_PATH, conn)
    try:
        label_df = pd.read_csv(LOCAL_LABEL_PATH)
    except:
        label_df = pd.DataFrame(columns=["username", "CardCode", "feedback", "reason"])

    return trans_df, outputs_df, label_df


def labelling_component():
    st.title("KIỂM ĐỊNH KẾT QUẢ ĐÁNH TAG BỆNH TỪ TOOL TỰ ĐỘNG")

    if not st.session_state["authentication_status"]:
        st.warning("Hãy đăng nhập để sử dụng dịch vụ")

    else:
        col_x_1, col_x_2, _ = st.columns([1, 1, 2])
        col1, col2 = st.columns([2, 1])
        conn = st.connection("gcs", type=FilesConnection)
        with col_x_1:
            st.write(
                """<style>
                .st-emotion-cache-ocqkz7.e1f1d6gn4{
                    align-items: end
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            with st.spinner("Loading..."):
                trans_df, outputs_df, label_df = load_all_data(conn)

            labeller_username = st.session_state["username"]
            total_cardcodes = set(trans_df["CardCode"].unique())
            cardcodes = load_unlabeled_cardcodes(labeller_username, total_cardcodes)

            st.subheader("Chọn khách hàng")
            cardcode = select_customer(cardcodes)
        with col_x_2:
            st.warning(
                "Khách hàng được lưu sẽ không hiển thị lại",
                icon="⚠️",
            )

        with col1:
            show_input_cols = ["DocEntry", "Date", "item_name", "Category", "Quantity"]
            trans_df: pd.DataFrame = trans_df[trans_df["CardCode"] == cardcode][
                show_input_cols
            ]

            outputs_df = outputs_df[outputs_df["CardCode"] == cardcode][
                [
                    "lv1_name",
                    "lv1_score",
                    "lv2_name",
                    "lv2_score",
                    "lv3_name",
                    "lv3_score",
                ]
            ]

            st.subheader(
                f"Input - Chi tiết đơn hàng theo ngày (:blue[{trans_df['DocEntry'].nunique()} Đơn hàng])"
            )
            st.dataframe(
                trans_df.rename(
                    columns={
                        "DocEntry": "Mã đơn hàng",
                        "Date": "Ngày mua",
                        "item_name": "Tên sản phẩm",
                        "Category": "Loại",
                        "Quantity": "Số lượng",
                    }
                ).style.apply(format_color_groups, axis=None),
                hide_index=True,
                use_container_width=True,
                height=290,
            )

            st.subheader("Output - Model output")
            st.dataframe(
                outputs_df.rename(
                    columns={
                        "lv1_name": "Cấp 1 - Chuyên Khoa",
                        "lv1_score": "Cấp 1 - Score",
                        "lv2_name": "Cấp 2 - Nhóm bệnh",
                        "lv2_score": "Cấp 2 - Score",
                        "lv3_name": "Cấp 3 - Bệnh",
                        "lv3_score": "Cấp 3 - Score",
                    }
                ),
                hide_index=True,
                use_container_width=True,
                height=141,
            )

        with col2:
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
                [data-testid="baseButton-primaryFormSubmit"] {
                    height: 56px;
                },
                </style>
                """,
                unsafe_allow_html=True,
            )
            with st.form("label_form", clear_on_submit=True):
                st.write("#")
                st.subheader("Phản hồi")
                feedback_val = st.radio(
                    "Feedback", ["Đồng ý", "Kiểm tra lại"], key="feedback_radio"
                )
                st.write("#")
                st.subheader("Ý kiến")
                reason_val = st.text_area(
                    label="Ý kiến (nếu có)",
                    placeholder="Viết ý kiến của bạn...",
                    label_visibility="collapsed",
                )
                reason_val = None if reason_val.strip() == "" else reason_val

                col_form_1, col_form_2 = st.columns([2, 8])
                with col_form_1:
                    submitted = st.form_submit_button(
                        "SAVE", type="primary", use_container_width=True
                    )
                with col_form_2:
                    if submitted:
                        if cardcode is None:
                            st.warning("Hãy chọn 1 cardcode")
                        else:
                            df_submit = pd.DataFrame(
                                {
                                    "username": [labeller_username],
                                    "CardCode": [cardcode],
                                    "feedback": [feedback_val],
                                    "reason": [reason_val],
                                }
                            )

                            label_df = pd.concat(
                                [df_submit, label_df], ignore_index=True
                            )
                            with st.spinner("Saving data..."):
                                label_df.to_csv(LOCAL_LABEL_PATH, index=False)
                                save_data_gcs(LOCAL_LABEL_PATH, LABEL_PATH, conn=conn)
                                st.success("Thank you for your response!!!")

                st.write("#")

        st.subheader("All label data")
        st.dataframe(
            label_df.query(f"username == '{labeller_username}'").rename(
                columns={
                    "username": "Tên tài khoản",
                    "feedback": "Phản hồi",
                    "reason": "Ý kiến",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
