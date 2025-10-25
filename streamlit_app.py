import streamlit as st
from openai import OpenAI
import cpsat
# Show title and description.
st.title("📄 Fire shifts scheduler")
st.write(
    "Copy and paste your monthly shift schedule and let the tool work out the necessary types of work! "
    # "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
# openai_api_key = st.text_input("OpenAI API Key", type="password")
data = """name          1	4	7	10	13	16	19	22	25	28	31
ΠΟΤΗΡΑΣ	Ρ	. 	Ρ	 .	 .	. 	Ρ	 .	Ρ	Ρ	 .
ΜΑΚΡΗΣ	 .	Ρ	 .	. 	Α	 .	 .	 .	 .	Α	Α
ΓΩΓΟΣ	Ρ	.	Ρ	 .	 .	Ρ	 .	.	. 	. 	Ρ
ΧΑΡΙΤΙΔΗΣ	 .	.	 .	 .	 .	 	Ρ	Ρ	Ρ	 .	Ρ .
ΤΣΙΩΤΡΑΣ	Ρ	.	Ρ	Ρ	 .	 .	. 	Ρ	 .	 .	 .
ΒΕΣΚΟΣ	 .	Ρ	 .	Α	Α	Ρ	 .	 .	. 	 .	 .
ΚΙΟΣΣΕΣ	 .	Ρ	. 	 .	Ρ	 .	Ρ	 .	 .	Ρ	 .
ΛΑΖΑΡΙΔΗΣ	.	 .	 .	Ρ	 .	Ρ	 .	Ρ	Ρ	 .	 .
"""
pasted = st.text_area("Paste your shifts here", placeholder=data, height="content")

scheduler = cpsat.Fireshifts(data)
# st.button(label, key=None, help=None, on_click=None, args=None, 
# kwargs=None, *, type="secondary", icon=None, disabled=False, 
# use_container_width=None, width="content")

# results = None
# dis = False
# done = False
# def schedule():
#     global dis, done, results
#     dis = True
#     scheduler.create_model()
#     scheduler.solve()
#     results=scheduler.get_results()
#     dis=False
#     done = True

# st.button("Schedule", on_click=schedule, disabled=dis, )
# if done:
#     schedule_df, summary_df = scheduler.get_results()
#     st.info(schedule_df)
#     st.info(summary_df)

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
    