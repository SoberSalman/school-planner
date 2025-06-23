# 🎓 AI School Resource Planner

This project is a comprehensive, AI-driven system for optimizing school resource planning. It generates a conflict-free and optimized weekly timetable for an entire school, demonstrating a full-stack approach that integrates Data Engineering, AI/ML Engineering, Data Analysis, and UI/UX Development.

The system is built around a powerful **Hybrid Genetic Algorithm** that intelligently navigates the vast and complex search space of scheduling possibilities to produce high-quality, actionable timetables.

## 🚀 Live Demo & How to Run

The application is served as a web interface built with FastAPI.

**1. Installation:**
First, ensure all dependencies are installed. It's recommended to use a virtual environment.
```bash
pip install -r requirements.txt
```

**2. Data Setup (First-Time Use Only):**
If the school_planner.db file does not exist, you must generate the synthetic data and create the database.

```bash
# Generate realistic data using an LLM (requires LM Studio or similar to be running)
python data/generate_data.py

# Create and populate the SQLite database from the generated CSVs
python data/setup_database.py
```

**3. Launch the Application** 

Launch the web server from the project root.

```bash
python run.py
```

# 🏛️ Project Architecture

The project is structured into distinct, modular components, each handling a specific role:

- **data/**: Contains scripts for generating synthetic data (`generate_data.py`) and setting up the initial database (`setup_database.py`).
- **ai/**: The core intelligence of the application. It contains the Hybrid Genetic Algorithm (`genetic_solver.py`) and shared utilities (`utils.py`).
- **static/**: Holds the CSS stylesheet (`style.css`) for the web interface.
- **templates/**: Contains the Jinja2 HTML template (`index.html`) that structures the frontend.
- **main.py**: The FastAPI backend server. It defines API endpoints, orchestrates the AI solver, and serves the web UI.
- **run.py**: A simple script to launch the Uvicorn web server.
- **school_planner.db**: The SQLite database that acts as the single source of truth for all school data.

---

# 🧬 The AI Core: A Hybrid Genetic Algorithm

A simple Genetic Algorithm (GA) is insufficient for a problem this constrained. A purely random search will almost never find a valid solution. Therefore, this project implements a **Hybrid Genetic Algorithm**, combining GA with intelligent heuristics.

## Key Concepts

- **Gene**: Basic unit of a schedule. Tuple: `(teacher_id, classroom_id, day_of_week, time_slot)`.
- **Chromosome (Individual)**: List of genes; represents a full weekly schedule.
- **Population**: A set of chromosomes; evolved over generations.

---

## How the Hybrid Algorithm Works

### 1. Guided Initialization (Smart Start)
Uses a greedy initializer to reduce initial conflicts by intelligently placing classes.

### 2. Multi-Objective Fitness Function
- **Hard Conflicts**: Double-booked teacher/classroom/section (-1000 weight).
- **Soft Conflicts**: Idle periods in teacher schedules (-1 weight).

### 3. Repair Mechanism (Secret Weapon)
- Detects conflicts post-mutation/crossover.
- Applies local search to fix each hard conflict by moving classes.

### 4. Advanced Genetic Operators
- **Intelligent Crossover**: Swaps schedules of selected teachers only.
- **Elitism**: Top 5% schedules passed unchanged to next generation.

---

# 🛠️ Technology Stack

- **Backend**: FastAPI, Uvicorn  
- **Frontend**: Jinja2, HTML5, CSS3, JavaScript  
- **AI/ML**: DEAP (Distributed Evolutionary Algorithms in Python)  
- **Database**: SQLite, Pandas  
- **Visualization**: Plotly

---

# 🔑 Key Features and Requirements Met

- ✅ **Optimized Scheduling**: Auto-assigns teachers/classrooms, resolving all hard constraints.
- 🚨 **Conflict Handling & Alerts**: Fitness function + UI conflict list.
- 📊 **Data Analysis**: Dashboard with utilization metrics.
- 📈 **Scalable Design**: Just add data—no code change.
- 🖥️ **Flexible UI**: Clean, responsive interface with filtering and placeholder for drag-and-drop scheduling.

