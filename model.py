from typing import NamedTuple


class ClassConfig(NamedTuple):
    code: str
    name: str = None


class Config(NamedTuple):
    periods: int
    classes: list[ClassConfig]
    together: list[list[str]]
    apart: list[list[str]]


class Course:
    def __init__(self, code: str, size: int, availability: str, name: str = None):
        self.code = code
        self.size = size
        self.availability = [c == "1" for c in availability]
        self.name = name if name else code


class Student:
    def __init__(self, name, choices):
        self.name = name
        self.choices = choices


class ResultRecord(NamedTuple):
    student: str
    courses: list[str]
    penalty: int


class CourseChoice(NamedTuple):
    code: str
    original_reserve: bool
    fits: bool


class EnrichedResultRecord(NamedTuple):
    student: str
    assigned: list[CourseChoice]  # assigned courses per period, followed by any remaining courses
    penalty: int

    @staticmethod
    def from_result_record(config: Config, courses: list[Course], result_record: ResultRecord, student: Student):
        def is_reserve(cc):
            return cc in student.choices[config.periods:]

        def get_course(cc):
            return next(course for course in courses if course.code == cc)

        # all choices that are not in the result
        remaining_codes = [course for course in student.choices if course and course not in result_record.courses]

        course_choices = []
        for period, course_code in enumerate(result_record.courses):
            if course_code:
                course_choices.append(CourseChoice(course_code, is_reserve(course_code), True))
            else:
                replaced = False
                # if possible, replace the None with a remaining course that is available in this period
                for remaining in remaining_codes:
                    course = get_course(remaining)
                    if course.availability[period]:
                        course_choices.append(CourseChoice(remaining, is_reserve(remaining), False))
                        remaining_codes.remove(remaining)
                        replaced = True
                        break

                # if not replaced,  it with the first remaining course if any
                if not replaced and remaining_codes:
                    code = remaining_codes.pop(0)
                    course_choices.append(CourseChoice(code, is_reserve(code), False))
                else:
                    course_choices.append(None)

        # add the remaining courses
        for remaining in remaining_codes:
            course_choices.append(CourseChoice(remaining, is_reserve(remaining), True))

        return EnrichedResultRecord(student.name, course_choices, result_record.penalty)


class Data:
    def __init__(self):
        self.config = None
        self.students: list[Student] = []
        self.courses: list[Course] = []
        self._result: list[ResultRecord] = []
        self._enriched_result: list[EnrichedResultRecord] = []
        self.previous_result: list[ResultRecord] | None = None
        self.previous_result_dict = None  # cache omdat er vaak lookups in worden gedaan
        self.student_to_class = {}

    def add_students(self, class_code, students):
        for student in students:
            self.students.append(student)
            self.student_to_class[student.name] = class_code

    def validate(self):
        validation_errors = []
        # check if all student choices are valid
        for student in self.students:
            for choice in student.choices:
                if choice and not any(course.code == choice for course in self.courses):
                    validation_errors.append(f"Onbekend vak {choice} voor leerling {student.name}")

        for group_name, pairs in {'Samen': self.config.together, 'Apart': self.config.apart}.items():
            for pair in pairs:
                if len(pair) != 2:
                    validation_errors.append(f"{group_name} lijst moet paren van 2 elementen bevatten")
                for student_name in pair:
                    if not any(student.name == student_name for student in self.students):
                        validation_errors.append(
                            f"{student_name} staat onder '{group_name}', maar is niet gevonden in een klas")

        # TODO check for duplicates
        for student in self.students:
            if len(student.choices) != len(set(student.choices)):
                validation_errors.append(f"Duplicaten in keuzes van leerling {student.name}")

        # TODO check with last year's data if available

        if validation_errors:
            raise HandledException("\n".join(validation_errors))

    # setter for result, which also derives the enriched result
    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value
        self._enriched_result = [
            EnrichedResultRecord.from_result_record(self.config, self.courses, record, self.get_student(record.student))
            for record in value]

    @property
    def enriched_result(self):
        return self._enriched_result

    def get_difference_count(self):
        """
        Gives the number of difference between the previous calculation. Useful to know if there are
        changes and how many after a recalculation with potentially different parameters or input.
        """

        def diffs(l1: list, l2: list) -> int:
            ll1 = ["" if x is None else x for x in l1]
            ll2 = ["" if x is None else x for x in l2]

            diff_count = 0
            for i in range(min(len(ll1), len(ll2))):
                if ll1[i] != ll2[i]:
                    diff_count += 1
            # Add the remaining elements in the longer list to the difference count
            diff_count += abs(len(ll1) - len(ll2))
            return diff_count

        previous = self.previous_result if self.previous_result else []

        pr = self._result_to_dict(previous)

        nw = self._result_to_dict(self.result)

        diff = 0
        for student in self.students:
            if student.name in pr and student.name in nw:
                diff += diffs(pr[student.name], nw[student.name])
            else:
                diff += 1

        # Add 1 for each student that is in the previous result but not in the new result
        for student in pr:
            if student not in nw:
                diff += 1

        return diff

    def get_previous_result(self, student_name):
        if not self.previous_result:
            return None

        return self._get_previous_result_dict().get(student_name)

    def _get_previous_result_dict(self):
        if not self.previous_result_dict:
            self.previous_result_dict = self._result_to_dict(self.previous_result)
        return self.previous_result_dict

    def _result_to_dict(self, result):
        return {record.student: record.courses for record in result}

    def get_course_name(self, course):
        if not course:
            return ''
        return next(c.name for c in self.courses if c.code == course)

    def get_student(self, student):
        return next(s for s in self.students if s.name == student)

    def index_of_student(self, student):
        return next(i for i, s in enumerate(self.students) if s.name == student)


class HandledException(Exception):
    """
    The app will not print a stack trace for this exception, but only the message.
    """
    def __init__(self, message: str):
        super().__init__(message)
