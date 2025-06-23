import sqlite3
import pandas as pd

DB_NAME = "school_planner.db"
# Define the school's schedule parameters
DAYS_OF_WEEK = range(1, 6)  # 1=Monday, 5=Friday
TIME_SLOTS_PER_DAY = 8      # e.g., 8 periods from 9am to 4pm

def load_data(conn):
    """Loads all required data from the database into pandas DataFrames."""
    print("Loading data from database...")
    
    # Load available teachers and their specializations
    teachers_query = """
    SELECT t.teacher_id, ts.subject_id
    FROM teachers t
    JOIN teacher_specializations ts ON t.teacher_id = ts.teacher_id
    WHERE t.is_available = 1;
    """
    teachers_df = pd.read_sql_query(teachers_query, conn)
    
    # Load available classrooms and their types
    classrooms_query = """
    SELECT c.classroom_id, c.type_id
    FROM classrooms c
    WHERE c.is_available = 1;
    """
    classrooms_df = pd.read_sql_query(classrooms_query, conn)

    # Load curriculum requirements
    curriculum_query = """
    SELECT cur.section_id, cur.subject_id, cur.weekly_hours, cur.required_classroom_type_id
    FROM curriculum cur;
    """
    curriculum_df = pd.read_sql_query(curriculum_query, conn)


    # --- FIX STARTS HERE: Handle missing values and then enforce types ---
    print("Cleaning data and enforcing types...")

    # Step 1: Identify and drop rows with missing essential information
    # This is the most critical step to prevent the conversion error.
    initial_curriculum_rows = len(curriculum_df)
    curriculum_df.dropna(
        subset=['section_id', 'subject_id', 'required_classroom_type_id', 'weekly_hours'],
        inplace=True
    )
    if len(curriculum_df) < initial_curriculum_rows:
        print(f"Warning: Dropped {initial_curriculum_rows - len(curriculum_df)} rows from curriculum due to missing data.")

    # Step 2: Now that NaNs are gone, we can safely convert to integers.
    try:
        # For teachers_df
        teachers_df['teacher_id'] = teachers_df['teacher_id'].astype(int)
        teachers_df['subject_id'] = teachers_df['subject_id'].astype(int)

        # For classrooms_df
        classrooms_df['classroom_id'] = classrooms_df['classroom_id'].astype(int)
        classrooms_df['type_id'] = classrooms_df['type_id'].astype(int)

        # For curriculum_df
        curriculum_df['section_id'] = curriculum_df['section_id'].astype(int)
        curriculum_df['subject_id'] = curriculum_df['subject_id'].astype(int)
        curriculum_df['required_classroom_type_id'] = curriculum_df['required_classroom_type_id'].astype(int)
        
        # Also handle the weekly_hours column here
        curriculum_df['weekly_hours'] = curriculum_df['weekly_hours'].round().astype(int)

    except Exception as e:
        print(f"Error during data type conversion: {e}")
        # Optional: Print info about which column is causing issues
        for col in curriculum_df.columns:
            if curriculum_df[col].isnull().any():
                print(f"Column '{col}' still contains null values.")
        raise # Re-raise the exception to stop execution
    # --- FIX ENDS HERE ---

    print("Data loaded and cleaned successfully.")
    return teachers_df, classrooms_df, curriculum_df

def save_schedule_to_db(conn, schedule_df):
    """Saves the generated schedule DataFrame to the database."""
    if schedule_df is None or schedule_df.empty:
        print("No schedule to save.")
        return

    print("Saving schedule to database...")
    cursor = conn.cursor()
    # Clear the old schedule before inserting the new one
    cursor.execute("DELETE FROM schedule;")
    
    schedule_df.to_sql('schedule', conn, if_exists='append', index=False)
    conn.commit()
    print(f"{len(schedule_df)} class slots have been scheduled and saved.")

def format_solution(solution_dict):
    """Converts a solver's solution dictionary to a pandas DataFrame."""
    if not solution_dict:
        return None
        
    schedule_data = []
    for (section_id, subject_id, _), (teacher_id, classroom_id, day, time_slot) in solution_dict.items():
        schedule_data.append({
            'section_id': section_id,
            'subject_id': subject_id,
            'teacher_id': teacher_id,
            'classroom_id': classroom_id,
            'day_of_week': day,
            'time_slot': time_slot
        })
    return pd.DataFrame(schedule_data)