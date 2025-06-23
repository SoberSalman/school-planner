import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from ai.utils import TIME_SLOTS_PER_DAY, DAYS_OF_WEEK

st.set_page_config(page_title="Resource Analysis", page_icon="📊", layout="wide")
st.title("📊 Resource & Performance Dashboard")

@st.cache_data
def load_base_data():
    """Loads teachers and classrooms base info."""
    with sqlite3.connect("school_planner.db") as conn:
        teachers = pd.read_sql("SELECT teacher_id, teacher_name, max_weekly_hours FROM teachers", conn)
        classrooms = pd.read_sql("SELECT c.classroom_id, c.classroom_name, ct.type_name FROM classrooms c JOIN classroom_types ct ON c.type_id = ct.type_id", conn)
    return teachers, classrooms

# --- UI Logic ---
if st.session_state.get('schedule_df') is None:
    st.warning("No schedule has been generated yet. Please go to the main page to generate one.", icon="⚠️")
else:
    schedule_df = st.session_state.schedule_df
    teachers_df, classrooms_df = load_base_data()
    
    # --- Key Performance Indicators (KPIs) ---
    st.header("📈 At a Glance")
    col1, col2, col3 = st.columns(3)
    total_classes = len(schedule_df)
    total_teachers = schedule_df['teacher_id'].nunique()
    total_rooms = schedule_df['classroom_id'].nunique()
    col1.metric("Total Scheduled Classes", f"{total_classes} hours")
    col2.metric("Active Teachers", f"{total_teachers}")
    col3.metric("Utilized Rooms", f"{total_rooms}")

    # --- Teacher Utilization Analysis ---
    st.header("👨‍🏫 Teacher Utilization")
    teacher_hours = schedule_df.groupby('teacher_id').size().reset_index(name='scheduled_hours')
    teacher_util = teachers_df.merge(teacher_hours, on='teacher_id', how='left').fillna(0)
    teacher_util['utilization_pct'] = ((teacher_util['scheduled_hours'] / teacher_util['max_weekly_hours']) * 100).round(1)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Top 5 Busiest Teachers")
        st.dataframe(teacher_util.sort_values('utilization_pct', ascending=False).head(5)[['teacher_name', 'scheduled_hours', 'utilization_pct']], hide_index=True)
        
        st.subheader("Top 5 Under-Utilized Teachers")
        st.dataframe(teacher_util[teacher_util['scheduled_hours'] > 0].sort_values('utilization_pct', ascending=True).head(5)[['teacher_name', 'scheduled_hours', 'utilization_pct']], hide_index=True)

    with c2:
        st.subheader("Distribution of Teacher Workload")
        fig = px.histogram(teacher_util, x='scheduled_hours', title='Number of Teachers per Scheduled Hour Count', labels={'scheduled_hours': 'Weekly Hours Scheduled'})
        st.plotly_chart(fig, use_container_width=True)

    # --- Classroom Utilization Analysis ---
    st.header("🏫 Classroom Utilization")
    total_available_slots = len(DAYS_OF_WEEK) * TIME_SLOTS_PER_DAY
    classroom_hours = schedule_df.groupby('classroom_id').size().reset_index(name='scheduled_hours')
    classroom_util = classrooms_df.merge(classroom_hours, on='classroom_id', how='left').fillna(0)
    classroom_util['utilization_pct'] = ((classroom_util['scheduled_hours'] / total_available_slots) * 100).round(1)

    c3, c4 = st.columns([2, 1])
    with c3:
        st.subheader("Utilization by Room Type")
        avg_util_by_type = classroom_util.groupby('type_name')['utilization_pct'].mean().round(1).reset_index()
        fig2 = px.bar(avg_util_by_type, x='type_name', y='utilization_pct', title='Average Utilization % by Room Type', color='type_name', labels={'type_name': 'Room Type', 'utilization_pct': 'Average Utilization (%)'})
        st.plotly_chart(fig2, use_container_width=True)
        
    with c4:
        st.subheader("Potential Bottlenecks")
        high_demand = classroom_util[classroom_util['utilization_pct'] > 80]
        st.warning("High-Demand Rooms (>80% Use)")
        st.dataframe(high_demand[['classroom_name', 'utilization_pct']], hide_index=True)

        st.subheader("Underutilized Assets")
        low_demand = classroom_util[classroom_util['utilization_pct'] < 25]
        st.info("Low-Usage Rooms (<25% Use)")
        st.dataframe(low_demand[['classroom_name', 'utilization_pct']], hide_index=True)