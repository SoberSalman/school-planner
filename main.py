from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import pandas as pd
import time
import plotly.express as px
import collections

# Import the new, powerful GA solver
from ai.utils import load_data, format_solution, save_schedule_to_db
from ai.genetic_solver import solve_with_ga
from ai.utils import TIME_SLOTS_PER_DAY, DAYS_OF_WEEK

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_schedule_conflicts(schedule_df):
    """Detects and returns a list of conflicts from a generated schedule."""
    if schedule_df is None: return []
    
    conflicts = []
    teacher_slots = collections.defaultdict(list)
    room_slots = collections.defaultdict(list)
    section_slots = collections.defaultdict(list)

    # Group classes by timeslot
    for _, row in schedule_df.iterrows():
        teacher_key = (row['teacher_id'], row['day_of_week'], row['time_slot'])
        room_key = (row['classroom_id'], row['day_of_week'], row['time_slot'])
        section_key = (row['section_id'], row['day_of_week'], row['time_slot'])
        
        class_info = f"{row['subject_name']} for {row['section_full_name']}"
        teacher_slots[teacher_key].append(class_info)
        room_slots[room_key].append(f"Room {row['classroom_name']}")
        section_slots[section_key].append(f"Section {row['section_full_name']}")

    # Check for slots used more than once
    for key, classes in teacher_slots.items():
        if len(classes) > 1:
            conflicts.append(f"Teacher Conflict: Day {key[1]}, Slot {key[2]} - Teacher is double-booked with: {'; '.join(classes)}")
    for key, classes in room_slots.items():
        if len(classes) > 1:
            conflicts.append(f"Room Conflict: Day {key[1]}, Slot {key[2]} - Room is double-booked.")
    for key, classes in section_slots.items():
        if len(classes) > 1:
            conflicts.append(f"Section Conflict: Day {key[1]}, Slot {key[2]} - Section has overlapping classes.")
            
    return conflicts


