import itertools
import os
from typing import NamedTuple

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import ObjLinearExprT

from model import Data, ResultRecord, HandledException

UNSOLVABLE_PENALTY = 10000


class Assignment(NamedTuple):
    assignment: tuple[int, ...]
    penalty: int


class SolverResult(NamedTuple):
    # if False, this assignment is not schedulable, some students can not follow their choices
    schedulable: bool

    # an optimal solution has been found within the constraints of this pass
    optimal: bool

    # if True, the solution is feasible, but may not be not optimal
    feasable: bool

    result: list[ResultRecord]

    # if not None, another pass can be attempted relaxing constraints
    next_pass: int | None


class Solver:
    def __init__(self, data: Data, minimize_changes: bool, debug: bool = False):
        self.data = data
        self.minimize_changes = minimize_changes
        self.debug = debug
        self.periods = data.config.periods
        self.courses = data.courses
        self.students = data.students

    def solve(self):
        solver_pass = 0
        while True:
            # start_time = time.time()
            # while time.time() - start_time < 5:
            #     pass

            result = self._solve(solver_pass)
            if result.next_pass is None:
                if result.optimal or result.feasable:
                    self.data.result = result.result
                else:
                    raise HandledException("No solution found")
                return result
            solver_pass = result.next_pass

    def _solve(self, solver_pass: int) -> SolverResult:
        print(f"Solver pass {solver_pass}")
        # Generate all valid assignments per student
        valid_assignments: list[list[Assignment]] = self._create_valid_assignments(solver_pass)
        # self._print_valid_assignments(valid_assignments)
        # sys.exit(1)

        model = cp_model.CpModel()

        ### Variables ###

        assignment = {}
        for student in range(len(self.students)):
            for index, possible_assignment in enumerate(valid_assignments[student]):
                assignment[(student, index)] = model.NewBoolVar(
                    f"student{student}_assignment{index}")

        print(f"Number of assignment variables: {len(assignment)}")

        ### Constraints ###

        # Each student is assigned to exactly one valid assignment
        for student in range(len(self.students)):
            model.AddExactlyOne(
                [assignment[(student, assignment_index)] for assignment_index in range(len(valid_assignments[student]))]
            )

        # Each course is assigned to at most its size in each period
        for course in range(len(self.courses)):
            for period in range(self.periods):
                # find all assignment variables that assign this course in this period
                in_assignemnts = []
                for student in range(len(self.students)):
                    for index, possible_assignment in enumerate(valid_assignments[student]):
                        if possible_assignment.assignment[period] == course:
                            assignment_var = assignment[(student, index)]
                            in_assignemnts.append(assignment_var)
                model.Add(sum(in_assignemnts) <= self.courses[course].size)

        ### Objective ###

        penalty_expressions: list[ObjLinearExprT] = []
        penalty_weights: list[int] = []
        for student in range(len(self.students)):
            for index in range(len(valid_assignments[student])):
                penalty_expressions.append(assignment[(student, index)])
                penalty_weights.append(valid_assignments[student][index].penalty)

        if solver_pass < 2:
            # Since this can blow up the number of combinations, we only do this in the first passes
            # We could base this decision on the number of parameters or time it took in the previous pass
            (c_expr, c_weights) = self._calculate_combination_penalties(model, valid_assignments, assignment)
            penalty_expressions += c_expr
            penalty_weights += c_weights

        print(f"Number of penalty expressions: {len(penalty_expressions)}")
        model.Minimize(cp_model.LinearExpr.weighted_sum(penalty_expressions, penalty_weights))

        ### Hints or Assumptions ###

        # if self.minimize_changes and self.data.previous_result:
        #     # Unfortunately, hints do not seem to have effect while assumptions seem to result in suboptimal solutions
        #     self._add_hints(assignment, model, valid_assignments)

        ### Solve ###

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0
        log_file = None
        if self.debug:
            path = os.path.join("logs", f"search_progress_{solver_pass}.txt")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            log_file = open(f"search_progress_{solver_pass}.txt", "w")
            solver.log_callback = lambda x: log_file.write(x + "\n")
            solver.parameters.log_search_progress = True
            solver.parameters.log_to_stdout = False

        status = solver.Solve(model)
        solved = False
        result = []
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            penalty = solver.ObjectiveValue()
            result = self._get_result(solver, valid_assignments, assignment)
            result_type = "optimal" if status == cp_model.OPTIMAL else "feasible"
            print(f"{result_type} solution found. Penalty: {penalty}")
            solved = True
        else:
            print(f"No solution found, solver status is {status}")

        print(f"Time to solve: {solver.WallTime():.2f}s")
        if log_file:
            log_file.close()
        return SolverResult(
            schedulable=solved and solver_pass == 0,
            optimal=status == cp_model.OPTIMAL,
            feasable=status == cp_model.FEASIBLE,
            result=result,
            next_pass=solver_pass + 1 if (not solved and solver_pass < 4) else None
        )

    def _add_hints(self, assignment, model, valid_assignments):
        reference_result = self.data.previous_result
        for student_nr, student in enumerate(self.students):
            # find matching record in reference result
            reference_record = next((record for record in reference_result if record.student == student.name), None)
            if reference_record:
                # convert reference result to course numbers
                reference_courses = [self._course_number(course) for course in reference_record.courses]
                # find matching assignment
                matching_index = None
                for index, possible_assignment in enumerate(valid_assignments[student_nr]):
                    if possible_assignment.assignment == tuple(reference_courses):
                        matching_index = index
                        break
                if matching_index is not None:
                    for index, possible_assignment in enumerate(valid_assignments[student_nr]):
                        var = assignment[(student_nr, index)]
                        model.AddAssumption(var if index == matching_index else var.Not())

    def _create_valid_assignments(self, solver_pass: int) -> list[list[Assignment]]:
        """
        Returns the valid assignments per student
        """
        result: list[list[Assignment]] = []
        for student_nr, student in enumerate(self.students):
            # generate all permutations of the requested course numbers (including reserves)
            course_names = student.choices
            course_numbers = [self._course_number(course_name) for course_name in course_names]
            valid_assignments: list[Assignment] = []

            # just extend the list with -1's up to the number of periods
            course_numbers += [-1] * (self.periods - len(course_numbers))

            # ensure that there are at least 'solver_pass' -1 elements in the list
            course_numbers += [-1] * (solver_pass - course_numbers.count(-1))

            for permutation in itertools.permutations(course_numbers, self.periods):
                if self._is_valid_assignment(permutation):
                    penalty = self._calculate_penalty(permutation, course_numbers[:self.periods],
                                                      course_numbers[self.periods:], student.name)
                    valid_assignments.append(Assignment(permutation, penalty))

            # Remove duplicates (may happen because of the -1's)
            valid_assignments = list({assignment: None for assignment in valid_assignments})

            # For testing the stability of our algorithm, shuffle the valid assignments
            # import random
            # random.shuffle(valid_assignments)

            result.append(valid_assignments)
        return result

    def _is_valid_assignment(self, assignment: tuple[int, ...]):
        # check if all courses are available in the requested periods
        for period, course in enumerate(assignment):
            if course >= 0 and not self.courses[course].availability[period]:
                return False
        # check if there are no duplicates
        courses = [course for course in assignment if course >= 0]
        if len(set(courses)) < len(courses):
            return False
        return True

    def _calculate_penalty(self, assignment: tuple[int, ...], choices: list[int], reserve: list[int],
                           student_name: str):
        if self.minimize_changes:
            return self._calculate_penalty_minimizing_changes(assignment, choices, reserve, student_name)
        else:
            return self._calculate_penalty_preferring_priority(assignment, choices, reserve)

    def _calculate_penalty_minimizing_changes(self, assignment: tuple[int, ...], choices: list[int],
                                              reserve: list[int], student_name: str):
        prev_course_names = self.data.get_previous_result(student_name)
        if not prev_course_names:
            return self._calculate_penalty_preferring_priority(assignment, choices, reserve)

        prev_course_numbers = [self._course_number(course_name) for course_name in prev_course_names]
        penalty = 0
        reserves_used = 0
        for idx, prev_course_number in enumerate(prev_course_numbers):
            if prev_course_number != -1 and prev_course_number != assignment[idx]:
                penalty += 1

        for course in reserve:
            if course != -1 and course in assignment:
                reserves_used += 1

        return penalty + reserves_used ** 2 * 10 + self.unsolvable_penalty(assignment, choices, reserve)

    def _calculate_penalty_preferring_priority(self, assignment: tuple[int, ...], choices: list[int],
                                               reserve: list[int]):
        penalty = 0
        reserves_used = 0

        # filter empty choices
        ordered_choices = [course for course in choices if course != -1]

        for i, course in enumerate(ordered_choices):
            if course not in assignment:
                penalty += 3 - i  # 3 if the first choice is not assigned, 2 if the second, etc.

        for course in reserve:
            if course != -1 and course in assignment:
                reserves_used += 1

        return penalty + reserves_used ** 2 * 10 + self.unsolvable_penalty(assignment, choices, reserve)

    def unsolvable_penalty(self, assignment: tuple[int, ...], choices: list[int], reserve: list[int]):
        assigned_count = len([course for course in assignment if course != -1])
        choice_count = len([course for course in choices if course != -1]) + len(
            [course for course in reserve if course != -1])
        assignable_count = min(self.periods, choice_count)
        # short = choice_count - assigned_count if choice_count > assigned_count else 0
        short = assignable_count - assigned_count
        return short ** 2 * UNSOLVABLE_PENALTY

    def _calculate_combination_penalties(self, model, valid_assignments: list[list[Assignment]], assignment) -> tuple[
        list[ObjLinearExprT], list[int]]:
        c_expr: list[ObjLinearExprT] = []
        c_weights: list[int] = []

        pairs_with_penalty = []
        for pair in self.data.config.together:
            pairs_with_penalty.append((pair, -5))
        for pair in self.data.config.apart:
            pairs_with_penalty.append((pair, 5))

        for pair_with_penalty in pairs_with_penalty:
            friend1_idx = self.data.index_of_student(pair_with_penalty[0][0])
            friend2_idx = self.data.index_of_student(pair_with_penalty[0][1])
            prefix = f"comb_{friend1_idx}_{friend2_idx}"

            for assignment1_index in range(len(valid_assignments[friend1_idx])):
                for assignment2_index in range(len(valid_assignments[friend2_idx])):
                    # for each course which is the same in each period, subtract 10 from the penalty (a bonus)
                    assignment1 = valid_assignments[friend1_idx][assignment1_index].assignment
                    assignment2 = valid_assignments[friend2_idx][assignment2_index].assignment
                    together_penalty = 0
                    for period in range(self.periods):
                        if assignment1[period] >= 0 and assignment1[period] == assignment2[period]:
                            together_penalty += pair_with_penalty[1]
                    if together_penalty != 0:
                        # create a new boolean variable for this combination, using AND
                        var1 = assignment[(friend1_idx, assignment1_index)]
                        var2 = assignment[(friend2_idx, assignment2_index)]
                        var1and2 = model.NewBoolVar(f"{prefix}_{assignment1_index}_{assignment2_index}")
                        model.AddBoolAnd([var1, var2]).only_enforce_if(var1and2)
                        model.AddBoolOr([var1.Not(), var2.Not()]).only_enforce_if(var1and2.Not())
                        c_expr.append(var1and2)
                        c_weights.append(together_penalty)

        return c_expr, c_weights

    def _get_result(self, solver, valid_assignments, assignment) -> list[ResultRecord]:
        def get_course_code(idx):
            if idx < 0:
                return ""
            return self.courses[idx].code

        result = []
        for student in range(len(self.students)):
            for assignment_index in range(len(valid_assignments[student])):
                if solver.Value(assignment[(student, assignment_index)]) == 1:
                    result.append(ResultRecord(self.students[student].name,
                                               [get_course_code(course) for course in
                                                valid_assignments[student][assignment_index].assignment],
                                               valid_assignments[student][assignment_index].penalty))
        return result

    def _print_valid_assignments(self, valid_assignments):
        for i, student_assignments in enumerate(valid_assignments):
            if self.data.students[i].name == "Grietje":
                print(f"Student {self.data.students[i].name}")
                for assignment in student_assignments:
                    course_codes = [self._course_code(course) for course in assignment.assignment]
                    print(f"  {",".join(course_codes)} penalty: {assignment.penalty}")

    def _course_number(self, course_name):
        for i, course in enumerate(self.courses):
            if course.code == course_name:
                return i
        return -1

    def _course_code(self, course_number):
        return '   ' if course_number < 0 else self.courses[course_number].code
