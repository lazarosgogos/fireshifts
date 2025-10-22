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
        model = cp_model.CpModel()

        # step 2: define data
        firefighters = self.df[self.cols[0]].to_list()
        dates = self.df.columns[1:].to_list()
        telephones = ['A', 'B', 'C']
        num_firefighters = len(self.df) # number of firefighters excluding first row (dates)
        num_dates = len(self.df.columns[1:]) # col 0 contains names
        num_telephones = len(telephones)

        # create shift variables
        # shifts[(f,d,t)] = firefighter 'f' works on day 'd' the telephone 't'
        shifts = {}
        for f in firefighters:
            for d in dates:
                for t in telephones:
                    shifts[(f,d,t)] = model.new_bool_var(f"shift_f{f}_d{d}_t{t}")

        # each telephone is assigned to exactly one firefighter
        for d in dates:
            for t in telephones:
                model.add_exactly_one(shifts[(f,d,t)] for f in firefighters)

        # each firefighter get at most one telephone
        for d in dates:
            for f in firefighters:
                model.add_at_most_one(shifts[(f,d,t)] for t in telephones)

        # make sure firefighters who don't work do not have any tel that day
        for i, f in enumerate(firefighters):
            for j, d in enumerate(dates):
                if self.df.iloc[i, j+1] != '.':
                    for t in telephones:
                        model.add(shifts[(f,d,t)] == 0)

        # try to distribute the telephones evenly to each firefighter
        # min_telephones_per_firefighter. if this is not feasible (quite possible)
        # some firefighters will get at most one more telephone

        min_shifts_per_firefighter = (num_telephones*num_dates) // num_firefighters
        if num_telephones * num_dates % num_firefighters == 0:
            max_shifts_per_firefighter = min_shifts_per_firefighter
        else:
            max_shifts_per_firefighter = min_shifts_per_firefighter + 1

        for f in firefighters:
            shifts_worked = []
            for d in dates:
                for t in telephones:
                    shifts_worked.append(shifts[(f,d,t)])
            model.add(min_shifts_per_firefighter <= sum(shifts_worked))
            model.add(sum(shifts_worked) <= max_shifts_per_firefighter)

        # count how many times a firefighter works A,B, or C
        counts = {}
        for f in firefighters:
            for t in telephones:
                counts[(f,t)] = model.new_int_var(0, num_dates, f"count_f{f}_t{t}")
                model.add(counts[(f,t)] == sum(shifts[(f,d,t)] for d in dates))

        # say each pair differs by at most 1
        for f in firefighters:
            model.add(counts[(f, 'A')] - counts[(f, 'B')] <= 1)
            model.add(counts[(f, 'B')] - counts[(f, 'A')] <= 1)
            model.add(counts[(f, 'A')] - counts[(f, 'C')] <= 1)
            model.add(counts[(f, 'C')] - counts[(f, 'A')] <= 1)
            model.add(counts[(f, 'B')] - counts[(f, 'C')] <= 1)
            model.add(counts[(f, 'C')] - counts[(f, 'B')] <= 1)

        # total call shifts per firefighter  
        total_counts = {}
        for f in firefighters:
            total_counts[f] = model.new_int_var(0, num_telephones * num_dates, f"total_{f}")
            model.add(total_counts[f] == sum(shifts[(f,d,t)] for d in dates for t in telephones))

        max_count = model.new_int_var(0, num_telephones * num_dates, "max_count")
        min_count = model.new_int_var(0, num_telephones * num_dates, "min_count")

        for f in firefighters:
            model.add(total_counts[f] <= max_count)
            model.add(total_counts[f] >= min_count)

        model.minimize(max_count - min_count)

    # create a solver and solve
    solver = cp_model.CpSolver()

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for f in firefighters:
            for d in dates:
                for t in telephones:
                    if solver.Value(shifts[(f,d,t)]):
                    print(f"{f} at date {d} works {t}")

    schedule_data = []
    for d in dates:
        row = {}
        for t in telephones:
        for f in firefighters:
            if solver.Value(shifts[(f,d,t)]):
            row[t] = f
        schedule_data.append(row)
    schedule_df = pd.DataFrame(schedule_data, index=dates)
    schedule_df.index.name = "Date"

    summary = []
    for f in firefighters:
        row = {"Firefighter": f}
        for t in telephones:
        row[f"sum of tel {t}"] = sum(solver.Value(shifts[(f,d,t)]) for d in dates)
        summary.append(row)

    summary_df = pd.DataFrame(summary).set_index("Firefighter")

    print(schedule_df)
    print(summary_df)