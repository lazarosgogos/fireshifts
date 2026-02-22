from ortools.sat.python import cp_model
import pandas as pd
from io import StringIO

class Fireshifts():
    def __init__(self, data):
        self.df = pd.read_csv(StringIO(data), sep=r"\s+", engine="python")
        self.cols = self.df.columns
        date_cols = self.df[self.cols[1:]]

    def create_model(self):
        
        # step 1: create a model
        self.model = cp_model.CpModel()

        # step 2: define data
        self.firefighters = self.df[self.cols[0]].to_list()
        self.dates = self.df.columns[1:].to_list()
        self.telephones = ['A', 'B', 'C']
        self.patrol_names = ['A', 'B']
        num_firefighters = len(self.df) # number of firefighters excluding first row (dates)
        num_dates = len(self.df.columns[1:]) # col 0 contains names
        num_telephones = len(self.telephones)
        num_patrols = len(self.patrol_names)

        # create shift variables
        # shifts[(f,d,t)] = firefighter 'f' works on day 'd' the telephone 't'
        self.shifts = {}
        for f in self.firefighters:
            for d in self.dates:
                for t in self.telephones:
                    self.shifts[(f,d,t)] = self.model.new_bool_var(f"shift_f{f}_d{d}_t{t}")
        
        # create patrol variables
        # patrols[(f,d,p)] = firefighter 'f' works on day 'd' on patrol 'p'
        self.patrols = {}
        for f in self.firefighters:
            for d in self.dates:
                for p in self.patrol_names:
                    self.patrols[(f,d,p)] = self.model.new_bool_var(f"patrol_f{f}_d{d}_p{p}")
        
        
        # each telephone is assigned to exactly one firefighter
        for d in self.dates:
            for t in self.telephones:
                self.model.add_exactly_one(self.shifts[(f,d,t)] for f in self.firefighters)

        # each firefighter get at most one telephone
        for d in self.dates:
            for f in self.firefighters:
                self.model.add_at_most_one(self.shifts[(f,d,t)] for t in self.telephones)


        # make sure firefighters who don't work do not have any tel that day
        for i, f in enumerate(self.firefighters):
            for j, d in enumerate(self.dates):
                if self.df.iloc[i, j+1] != '.':
                    for t in self.telephones:
                        self.model.add(self.shifts[(f,d,t)] == 0)

        # -- PATROLS
        # each patrol needs exactly 2 firefighters per day
        for d in self.dates:
            for p in self.patrol_names:
                self.model.add(sum(self.patrols[(f,d,p)] for f in self.firefighters) == 2)

        # each firefighter can have at most one patrol per day
        for d in self.dates:
            for f in self.firefighters:
                self.model.add_at_most_one(self.patrols[(f,d,p)] for p in self.patrol_names)

        # firefighters can only be on patrol if they're working that day
        for i, f in enumerate(self.firefighters):
            for j, d in enumerate(self.dates):
                if self.df.iloc[i, j+1] != '.':
                    for p in self.patrol_names:
                        self.model.add(self.patrols[(f,d,p)] == 0)

        # HARD CONSTRAINT: patrol B cannot have telephone B
        for d in self.dates:
            for f in self.firefighters:
                self.model.add_implication(self.patrols[(f,d,'B')], self.shifts[(f,d,'B')].Not())

        # try to distribute the telephones evenly to each firefighter
        # min_telephones_per_firefighter. if this is not feasible (quite possible)
        # some firefighters will get at most one more telephone

        min_shifts_per_firefighter = (num_telephones*num_dates) // num_firefighters
        if num_telephones * num_dates % num_firefighters == 0:
            max_shifts_per_firefighter = min_shifts_per_firefighter
        else:
            max_shifts_per_firefighter = min_shifts_per_firefighter + 1

        for f in self.firefighters:
            shifts_worked = []
            for d in self.dates:
                for t in self.telephones:
                    shifts_worked.append(self.shifts[(f,d,t)])
            self.model.add(min_shifts_per_firefighter <= sum(shifts_worked))
            self.model.add(sum(shifts_worked) <= max_shifts_per_firefighter)

        # try to distribute patrols evenly to each firefighter
        min_patrols_per_firefighter = (num_patrols * 2 * num_dates) // num_firefighters
        if (num_patrols * 2 * num_dates) % num_firefighters == 0:
            max_patrols_per_firefighter = min_patrols_per_firefighter
        else:
            max_patrols_per_firefighter = min_patrols_per_firefighter + 1

        for f in self.firefighters:
            patrols_worked = []
            for d in self.dates:
                for p in self.patrol_names:
                    patrols_worked.append(self.patrols[(f,d,p)])
            self.model.add(min_patrols_per_firefighter <= sum(patrols_worked))
            self.model.add(sum(patrols_worked) <= max_patrols_per_firefighter)

        # count how many times a firefighter works A,B, or C
        counts = {}
        for f in self.firefighters:
            for t in self.telephones:
                counts[(f,t)] = self.model.new_int_var(0, num_dates, f"count_f{f}_t{t}")
                self.model.add(counts[(f,t)] == sum(self.shifts[(f,d,t)] for d in self.dates))
        
        # say each pair differs by at most 1
        violations = []
        allowed_gap = 1
        for f in self.firefighters:
            pairs = [('A', 'B'), ('A', 'C'), ('B', 'C')]
            for p,q in pairs:
                abs_diff = self.model.new_int_var(0, num_dates, f"abs_{f}_{p}_{q}")
                self.model.add_abs_equality(abs_diff, counts[(f,p)] - counts[(f,q)])

                violation = self.model.new_int_var(0, num_dates, f"viol_{f}_{p}_{q}")

                self.model.add(violation >= abs_diff - allowed_gap)

                self.model.add(violation <= num_dates)
                violations.append(violation)

        # SOFT CONSTRAINT: discourage patrol B + telephone C
        patrol_b_tel_c_violations = []
        for d in self.dates:
            for f in self.firefighters:
                violation = self.model.new_bool_var(f"patrol_b_tel_c_{f}_{d}")
                self.model.add_bool_and([self.patrols[(f,d,'B')], self.shifts[(f,d,'C')]]).only_enforce_if(violation)
                self.model.add_bool_or([self.patrols[(f,d,'B')].Not(), self.shifts[(f,d,'C')].Not()]).only_enforce_if(violation.Not())
                patrol_b_tel_c_violations.append(violation)

        # SOFT CONSTRAINT: discourage patrol A + telephone B (prefer non-patrol for tel B)
        patrol_a_tel_b_violations = []
        for d in self.dates:
            for f in self.firefighters:
                violation = self.model.new_bool_var(f"patrol_a_tel_b_{f}_{d}")
                self.model.add_bool_and([self.patrols[(f,d,'A')], self.shifts[(f,d,'B')]]).only_enforce_if(violation)
                self.model.add_bool_or([self.patrols[(f,d,'A')].Not(), self.shifts[(f,d,'B')].Not()]).only_enforce_if(violation.Not())
                patrol_a_tel_b_violations.append(violation)

        # total call shifts per firefighter  
        total_counts = {}
        for f in self.firefighters:
            total_counts[f] = self.model.new_int_var(0, num_telephones * num_dates, f"total_{f}")
            self.model.add(total_counts[f] == sum(self.shifts[(f,d,t)] for d in self.dates for t in self.telephones))

        max_count = self.model.new_int_var(0, num_telephones * num_dates, "max_count")
        min_count = self.model.new_int_var(0, num_telephones * num_dates, "min_count")

        for f in self.firefighters:
            self.model.add(total_counts[f] <= max_count)
            self.model.add(total_counts[f] >= min_count)

        # Objective: minimize telephone imbalance + soft constraint violations
        self.model.minimize(
            10 * (max_count - min_count) + 
            5 * sum(patrol_b_tel_c_violations) + 
            3 * sum(patrol_a_tel_b_violations)
        )

    def solve(self):
        # create a solver and solve
        solver = cp_model.CpSolver()

        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule_data = []
            for d in self.dates:
                row = {}
                for t in self.telephones:
                    for f in self.firefighters:
                        if solver.Value(self.shifts[(f,d,t)]):
                            row[t] = f
                for p in self.patrol_names:
                    patrol_members = []
                    for f in self.firefighters:
                        if solver.Value(self.patrols[(f,d,p)]):
                            patrol_members.append(f)
                    row[f'Patrol_{p}'] = ', '.join(patrol_members)
                schedule_data.append(row)
            self.schedule_df = pd.DataFrame(schedule_data, index=self.dates)
            self.schedule_df.index.name = "Date"

            summary = []
            for f in self.firefighters:
                row = {"Firefighter": f}
                for t in self.telephones:
                    row[f"Tel_{t}"] = sum(solver.Value(self.shifts[(f,d,t)]) for d in self.dates)
                for p in self.patrol_names:
                    row[f"Patrol_{p}"] = sum(solver.Value(self.patrols[(f,d,p)]) for d in self.dates)
                row["Total_Tel"] = sum(solver.Value(self.shifts[(f,d,t)]) for d in self.dates for t in self.telephones)
                row["Total_Patrol"] = sum(solver.Value(self.patrols[(f,d,p)]) for d in self.dates for p in self.patrol_names)
                summary.append(row)

            self.summary_df = pd.DataFrame(summary).set_index("Firefighter")
        else:
            self.schedule_df = pd.DataFrame()
            self.summary_df = pd.DataFrame()

    def get_results(self):
        return self.schedule_df, self.summary_df