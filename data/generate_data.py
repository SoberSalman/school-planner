import openai
import pandas as pd
import json
import random

client = openai.OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

NUM_TEACHERS = 120
NUM_CLASSROOMS = 50
GRADES = range(1, 11)
SECTIONS = ['A', 'B', 'C']

SUBJECTS_LIST = [
    "Mathematics", "Physics", "Chemistry", "Biology", "English", "History",
    "Geography", "Physical Education (PE)", "Art", "Music", "Computer Science", "Nutrition"
]

CLASSROOM_TYPES_MAPPING = {
    "Normal Classroom": ["Mathematics", "English", "History", "Geography", "Art", "Music"],
    "Science Lab": ["Physics", "Chemistry", "Biology"],
    "PE Area": ["Physical Education (PE)"],
    "Computer Lab": ["Computer Science"],
    "Nutrition Kitchen": ["Nutrition"]
}


def generate_data_with_llm(prompt, temperature=0.7):
    """Calls the local LLM to generate data based on a prompt."""
    print(f"Sending prompt to LLM:\n---\n{prompt}\n---")
    try:
        completion = client.chat.completions.create(
            model="local-model",  # This value doesn't matter for LM Studio
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        response_content = completion.choices[0].message.content
        print(f"Received response:\n---\n{response_content}\n---")
        return response_content
    except Exception as e:
        print(f"Error communicating with LLM: {e}")
        return None
def generate_teachers():
    """Generates a list of teachers and their specializations."""
    prompt = f"""
    Generate a list of {NUM_TEACHERS} unique and diverse first and last names for school teachers.
    Format the output as a simple JSON array of strings. For example: ["John Doe", "Jane Smith"].
    """
    names_json_str = generate_data_with_llm(prompt)
    
    # --- FIX STARTS HERE ---
    # Clean the LLM response to remove Markdown code blocks before parsing
    if names_json_str:
        cleaned_json_str = names_json_str.strip().replace('```json', '').replace('```', '').strip()
        try:
            teacher_names = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON from LLM response for teachers: {e}")
            print(f"Problematic string: {cleaned_json_str}")
            return pd.DataFrame(), pd.DataFrame() # Return empty dataframes on failure
    else:
        return pd.DataFrame(), pd.DataFrame() # Return empty if LLM failed
    # --- FIX ENDS HERE ---

    teachers = []
    specializations = []
    teacher_id_counter = 1

    # Ensure we don't try to access more names than we received
    for name in teacher_names[:NUM_TEACHERS]:
        teachers.append({
            "teacher_id": teacher_id_counter,
            "teacher_name": name,
            "max_weekly_hours": random.randint(18, 25) # Standard teaching load
        })

        # Assign 1 to 3 specializations
        num_specializations = random.randint(1, 3)
        teacher_subjects = random.sample(SUBJECTS_LIST, num_specializations)
        for subject in teacher_subjects:
            specializations.append({
                "teacher_id": teacher_id_counter,
                "subject_name": subject
            })
        teacher_id_counter += 1

    return pd.DataFrame(teachers), pd.DataFrame(specializations)



def generate_classrooms():
    """Generates classrooms of different types."""
    # Define distribution
    num_labs = 8
    num_pe = 4
    num_kitchens = 2
    num_computer_labs = 6
    num_normal = NUM_CLASSROOMS - (num_labs + num_pe + num_kitchens + num_computer_labs)

    room_counts = {
        "Science Lab": num_labs,
        "PE Area": num_pe,
        "Nutrition Kitchen": num_kitchens,
        "Computer Lab": num_computer_labs,
        "Normal Classroom": num_normal
    }

    classrooms = []
    classroom_id_counter = 1
    for room_type, count in room_counts.items():
        for i in range(count):
            name = f"{room_type.replace(' ', '')}-{i+1}"
            capacity = 30 # Assume standard capacity
            if room_type == "PE Area":
                capacity = 60
            classrooms.append({
                "classroom_id": classroom_id_counter,
                "classroom_name": name,
                "type_name": room_type,
                "capacity": capacity
            })
            classroom_id_counter += 1
    return pd.DataFrame(classrooms)

def generate_curriculum():
    """Generates curriculum requirements for each grade-section."""
    # Create grade-sections first
    grade_sections = []
    section_id_counter = 1
    for grade in GRADES:
        for section in SECTIONS:
            grade_sections.append({
                "section_id": section_id_counter,
                "grade": grade,
                "section_name": section
            })
            section_id_counter += 1
    df_grade_sections = pd.DataFrame(grade_sections)

    # Generate curriculum for each grade
    curriculum_data = []
    for grade in GRADES:
        prompt = f"""
        Create a standard weekly curriculum for Grade {grade}.
        The curriculum must include subjects, and the number of hours per week for each subject.
        The total weekly hours should be between 30 and 35.
        Use subjects from this list: {SUBJECTS_LIST}.
        Ensure the subjects are appropriate for Grade {grade}. For example, younger grades might not have Physics.
        Format the output as a JSON object where keys are subject names and values are weekly hours.
        Example for a grade: {{"Mathematics": 5, "English": 5, "Science": 4, "History": 3, "PE": 2}}
        """
        curriculum_json_str = generate_data_with_llm(prompt, temperature=0.5)
        
        # --- FIX STARTS HERE ---
        # Clean the LLM response to remove Markdown code blocks before parsing
        if curriculum_json_str:
            cleaned_json_str = curriculum_json_str.strip().replace('```json', '').replace('```', '').strip()
            try:
                grade_curriculum = json.loads(cleaned_json_str)
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON from LLM response for grade {grade}: {e}")
                print(f"Problematic string: {cleaned_json_str}")
                continue # Skip this grade if parsing fails
        else:
            continue # Skip this grade if LLM fails
        # --- FIX ENDS HERE ---

        # Apply this curriculum to all sections of the grade
        sections_for_grade = df_grade_sections[df_grade_sections['grade'] == grade]
        for _, row in sections_for_grade.iterrows():
            for subject, hours in grade_curriculum.items():
                 # Find the required room type
                required_room_type = "Normal Classroom" # Default
                for room_type, subjects_in_type in CLASSROOM_TYPES_MAPPING.items():
                    if subject in subjects_in_type:
                        required_room_type = room_type
                        break
                curriculum_data.append({
                    "section_id": row['section_id'],
                    "subject_name": subject,
                    "weekly_hours": hours,
                    "required_classroom_type": required_room_type
                })

    df_curriculum = pd.DataFrame(curriculum_data)
    return df_grade_sections, df_curriculum

def main():
    """Main function to generate all data and save to CSVs."""
    print("Generating Teacher Data...")
    df_teachers, df_teacher_specializations = generate_teachers()
    df_teachers.to_csv("teachers.csv", index=False)
    df_teacher_specializations.to_csv("teacher_specializations.csv", index=False)
    print("Teacher data saved to teachers.csv and teacher_specializations.csv")

    print("\nGenerating Classroom Data...")
    df_classrooms = generate_classrooms()
    df_classrooms.to_csv("classrooms.csv", index=False)
    print("Classroom data saved to classrooms.csv")

    print("\nGenerating Curriculum Data...")
    df_grade_sections, df_curriculum = generate_curriculum()
    df_grade_sections.to_csv("grade_sections.csv", index=False)
    df_curriculum.to_csv("curriculum.csv", index=False)
    print("Curriculum data saved to grade_sections.csv and curriculum.csv")

    # Static data
    df_subjects = pd.DataFrame(SUBJECTS_LIST, columns=["subject_name"])
    df_subjects.to_csv("subjects.csv", index=False)
    print("\nSubjects data saved to subjects.csv")

    df_classroom_types = pd.DataFrame(list(CLASSROOM_TYPES_MAPPING.keys()), columns=["type_name"])
    df_classroom_types.to_csv("classroom_types.csv", index=False)
    print("Classroom types data saved to classroom_types.csv")


if __name__ == "__main__":
    main()


def generate_teachers():
    """Generates a list of teachers and their specializations."""
    prompt = f"""
    Generate a list of {NUM_TEACHERS} unique and diverse first and last names for school teachers.
    Format the output as a simple JSON array of strings. For example: ["John Doe", "Jane Smith"].
    """
    names_json_str = generate_data_with_llm(prompt)
    teacher_names = json.loads(names_json_str)

    teachers = []
    specializations = []
    teacher_id_counter = 1

    for name in teacher_names[:NUM_TEACHERS]:
        teachers.append({
            "teacher_id": teacher_id_counter,
            "teacher_name": name,
            "max_weekly_hours": random.randint(18, 25) # Standard teaching load
        })

        # Assign 1 to 3 specializations
        num_specializations = random.randint(1, 3)
        teacher_subjects = random.sample(SUBJECTS_LIST, num_specializations)
        for subject in teacher_subjects:
            specializations.append({
                "teacher_id": teacher_id_counter,
                "subject_name": subject
            })
        teacher_id_counter += 1

    return pd.DataFrame(teachers), pd.DataFrame(specializations)

def generate_classrooms():
    """Generates classrooms of different types."""
    # Define distribution
    num_labs = 8
    num_pe = 4
    num_kitchens = 2
    num_computer_labs = 6
    num_normal = NUM_CLASSROOMS - (num_labs + num_pe + num_kitchens + num_computer_labs)

    room_counts = {
        "Science Lab": num_labs,
        "PE Area": num_pe,
        "Nutrition Kitchen": num_kitchens,
        "Computer Lab": num_computer_labs,
        "Normal Classroom": num_normal
    }

    classrooms = []
    classroom_id_counter = 1
    for room_type, count in room_counts.items():
        for i in range(count):
            name = f"{room_type.replace(' ', '')}-{i+1}"
            capacity = 30 # Assume standard capacity
            if room_type == "PE Area":
                capacity = 60
            classrooms.append({
                "classroom_id": classroom_id_counter,
                "classroom_name": name,
                "type_name": room_type,
                "capacity": capacity
            })
            classroom_id_counter += 1
    return pd.DataFrame(classrooms)

def generate_curriculum():
    """Generates curriculum requirements for each grade-section."""
    # Create grade-sections first
    grade_sections = []
    section_id_counter = 1
    for grade in GRADES:
        for section in SECTIONS:
            grade_sections.append({
                "section_id": section_id_counter,
                "grade": grade,
                "section_name": section
            })
            section_id_counter += 1
    df_grade_sections = pd.DataFrame(grade_sections)

    # Generate curriculum for each grade
    curriculum_data = []
    for grade in GRADES:
        prompt = f"""
        Create a standard weekly curriculum for Grade {grade}.
        The curriculum must include subjects, and the number of hours per week for each subject.
        The total weekly hours should be between 30 and 35.
        Use subjects from this list: {SUBJECTS_LIST}.
        Ensure the subjects are appropriate for Grade {grade}. For example, younger grades might not have Physics.
        Format the output as a JSON object where keys are subject names and values are weekly hours.
        Example for a grade: {{"Mathematics": 5, "English": 5, "Science": 4, "History": 3, "PE": 2}}
        """
        curriculum_json_str = generate_data_with_llm(prompt, temperature=0.5)
        # Clean up potential markdown formatting from LLM response
        curriculum_json_str = curriculum_json_str.strip().replace('```json', '').replace('```', '').strip()
        grade_curriculum = json.loads(curriculum_json_str)

        # Apply this curriculum to all sections of the grade
        sections_for_grade = df_grade_sections[df_grade_sections['grade'] == grade]
        for _, row in sections_for_grade.iterrows():
            for subject, hours in grade_curriculum.items():
                 # Find the required room type
                required_room_type = "Normal Classroom" # Default
                for room_type, subjects_in_type in CLASSROOM_TYPES_MAPPING.items():
                    if subject in subjects_in_type:
                        required_room_type = room_type
                        break
                curriculum_data.append({
                    "section_id": row['section_id'],
                    "subject_name": subject,
                    "weekly_hours": hours,
                    "required_classroom_type": required_room_type
                })

    df_curriculum = pd.DataFrame(curriculum_data)
    return df_grade_sections, df_curriculum
def main():
    """Main function to generate all data and save to CSVs."""
    
    # 1. Generate Teacher Data
    print("Generating Teacher Data...")
    df_teachers, df_teacher_specializations = generate_teachers()
    if not df_teachers.empty:
        df_teachers.to_csv("teachers.csv", index=False)
        df_teacher_specializations.to_csv("teacher_specializations.csv", index=False)
        print("Teacher data saved to teachers.csv and teacher_specializations.csv")
    else:
        print("Skipping teacher data saving due to generation error.")

    # 2. Generate Classroom Data
    print("\nGenerating Classroom Data...")
    df_classrooms = generate_classrooms()
    df_classrooms.to_csv("classrooms.csv", index=False)
    print("Classroom data saved to classrooms.csv")

    # 3. Generate Curriculum Data
    print("\nGenerating Curriculum Data...")
    df_grade_sections, df_curriculum = generate_curriculum()
    if not df_grade_sections.empty:
        df_grade_sections.to_csv("grade_sections.csv", index=False)
        df_curriculum.to_csv("curriculum.csv", index=False)
        print("Curriculum data saved to grade_sections.csv and curriculum.csv")
    else:
        print("Skipping curriculum data saving due to generation error.")


    # 4. Generate Static Data
    print("\nGenerating Static Data...")
    
    # Subjects
    df_subjects = pd.DataFrame({"subject_name": SUBJECTS_LIST})
    df_subjects.to_csv("subjects.csv", index=False)
    print("Subjects data saved to subjects.csv")

    # Classroom Types
    df_classroom_types = pd.DataFrame({"type_name": list(CLASSROOM_TYPES_MAPPING.keys())})
    df_classroom_types.to_csv("classroom_types.csv", index=False)
    print("Classroom types data saved to classroom_types.csv")
    
    print("\nAll data generation complete.")


if __name__ == "__main__":
    main()