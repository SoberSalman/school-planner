import streamlit as st
import sqlite3
import pandas as pd

# Use the full page width for a better timetable layout
st.set_page_config(page_title="Visual Timetable", page_icon="🗓️", layout="wide")

st.title("🗓️ Visual School Timetable")

@st.cache_data
def load_master_data():
    """
    Loads all reference data (names for teachers, subjects, etc.) for mapping.
    Using .set_index() makes mapping IDs to names extremely fast and efficient.
    """
    with sqlite3.connect("school_planner.db") as conn:
        teachers = pd.read_sql("SELECT teacher_id, teacher_name FROM teachers", conn).set_index('teacher_id')
        subjects = pd.read_sql("SELECT subject_id, subject_name FROM subjects", conn).set_index('subject_id')
        classrooms = pd.read_sql("SELECT classroom_id, classroom_name FROM classrooms", conn).set_index('classroom_id')
        sections = pd.read_sql("SELECT section_id, 'Grade ' || grade || '-' || section_name as section_full_name FROM grade_sections", conn).set_index('section_id')
    return teachers, subjects, classrooms, sections

def generate_timetable_html(df, filter_type, filter_value):
    """
    This is the new, robust function to generate a styled HTML grid for the timetable.
    It correctly handles data lookup and HTML construction.
    """
    st.subheader(f"Timetable for: {filter_value}")

    # --- Step 1: Filter the data and create an explicit copy ---
    # This is the crucial fix for both the SettingWithCopyWarning and the filtering bug.
    if filter_type == 'View by: Grade/Section':
        filtered_df = df[df['section_full_name'] == filter_value].copy()
    elif filter_type == 'View by: Teacher':
        filtered_df = df[df['teacher_name'] == filter_value].copy()
    else:  # Classroom
        filtered_df = df[df['classroom_name'] == filter_value].copy()

    if filtered_df.empty:
        st.warning("No classes scheduled for this selection.")
        return

    # --- Step 2: Define what unique information to display in each cell ---
    if filter_type == 'View by: Grade/Section':
        filtered_df['cell_line_1'] = filtered_df['subject_name']
        filtered_df['cell_line_2'] = "w/ " + filtered_df['teacher_name']
        filtered_df['cell_line_3'] = "@ " + filtered_df['classroom_name']
    elif filter_type == 'View by: Teacher':
        filtered_df['cell_line_1'] = filtered_df['subject_name']
        filtered_df['cell_line_2'] = "for " + filtered_df['section_full_name']
        filtered_df['cell_line_3'] = "@ " + filtered_df['classroom_name']
    else:  # Classroom
        filtered_df['cell_line_1'] = filtered_df['subject_name']
        filtered_df['cell_line_2'] = "for " + filtered_df['section_full_name']
        filtered_df['cell_line_3'] = "w/ " + filtered_df['teacher_name']

    # --- Step 3: Pivot the data reliably ---
    # This structure is designed to be easily looked up in the next step.
    pivot = filtered_df.pivot_table(
        index='time_slot',
        columns='day_of_week',
        values=['cell_line_1', 'cell_line_2', 'cell_line_3'],
        aggfunc='first'
    )

    # --- Step 4: Build the HTML Grid with robust data lookup ---
    html = "<div class='timetable-grid'>"
    headers = ["Time", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for header in headers:
        html += f"<div class='grid-header'>{header}</div>"

    for time_slot in range(1, 9):  # 8 time slots
        html += f"<div class='grid-timeslot'>Slot {time_slot}</div>"
        for day in range(1, 6):  # 5 days
            # Robustly check if data exists for this day and slot
            if ('cell_line_1', day) in pivot.columns and time_slot in pivot.index:
                cell_data_1 = pivot.loc[time_slot, ('cell_line_1', day)]
                # Check if the specific cell has a value (it might be NaN)
                if pd.notna(cell_data_1):
                    cell_data_2 = pivot.loc[time_slot, ('cell_line_2', day)]
                    cell_data_3 = pivot.loc[time_slot, ('cell_line_3', day)]
                    html += f"""
                    <div class='grid-cell'>
                        <span class='subject'>{cell_data_1}</span>
                        <span class='teacher'>{cell_data_2}</span>
                        <span class='room'>{cell_data_3}</span>
                    </div>
                    """
                else:
                    html += "<div class='grid-cell'></div>"  # Empty cell for NaN
            else:
                html += "<div class='grid-cell'></div>"  # Empty cell if no class

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# --- Main UI Logic ---
if st.session_state.get('schedule_df') is None:
    st.warning("No schedule has been generated yet. Please go to the main page to generate one.", icon="⚠️")
else:
    teachers, subjects, classrooms, sections = load_master_data()

    # Efficiently create the full schedule DataFrame for display using .map()
    schedule = st.session_state.schedule_df.copy()
    schedule['teacher_name'] = schedule['teacher_id'].map(teachers['teacher_name'])
    schedule['subject_name'] = schedule['subject_id'].map(subjects['subject_name'])
    schedule['classroom_name'] = schedule['classroom_id'].map(classrooms['classroom_name'])
    schedule['section_full_name'] = schedule['section_id'].map(sections['section_full_name'])

    st.header("🔎 Filter Timetable")
    filter_type = st.selectbox("View by:", ['View by: Grade/Section', 'View by: Teacher', 'View by: Classroom'])

    # Dynamically populate the second selectbox based on the first
    if filter_type == 'View by: Grade/Section':
        options = sorted(schedule['section_full_name'].unique())
        filter_value = st.selectbox("Select a Section:", options)
    elif filter_type == 'View by: Teacher':
        options = sorted(schedule['teacher_name'].unique())
        filter_value = st.selectbox("Select a Teacher:", options)
    else:  # Classroom
        options = sorted(schedule['classroom_name'].unique())
        filter_value = st.selectbox("Select a Classroom:", options)

    if filter_value:
        generate_timetable_html(schedule, filter_type, filter_value)