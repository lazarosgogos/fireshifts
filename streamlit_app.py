import streamlit as st
from openai import OpenAI
import cpsat
# Show title and description.
st.title("📄 Fire shifts scheduler 🔥")
st.write(
    "Copy and paste your monthly shift schedule and let the tool work out the necessary types of work! "
    # "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

data = """name			1	4	7	10	13	16	19	22	25	28	31
ΠΟΤΗΡΑΣ		P	. 	P	 .	 .	. 	P	 .	P	P	 .
ΜΑΚΡΗΣ		.	P	 .	. 	A	 .	 .	 .	.	A	A
ΓΩΓΟΣ			P	.	P	 .	 .	P	 .	.	. 	. 	P
ΧΑΡΙΤΙΔΗΣ		.	.	 .	 .	 . 	P	P	P	.	P	.
ΤΣΙΩΤΡΑΣ		P	.	P	P	 .	.	. 	P	.	.	.
ΒΕΣΚΟΣ		.	P	 .	A	A	P	.	.	. 	.	.
ΚΙΟΣΣΕΣ		.	P	. 	 .	P	.	P	.	.	P	.
ΛΑΖΑΡΙΔΗΣ	.	 .	 .	P	.	P	.	P	P	.	.
ΚΕΣΙΔΗΣ 	.	 .	 .	P	.	P	.	P	P	.	.
"""
pasted = st.text_area("Paste your shifts here", placeholder=data, height="content")

scheduler = cpsat.Fireshifts(data)

if st.button("Schedule"):
    pasted = pasted if pasted else data
    scheduler = cpsat.Fireshifts(pasted)
    scheduler.create_model()
    scheduler.solve()
    schedule_df, summary_df = scheduler.get_results()
    st.info("Schedule")
    st.dataframe(schedule_df)
    st.info("Summary")
    st.dataframe(summary_df)
    