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
        num_firefighters = len(self.df) # number of firefighters excluding first row (dates)
        num_dates = len(self.df.columns[1:]) # col 0 contains names
        num_telephones = len(self.telephones)

        # create shift variables
        # shifts[(f,d,t)] = firefighter 'f' works on day 'd' the telephone 't'
        self.shifts = {}
        for f in self.firefighters:
            for d in self.dates:
                for t in self.telephones:
                    self.shifts[(f,d,t)] = self.model.new_bool_var(f"shift_f{f}_d{d}_t{t}")

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

        # count how many times a firefighter works A,B, or C
        counts = {}
        for f in self.firefighters:
            for t in self.telephones:
                counts[(f,t)] = self.model.new_int_var(0, num_dates, f"count_f{f}_t{t}")
                self.model.add(counts[(f,t)] == sum(self.shifts[(f,d,t)] for d in self.dates))

        # say each pair differs by at most 1
        for f in self.firefighters:
            self.model.add(counts[(f, 'A')] - counts[(f, 'B')] <= 1)
            self.model.add(counts[(f, 'B')] - counts[(f, 'A')] <= 1)
            self.model.add(counts[(f, 'A')] - counts[(f, 'C')] <= 1)
            self.model.add(counts[(f, 'C')] - counts[(f, 'A')] <= 1)
            self.model.add(counts[(f, 'B')] - counts[(f, 'C')] <= 1)
            self.model.add(counts[(f, 'C')] - counts[(f, 'B')] <= 1)

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

        self.model.minimize(max_count - min_count)

    def solve(self):
        # create a solver and solve
        solver = cp_model.CpSolver()

        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # for f in self.firefighters:
            #     for d in self.dates:
            #         for t in self.telephones:
            #             if solver.Value(self.shifts[(f,d,t)]):
            #                 print(f"{f} at date {d} works {t}")

            schedule_data = []
            for d in self.dates:
                row = {}
                for t in self.telephones:
                    for f in self.firefighters:
                        if solver.Value(self.shifts[(f,d,t)]):
                            row[t] = f
                schedule_data.append(row)
            self.schedule_df = pd.DataFrame(schedule_data, index=self.dates)
            self.schedule_df.index.name = "Date"

            summary = []
            for f in self.firefighters:
                row = {"Firefighter": f}
                for t in self.telephones:
                    row[f"sum of tel {t}"] = sum(solver.Value(self.shifts[(f,d,t)]) for d in self.dates)
                summary.append(row)

            self.summary_df = pd.DataFrame(summary).set_index("Firefighter")

    def get_results(self):
        # print(self.schedule_df)
        # print(self.summary_df)
        return self.schedule_df, self.summary_df