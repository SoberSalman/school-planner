import sqlite3
import pandas as pd

DB_NAME = "school_planner.db"

def create_tables(conn):
    """Creates all necessary tables based on the schema."""
    cursor = conn.cursor()
    cursor.executescript("""
        DROP TABLE IF EXISTS teachers;
        CREATE TABLE teachers (
            teacher_id INTEGER PRIMARY KEY,
            teacher_name TEXT NOT NULL,
            max_weekly_hours INTEGER NOT NULL,
            is_available BOOLEAN DEFAULT 1
        );

        DROP TABLE IF EXISTS subjects;
        CREATE TABLE subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT UNIQUE NOT NULL
        );

        DROP TABLE IF EXISTS teacher_specializations;
        CREATE TABLE teacher_specializations (
            teacher_id INTEGER,
            subject_id INTEGER,
            PRIMARY KEY (teacher_id, subject_id),
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        );

        DROP TABLE IF EXISTS classroom_types;
        CREATE TABLE classroom_types (
            type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT UNIQUE NOT NULL
        );

        DROP TABLE IF EXISTS classrooms;
        CREATE TABLE classrooms (
            classroom_id INTEGER PRIMARY KEY,
            classroom_name TEXT NOT NULL,
            type_id INTEGER,
            capacity INTEGER NOT NULL,
            is_available BOOLEAN DEFAULT 1,
            FOREIGN KEY (type_id) REFERENCES classroom_types(type_id)
        );

        DROP TABLE IF EXISTS grade_sections;
        CREATE TABLE grade_sections (
            section_id INTEGER PRIMARY KEY,
            grade INTEGER NOT NULL,
            section_name TEXT NOT NULL
        );

        DROP TABLE IF EXISTS curriculum;
        CREATE TABLE curriculum (
            curriculum_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            subject_id INTEGER,
            weekly_hours INTEGER NOT NULL,
            required_classroom_type_id INTEGER,
            FOREIGN KEY (section_id) REFERENCES grade_sections(section_id),
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
            FOREIGN KEY (required_classroom_type_id) REFERENCES classroom_types(type_id)
        );

        DROP TABLE IF EXISTS schedule;
        CREATE TABLE schedule (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            teacher_id INTEGER,
            subject_id INTEGER,
            classroom_id INTEGER,
            day_of_week INTEGER,
            time_slot INTEGER,
            FOREIGN KEY (section_id) REFERENCES grade_sections(section_id),
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
            FOREIGN KEY (classroom_id) REFERENCES classrooms(classroom_id)
        );
    """)
    conn.commit()
    print("Tables created successfully.")

def populate_tables(conn):
    """Populates tables from the generated CSV files."""
    # Load base data
    df_teachers = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/teachers.csv")
    df_subjects = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/subjects.csv")
    df_classroom_types = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/classroom_types.csv")
    df_classrooms = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/classrooms.csv")
    df_grade_sections = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/grade_sections.csv")
    df_specializations = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/teacher_specializations.csv")
    df_curriculum = pd.read_csv("/home/salman/Desktop/Projects/school-resource-planner/curriculum.csv")

    # Insert data into tables
    df_teachers.to_sql("teachers", conn, if_exists="append", index=False)
    df_subjects.to_sql("subjects", conn, if_exists="append", index=False)
    df_classroom_types.to_sql("classroom_types", conn, if_exists="append", index=False)
    df_grade_sections.to_sql("grade_sections", conn, if_exists="append", index=False)
    
    # --- Populate join/FK tables with correct IDs ---
    # Create mapping dictionaries
    subjects_map = pd.read_sql("SELECT subject_id, subject_name FROM subjects", conn).set_index("subject_name").to_dict()['subject_id']
    types_map = pd.read_sql("SELECT type_id, type_name FROM classroom_types", conn).set_index("type_name").to_dict()['type_id']

    # Classrooms
    df_classrooms['type_id'] = df_classrooms['type_name'].map(types_map)
    df_classrooms[['classroom_id', 'classroom_name', 'type_id', 'capacity']].to_sql("classrooms", conn, if_exists="append", index=False)

    # Specializations
    df_specializations['subject_id'] = df_specializations['subject_name'].map(subjects_map)
    df_specializations[['teacher_id', 'subject_id']].to_sql("teacher_specializations", conn, if_exists="append", index=False)

    # Curriculum
    df_curriculum['subject_id'] = df_curriculum['subject_name'].map(subjects_map)
    df_curriculum['required_classroom_type_id'] = df_curriculum['required_classroom_type'].map(types_map)
    df_curriculum[['section_id', 'subject_id', 'weekly_hours', 'required_classroom_type_id']].to_sql("curriculum", conn, if_exists="append", index=False)
    
    print("All tables populated successfully.")

def main():
    conn = sqlite3.connect(DB_NAME)
    create_tables(conn)
    populate_tables(conn)
    conn.close()
    print(f"Database '{DB_NAME}' has been created and populated.")

if __name__ == "__main__":
    main()