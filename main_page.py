import streamlit as st
import pandas as pd

TRANSACTION_PATH = "data/transactions.csv"
OUTPUT_PATH = "data/outputs_topn.csv"
LABEL_PATH = "data/total_labels.csv"

st.set_page_config(page_title="Labeling")

st.title("CDP Tool Verify Tagging")

# Add authenticate
st.subheader("Enter email")
labeller_email = st.text_input(
    "Your email", placeholder="Enter your email...", key="labeller_email"
)


def load_data():
    trans_df = pd.read_csv(TRANSACTION_PATH)
    outputs_df = pd.read_csv(OUTPUT_PATH)

    return trans_df, outputs_df


def load_cardcode_label():
    try:
        label_data = pd.read_csv(LABEL_PATH)
        cardcode_label = (label_data.query(f'email == "{labeller_email}"'))[
            "CardCode"
        ].unique()

        return set(cardcode_label)
    except:
        return set()


def select_customer():
    cardcode = st.selectbox(
        "Choose the customer's cardcode",
        cardcodes,
        index=None,
        placeholder="Select the cardcode...",
        key="customer_selector",
    )

    return cardcode


trans_df, outputs_df = load_data()

labeled_cardcodes = load_cardcode_label()
total_cardcodes = set(trans_df["CardCode"].unique())
cardcodes = total_cardcodes - labeled_cardcodes


st.subheader("Choose customer")
st.warning("Clear the selection before enter the new response", icon="⚠️")

cardcode = select_customer()

st.info(f"Labeled customer {len(labeled_cardcodes)}/{len(total_cardcodes)}", icon="☕")

show_input_cols = ["DocEntry", "Date", "item_name", "Category", "Quantity"]
trans_df = trans_df[trans_df["CardCode"] == cardcode][show_input_cols]

outputs_df = outputs_df[outputs_df["CardCode"] == cardcode][
    [f"lv{i}_name" for i in range(1, 4)]
]

st.subheader("Input - Detail transaction")
st.dataframe(trans_df, hide_index=True, use_container_width=True)

st.subheader("Output - Model output")
st.dataframe(outputs_df, hide_index=True, use_container_width=True)


try:
    df_label = pd.read_csv(LABEL_PATH)
except:
    df_label = pd.DataFrame()

with st.form("label_form", clear_on_submit=True):
    st.subheader("Response")
    feedback_val = st.radio("Feedback", ["Agree", "Disagree"])
    reason_val = st.text_area(label="Reason", placeholder="Write your reason...")
    reason_val = None if reason_val.strip() == "" else reason_val

    submitted = st.form_submit_button("SAVE")
    if submitted:
        if cardcode is None:
            st.warning("Please choose the cardcode")
            st.stop()

        df_submit = pd.DataFrame(
            {
                "email": [labeller_email],
                "CardCode": [cardcode],
                "feedback": [feedback_val],
                "reason": [reason_val],
            }
        )

        df_label = pd.concat([df_submit, df_label], ignore_index=True)
        df_label.to_csv(LABEL_PATH, index=False)
        st.success("Thank you for your response!!!")


st.subheader("All label data")
st.dataframe(df_label, hide_index=True, use_container_width=True)