def get_analysis_data(schedule_df):
    """
    Calculates all necessary KPIs, chart data, and resource insights
    from a generated schedule DataFrame.
    """
    if schedule_df is None or schedule_df.empty:
        return {}

    # --- Step 1: Load Base Data for Analysis ---
    with sqlite3.connect("school_planner.db") as conn:
        teachers_df = pd.read_sql("SELECT teacher_id, teacher_name, max_weekly_hours FROM teachers", conn)
        # Load classrooms with their type names directly using a JOIN
        classrooms_df = pd.read_sql("""
            SELECT c.classroom_id, c.classroom_name, ct.type_name 
            FROM classrooms c 
            JOIN classroom_types ct ON c.type_id = ct.type_id
        """, conn)

    # --- Step 2: Teacher Utilization Analysis ---
    # Count how many hours each teacher is scheduled
    teacher_hours = schedule_df.groupby('teacher_id').size().reset_index(name='scheduled_hours')
    # Merge with the base teacher data
    teacher_util = teachers_df.merge(teacher_hours, on='teacher_id', how='left').fillna(0)
    # Calculate utilization percentage
    teacher_util['utilization_pct'] = ((teacher_util['scheduled_hours'] / teacher_util['max_weekly_hours']) * 100).round(1)

    # --- Step 3: Classroom Utilization Analysis ---
    # Define total available time slots in a week
    total_available_slots = len(DAYS_OF_WEEK) * TIME_SLOTS_PER_DAY
    # Count how many hours each classroom is used
    classroom_hours = schedule_df.groupby('classroom_id').size().reset_index(name='scheduled_hours')
    # Merge with the base classroom data
    classroom_util = classrooms_df.merge(classroom_hours, on='classroom_id', how='left').fillna(0)
    # Calculate utilization percentage
    classroom_util['utilization_pct'] = ((classroom_util['scheduled_hours'] / total_available_slots) * 100).round(1)

    # --- Step 4: Prepare Data for the UI ---
    # Identify high and low demand rooms
    high_demand_rooms = classroom_util[classroom_util['utilization_pct'] > 85].to_dict('records')
    low_demand_rooms = classroom_util[classroom_util['utilization_pct'] < 25].to_dict('records')

    # Create charts using Plotly
    fig_teacher_workload = px.histogram(
        teacher_util, 
        x='scheduled_hours', 
        title='Teacher Workload Distribution',
        labels={'scheduled_hours': 'Weekly Hours Scheduled', 'count': 'Number of Teachers'}
    )
    
    avg_util_by_type = classroom_util.groupby('type_name')['utilization_pct'].mean().round(1).reset_index()
    fig_room_util = px.bar(
        avg_util_by_type, 
        x='type_name', 
        y='utilization_pct', 
        title='Average Utilization by Room Type', 
        color='type_name',
        labels={'type_name': 'Room Type', 'utilization_pct': 'Average Utilization (%)'}
    )
    
    # --- Step 5: Return a Dictionary with All Results ---
    return {
        "kpi_total_classes": len(schedule_df),
        "kpi_active_teachers": schedule_df['teacher_id'].nunique(),
        "kpi_utilized_rooms": schedule_df['classroom_id'].nunique(),
        "teacher_workload_chart": fig_teacher_workload.to_html(full_html=False, include_plotlyjs='cdn'),
        "room_util_chart": fig_room_util.to_html(full_html=False, include_plotlyjs='cdn'),
        "high_demand_rooms": high_demand_rooms,
        "low_demand_rooms": low_demand_rooms,
    }


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
async def generate_schedule(request: Request, dummy_form_input: str = Form(None)):
    """Handles the form submission, runs the GA, and returns the page with results."""
    # The rest of the function remains exactly the same.
    log_messages = []
    def logger(message):
        print(message)
        log_messages.append(message)

    conn = sqlite3.connect("school_planner.db")
    teachers_df, classrooms_df, curriculum_df = load_data(conn)
    
    logger("--- Running Advanced Genetic Algorithm ---")
    solution = solve_with_ga(teachers_df, classrooms_df, curriculum_df)

    full_schedule_df = None
    analysis_data = {}
    conflicts = []
    if solution:
        schedule_df = format_solution(solution)
        save_schedule_to_db(conn, schedule_df)
        
        # Create the full DataFrame for display
        # ... (same data mapping logic as before) ...
        # (This block for creating full_schedule_df is the same)
        with sqlite3.connect("school_planner.db") as conn_display:
            teachers_map = pd.read_sql("SELECT teacher_id, teacher_name FROM teachers", conn_display).set_index('teacher_id')
            subjects_map = pd.read_sql("SELECT subject_id, subject_name FROM subjects", conn_display).set_index('subject_id')
            classrooms_map = pd.read_sql("SELECT classroom_id, classroom_name FROM classrooms", conn_display).set_index('classroom_id')
            sections_map = pd.read_sql("SELECT section_id, 'Grade ' || grade || '-' || section_name as name FROM grade_sections", conn_display).set_index('section_id')
        
        full_schedule_df = schedule_df.copy()
        full_schedule_df['teacher_name'] = full_schedule_df['teacher_id'].map(teachers_map['teacher_name'])
        full_schedule_df['subject_name'] = full_schedule_df['subject_id'].map(subjects_map['subject_name'])
        full_schedule_df['classroom_name'] = full_schedule_df['classroom_id'].map(classrooms_map['classroom_name'])
        full_schedule_df['section_full_name'] = full_schedule_df['section_id'].map(sections_map['name'])
        
        analysis_data = get_analysis_data(full_schedule_df)
        conflicts = get_schedule_conflicts(full_schedule_df) # Get conflicts
    else:
        logger("GA failed to find a solution.")

    conn.close()

    # Pass everything back to the template
    teachers_list, sections_list, classrooms_list = [], [], []
    if full_schedule_df is not None:
        teachers_list = sorted(full_schedule_df['teacher_name'].unique())
        sections_list = sorted(full_schedule_df['section_full_name'].unique())
        classrooms_list = sorted(full_schedule_df['classroom_name'].unique())
        
    return templates.TemplateResponse("index.html", {
        "request": request,
        "teachers": teachers_list,
        "sections": sections_list,
        "classrooms": classrooms_list,
        "schedule": full_schedule_df.to_dict('records') if full_schedule_df is not None else None,
        "analysis": analysis_data,
        "logs": "\n".join(log_messages),
        "conflicts": conflicts
    })