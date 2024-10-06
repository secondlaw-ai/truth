import streamlit as st
import pandas as pd
import altair as alt
from truth.tools.discussion_parser import DiscussionParser
from truth import VerifierAgent


def visualize_metrics(metrics):
    st.subheader("Discussion Metrics")

    # Participation Overview
    col1, col2, col3 = st.columns(3)
    col1.metric("Unique Users", metrics["unique_users"])
    col2.metric("Total Messages", metrics["total_messages"])
    col3.metric("Time Span", metrics["time_span"])

    # Split screen into two columns
    col1, col2 = st.columns(2)

    # P-Value Distribution
    with col1:
        st.subheader("P-Value Distribution")
        p_value_data = pd.DataFrame(
            list(metrics["p_value_distribution"].items()), columns=["P-Value", "Count"]
        )
        p_value_chart = (
            alt.Chart(p_value_data)
            .mark_arc()
            .encode(theta="Count", color="P-Value", tooltip=["P-Value", "Count"])
            .properties(width=180, height=180)
        )
        st.altair_chart(p_value_chart, use_container_width=True)

    # Evidence and Rationale
    with col2:
        st.subheader("Evidence and Rationale")
        st.metric("Evidence Percentage", f"{metrics['evidence_percentage']:.1f}%")
        st.progress(metrics["evidence_percentage"] / 100)
        st.metric("Rationale Percentage", f"{metrics['rationale_percentage']:.1f}%")
        st.progress(metrics["rationale_percentage"] / 100)
        st.metric(
            "Evidence with Links", f"{metrics['evidence_with_links_percentage']:.1f}%"
        )

    # Resolution Status
    status_col, p_value_col = st.columns(2)
    with status_col:
        st.info(f"Status: {metrics['resolution_status']}")
    with p_value_col:
        st.success(
            f"Most Common P-Value: {metrics['most_common_p_value'][0]} ({metrics['most_common_p_value'][1]} votes)"
        )


def verify_votes(parsed_data, selected_model):
    st.header("Vote Verification Results")
    agent = VerifierAgent(model=selected_model)

    for i, message in enumerate(parsed_data["messages"]):
        st.subheader(f"Message {i+1} - User: {message.get('user', 'Unknown')}")
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"Timestamp: {message.get('timestamp', 'Unknown')}")
            st.write(f"P value submitted: {message.get('P', 'Not specified')}")

        with col2:
            with st.spinner("Verifying vote..."):
                res = agent.verify_uma_vote(
                    contract_description=parsed_data["description"], message=message
                )

            result_color = "green" if res["is_correct"] else "red"
            st.markdown(
                f"<h4 style='color: {result_color};'>{'Correct' if res['is_correct'] else 'Incorrect'}</h4>",
                unsafe_allow_html=True,
            )
            st.write(f"Confidence: {res['confidence']}")
            st.write(f"Explanation: {res['explanation']}")

        with st.expander("Show full message"):
            st.json(message)

        st.divider()


def main():
    st.set_page_config(layout="wide", page_title="UMA Vote Verifier Demo")

    st.title("UMA Truthteller")

    # Create two columns for the top section
    input_col, metrics_col = st.columns(2)

    with input_col:
        st.header("Input")
        # Backend model selection
        model_options = ["mistral-small-latest", "mistral-large-latest"]
        selected_model = st.selectbox("Select Backend Model", model_options)

        # Input field for contract description
        contract_description = st.text_area("Contract Discussion", "", height=300)

        # Submit button
        if st.button("Evaluate"):
            if contract_description:
                with st.spinner("Parsing discussion and calculating metrics..."):
                    parser = DiscussionParser(model=selected_model)
                    parsed = parser.parse_from_str(contract_description)
                    metrics = parser.calculate_metrics()

                # Store data in session state
                st.session_state.metrics = metrics
                st.session_state.parsed = parsed
                st.session_state.selected_model = selected_model
            else:
                st.warning("Please enter a contract discussion before submitting.")
    with metrics_col:
        if "metrics" in st.session_state:
            visualize_metrics(st.session_state.metrics)

    # Full width section for verification results
    if "parsed" in st.session_state:
        verify_votes(st.session_state.parsed, st.session_state.selected_model)

    # Display raw parsed data (optional)
    if "parsed" in st.session_state:
        with st.expander("Show Raw Parsed Data"):
            st.json(st.session_state.parsed)


if __name__ == "__main__":
    main()
