import random
import numpy as np
from deap import base, creator, tools, algorithms
from ai.utils import DAYS_OF_WEEK, TIME_SLOTS_PER_DAY
import collections

# --- GA Configuration ---
POPULATION_SIZE = 200
N_GENERATIONS = 150 # Increased generations for better convergence
CXPB = 0.9
MUTPB = 0.5

# Multi-objective: 1st, heavily penalize hard conflicts. 2nd, minimize soft conflicts (gaps).
creator.create("FitnessMulti", base.Fitness, weights=(-1000.0, -1.0))
creator.create("Individual", list, fitness=creator.FitnessMulti)

class ScheduleOptimizer:
    def __init__(self, teachers_df, classrooms_df, curriculum_df):
        print("--- Initializing Hybrid Genetic Algorithm Optimizer ---")
        self.teachers = teachers_df
        self.classrooms = classrooms_df
        self.curriculum = curriculum_df
        
        self.class_slots = []
        for _, row in curriculum_df.iterrows():
            for i in range(row['weekly_hours']):
                self.class_slots.append((row['section_id'], row['subject_id'], i))

        self.valid_assignments_per_slot = self._precompute_valid_assignments()
        self.toolbox = base.Toolbox()
        self._setup_toolbox()

    def _precompute_valid_assignments(self):
        print("Pre-computing valid resources for each class slot...")
        valid_assignments = []
        for section_id, subject_id, _ in self.class_slots:
            qualified_teachers = self.teachers[self.teachers['subject_id'] == subject_id]['teacher_id'].tolist()
            required_type_id = self.curriculum[(self.curriculum['section_id'] == section_id) & (self.curriculum['subject_id'] == subject_id)]['required_classroom_type_id'].iloc[0]
            suitable_classrooms = self.classrooms[self.classrooms['type_id'] == required_type_id]['classroom_id'].tolist()
            valid_assignments.append({'teachers': qualified_teachers, 'classrooms': suitable_classrooms})
        return valid_assignments

    def _create_gene(self, slot_idx):
        valid = self.valid_assignments_per_slot[slot_idx]
        return (random.choice(valid['teachers']), random.choice(valid['classrooms']), 
                random.choice(list(DAYS_OF_WEEK)), random.randint(1, TIME_SLOTS_PER_DAY))
    
    def _greedy_initializer(self):
        ind = creator.Individual([None] * len(self.class_slots))
        teacher_schedule, room_schedule, section_schedule = {}, {}, {}
        
        for i in range(len(self.class_slots)):
            section_id, _, _ = self.class_slots[i]
            attempts = 0
            while attempts < 50:
                gene = self._create_gene(i)
                teacher, room, day, slot = gene
                if not teacher_schedule.get((teacher, day, slot)) and \
                   not room_schedule.get((room, day, slot)) and \
                   not section_schedule.get((section_id, day, slot)):
                    ind[i] = gene
                    teacher_schedule[(teacher, day, slot)] = True
                    room_schedule[(room, day, slot)] = True
                    section_schedule[(section_id, day, slot)] = True
                    break
                attempts += 1
            if ind[i] is None:
                ind[i] = self._create_gene(i)
        return ind

    def _repair_schedule(self, individual):
        max_repair_cycles = 5
        for _ in range(max_repair_cycles):
            conflicts_found = False
            teacher_slots, room_slots, section_slots = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
            
            for i, gene in enumerate(individual):
                teacher, room, day, slot = gene
                section = self.class_slots[i][0]
                teacher_slots[(teacher, day, slot)].append(i)
                room_slots[(room, day, slot)].append(i)
                section_slots[(section, day, slot)].append(i)
            
            all_conflicts = set()
            for slot_group in [teacher_slots, room_slots, section_slots]:
                for indices in slot_group.values():
                    if len(indices) > 1:
                        conflicts_found = True
                        for i in indices[1:]: all_conflicts.add(i)

            if not conflicts_found:
                break # No more hard conflicts, repair is done

            # Attempt to repair only the identified conflicting genes
            for i in list(all_conflicts):
                for _ in range(20):
                    new_gene = self._create_gene(i)
                    new_teacher, new_room, new_day, new_slot = new_gene
                    
                    # Check against the *current* state of the schedule
                    if len(teacher_slots.get((new_teacher, new_day, new_slot), [])) == 0 and \
                       len(room_slots.get((new_room, new_day, new_slot), [])) == 0 and \
                       len(section_slots.get((self.class_slots[i][0], new_day, new_slot), [])) == 0:
                        individual[i] = new_gene
                        break
        return individual

    def _setup_toolbox(self):
        self.toolbox.register("individual", self._greedy_initializer)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.evaluate_schedule)
        self.toolbox.register("select", tools.selNSGA2)
        self.toolbox.register("mate", tools.cxTwoPoint)
        
        # --- THE DEFINITIVE FIX: A CUSTOM MUTATION OPERATOR ---
        def custom_mutate(individual, indpb):
            """Mutates a gene by re-generating a valid assignment for its position."""
            for i in range(len(individual)):
                if random.random() < indpb:
                    individual[i] = self._create_gene(i) # This respects the constraints of the class slot
            return individual,
        
        self.toolbox.register("mutate", custom_mutate, indpb=0.05)
        # --- END FIX ---

    def evaluate_schedule(self, individual):
        hard_conflicts, soft_conflicts = 0, 0
        teacher_slots, room_slots, section_slots = collections.defaultdict(int), collections.defaultdict(int), collections.defaultdict(int)
        teacher_daily_slots = collections.defaultdict(list)

        for i, gene in enumerate(individual):
            teacher, room, day, slot = gene
            section = self.class_slots[i][0]
            teacher_slots[(teacher, day, slot)] += 1
            room_slots[(room, day, slot)] += 1
            section_slots[(section, day, slot)] += 1
            teacher_daily_slots[(teacher, day)].append(slot)
        
        hard_conflicts += sum(c - 1 for c in teacher_slots.values() if c > 1)
        hard_conflicts += sum(c - 1 for c in room_slots.values() if c > 1)
        hard_conflicts += sum(c - 1 for c in section_slots.values() if c > 1)
        
        for slots in teacher_daily_slots.values():
            if len(slots) > 1:
                soft_conflicts += (max(slots) - min(slots) + 1) - len(slots)
                
        return hard_conflicts, soft_conflicts

    def run(self):
        pop = self.toolbox.population(n=POPULATION_SIZE)
        hof = tools.ParetoFront()
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean, axis=0)
        stats.register("min", np.min, axis=0)
        
        print("GA: Starting evolution...")
        
        # Manually implement the evolutionary loop for more control
        # 1. Evaluate the initial population
        fitnesses = self.toolbox.map(self.toolbox.evaluate, pop)
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit
        
        hof.update(pop)
        
        # 2. Begin the generational process
        for gen in range(1, N_GENERATIONS + 1):
            # Select the next generation individuals
            offspring = self.toolbox.select(pop, len(pop))
            offspring = [self.toolbox.clone(ind) for ind in offspring]

            # Apply crossover and mutation
            for i in range(1, len(offspring), 2):
                if random.random() < CXPB:
                    offspring[i-1], offspring[i] = self.toolbox.mate(offspring[i-1], offspring[i])
                    del offspring[i-1].fitness.values, offspring[i].fitness.values
            
            for i in range(len(offspring)):
                if random.random() < MUTPB:
                    offspring[i], = self.toolbox.mutate(offspring[i])
                    del offspring[i].fitness.values
            
            # Repair each new offspring that was modified
            for i in range(len(offspring)):
                if not offspring[i].fitness.valid:
                    offspring[i] = self._repair_schedule(offspring[i])

            # Evaluate the individuals with an invalid fitness
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            
            # Update the hall of fame with the new population
            hof.update(offspring)
            # Replace the old population with the new offspring
            pop[:] = offspring
            
            # Log the stats
            record = stats.compile(pop)
            print(f"Gen {gen}: Min Fitness (Hard, Soft)={record['min']}, Avg Fitness={record['avg']}")

        best_ind = None
        # Find the best solution with 0 hard conflicts from the Hall of Fame
        for ind in hof:
            if ind.fitness.values[0] == 0:
                best_ind = ind
                break
        
        if not best_ind:
            print("GA Warning: Could not find a perfect solution. Returning best found from population.")
            best_ind = tools.selBest(pop, 1)[0]
            
        print(f"\nGA Finished. Best solution fitness: {best_ind.fitness.values}")
        solution_dict = {self.class_slots[i]: best_ind[i] for i in range(len(self.class_slots))}
        return solution_dict

def solve_with_ga(teachers_df, classrooms_df, curriculum_df):
    optimizer = ScheduleOptimizer(teachers_df, classrooms_df, curriculum_df)
    return optimizer.run()