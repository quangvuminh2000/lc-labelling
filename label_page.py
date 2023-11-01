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


def format_color_groups(df):
    x = df.copy()
    factors = list(x["Ngày mua"].unique())
    colors = np.random.choice(COLOR_CODES, size=len(factors), replace=False)
    for i, factor in enumerate(factors):
        style = f"background-color: {colors[i]}"
        x.loc[x["Ngày mua"] == factor, :] = style
    return x


def load_data(conn: FilesConnection):
    # conn = st.connection("gcs", type=FilesConnection)
    trans_df = conn.read(TRANSACTION_PATH, input_format="csv", ttl=60)
    outputs_df = conn.read(OUTPUT_PATH, input_format="csv", ttl=60)

    return trans_df, outputs_df


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
    cardcode = st.selectbox(
        "Chọn CardCode khách hàng",
        cardcodes,
        index=None,
        placeholder="Chọn cardcode...",
        key="customer_selector",
    )

    return cardcode


def load_unlabeled_cardcodes(labeller_name: str, cardcode_total):
    labelled_cardcodes = load_cardcode_label(labeller_name)
    return cardcode_total - labelled_cardcodes


def labelling_component():
    st.title("KIỂM ĐỊNH KẾT QUẢ ĐÁNH TAG BỆNH TỪ TOOL TỰ ĐỘNG")

    if not st.session_state["authentication_status"]:
        st.warning("Hãy đăng nhập để sử dụng dịch vụ")

    else:
        col1, col2 = st.columns(2)
        with col1:
            with st.spinner("Loading..."):
                conn = st.connection("gcs", type=FilesConnection)
                trans_df = load_data_gcs(TRANSACTION_PATH, conn)
                outputs_df = load_data_gcs(OUTPUT_PATH, conn)

            labeller_username = st.session_state["username"]
            total_cardcodes = set(trans_df["CardCode"].unique())
            cardcodes = load_unlabeled_cardcodes(labeller_username, total_cardcodes)

            st.subheader("Chọn khách hàng")
            st.warning(
                "Sau khi submit kết quả kiểm định phải xóa ô chọn để chọn khách hàng mới",
                icon="⚠️",
            )

            cardcode = select_customer(cardcodes)

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
            )

        with col2:
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
            )

        try:
            df_label = pd.read_csv(LOCAL_LABEL_PATH)
        except:
            df_label = pd.DataFrame(
                columns=["username", "CardCode", "feedback", "reason"]
            )

        with st.form("label_form", clear_on_submit=True):
            with col2:
                st.subheader("Phản hồi")
                feedback_val = st.radio(
                    "Feedback", ["Đồng ý", "Kiểm tra lại"], key="feedback_radio"
                )
            st.subheader("Ý kiến")
            reason_val = st.text_area(
                label="Ý kiến (nếu có)",
                placeholder="Viết ý kiến của bạn...",
                label_visibility="collapsed",
            )
            reason_val = None if reason_val.strip() == "" else reason_val

            submitted = st.form_submit_button("SAVE", type="primary")
            if submitted:
                if cardcode is None:
                    st.warning(
                        "Hãy chọn 1 cardcode, hoặc xóa đi cardcode đã chọn và chọn lại"
                    )
                    st.stop()

                df_submit = pd.DataFrame(
                    {
                        "username": [labeller_username],
                        "CardCode": [cardcode],
                        "feedback": [feedback_val],
                        "reason": [reason_val],
                    }
                )

                df_label = pd.concat([df_submit, df_label], ignore_index=True)
                with st.spinner("Saving data..."):
                    df_label.to_csv(LOCAL_LABEL_PATH, index=False)
                    save_data_gcs(LOCAL_LABEL_PATH, LABEL_PATH, conn=conn)
                    st.success("Thank you for your response!!!")

        st.subheader("All label data")
        st.dataframe(
            df_label.query(f"username == '{labeller_username}'"),
            hide_index=True,
            use_container_width=True,
        )
