import streamlit as st
import pandas as pd
import re
import roman
from datetime import timedelta
from io import BytesIO

# ------------------------------------------------------
# دالة لتقسيم الـ Sequence بنفس المنطق الموجود عندك
def custom_split(seq):
    return '-'.join(re.findall(r'[A-Za-z]\d*|\d+|[A-Za-z]', str(seq)))


# ------------------------------------------------------
# تحضير ملف Schedule Time Input
def prepare_schedule_time(subjects_df, num_periods, schedule_times, withdrawn_subjects):
    subjects_df['Sequence'] = subjects_df['Sequence'].apply(custom_split)

    # map لكل وقت سحب برقم
    time_to_number_map = {time: i + 1 for i, time in enumerate(schedule_times)}

    data = []
    for subject in subjects_df.to_dict('records'):
        if subject["Subject"] in withdrawn_subjects:
            continue
        sequence = subject["Sequence"].split("-")
        for period in range(1, num_periods + 1):
            formulation = sequence[period - 1]
            for time in schedule_times:
                time_number = time_to_number_map[time]
                data.append({
                    "Subject": subject["Subject"],
                    "Sequence": subject["Sequence"],
                    "Formulation": formulation,
                    "Time": time,
                    "Period": period,
                    "Time Number": time_number
                })

    df = pd.DataFrame(data)
    return df, time_to_number_map


# ------------------------------------------------------
# تحضير ملف Actual Time Input
def prepare_actual_time(subjects_df, variation_df, schedule_times):
    time_to_number_map = {i + 1: time for i, time in enumerate(schedule_times)}

    variation_df['Study Stage (Period)'] = variation_df['Study Stage (Period)'].apply(lambda x: roman.fromRoman(str(x)))
    
    results = []
    for _, row in variation_df.iterrows():
        try:
            schedule_time = row['Schedule Time']
            actual_time = row['Actual Time']
            sample_no = row['Sample No.']

            if sample_no not in time_to_number_map:
                continue

            original_time = time_tnumber_map[sample_no]

            diff = timedelta(hours=actual_time.hour, minutes=actual_time.minute, seconds=actual_time.second) - \
                   timedelta(hours=schedule_time.hour, minutes=schedule_time.minute, seconds=schedule_time.second)
            diff = diff.total_seconds() / 3600
            adjustment = diff
            is_late = adjustment > 0
            adjusted_time = original_time + adjustment if is_late else original_time - abs(adjustment)

            results.append({
                "Study Stage (Period)": row['Study Stage (Period)'],
                "Subject Randomization No.": row['Subject Randomization No.'],
                "Sample No.": sample_no,
                "Original Schedule Time": original_time,
                "Adjusted Time": round(adjusted_time, 2)
            })
        except:
            continue

    results_df = pd.DataFrame(results)

    merged_table = subjects_df.merge(results_df,
                                     left_on=['Period', 'Subject', 'Time Number'],
                                     right_on=['Study Stage (Period)', 'Subject Randomization No.', 'Sample No.'],
                                     how='left')

    final_results_df = pd.DataFrame(merged_table)
    final_results_df['Time'] = final_results_df['Adjusted Time'].fillna(final_results_df['Time'])
    final_results_df = final_results_df.drop(columns=['Adjusted Time', 'Original Schedule Time',
                                                     'Sample No.', 'Subject Randomization No.', 'Study Stage (Period)'])
    final_results_df = final_results_df.drop(columns=["Time Number"])
    final_results_df.insert(4, 'concentration', "")
    final_results_df['Sequence'] = final_results_df['Sequence'].str.replace(r'\s*-\s*', '', regex=True)

    return final_results_df


# ------------------------------------------------------
# Streamlit UI
st.title("Phoenix WinNonlin Input Generator")

mode = st.radio("اختر نوع التحضير:", ["📅 Schedule Time Input", "⏰ Actual Time Input"])

if mode == "📅 Schedule Time Input":
    st.subheader("تحضير Schedule Time Input")
    file = st.file_uploader("ارفع ملف Subjects (Excel)", type=["xlsx", "xls"])

    if file:
        subjects_df = pd.read_excel(file)

        num_periods = st.number_input("عدد الفترات:", min_value=1, step=1, value=2)
        schedule_times_input = st.text_input("Schedule times (افصل بينها بفواصل):", "0.5,1.0,2.0")
        withdrawn_input = st.text_input("Withdrawn subjects (افصل بينها بفواصل):", "")

        if st.button("تحضير الملف"):
            schedule_times = [float(t.strip()) for t in schedule_times_input.split(",")]
            withdrawn_subjects = [int(w.strip()) for w in withdrawn_input.split(",")] if withdrawn_input else []

            df, mapping = prepare_schedule_time(subjects_df, num_periods, schedule_times, withdrawn_subjects)

            st.success("تم تحضير الملف بنجاح ✅")
            st.dataframe(df.head())

            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')
            st.download_button("⬇️ تحميل الملف", buffer.getvalue(), "schedule_time_input.xlsx")

            st.write("**Time to Number Mapping:**")
            st.json(mapping)


elif mode == "⏰ Actual Time Input":
    st.subheader("تحضير Actual Time Input")
    file_subjects = st.file_uploader("ارفع ملف Schedual_Time_Input (Excel)", type=["xlsx", "xls"], key="subjects")
    file_variation = st.file_uploader("ارفع ملف Variations (Excel)", type=["xlsx", "xls"], key="variation")

    schedule_times_input = st.text_input("Schedule times (افصل بينها بفواصل):", "0.5,1.0,2.0")

    if file_subjects and file_variation:
        if st.button("تحضير الملف"):
            subjects_df = pd.read_excel(file_subjects)
            variation_df = pd.read_excel(file_variation)

            schedule_times = [float(t.strip()) for t in schedule_times_input.split(",")]

            final_df = prepare_actual_time(subjects_df, variation_df, schedule_times)

            st.success("تم تعديل الأوقات بنجاح ✅")
            st.dataframe(final_df.head())

            buffer = BytesIO()
            final_df.to_excel(buffer, index=False, engine='openpyxl')
            st.download_button("⬇️ تحميل الملف", buffer.getvalue(), "actual_time_input.xlsx")
