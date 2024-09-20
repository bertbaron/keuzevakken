import os
import random

from model import Course, Student

directory = os.path.join("data", "testset")


def generate_data(seed, periods, course_count, student_count, size_min, size_max, availability_chance):
    random.seed(seed)
    courses = []
    students = []
    for i in range(course_count):
        size = random.randint(size_min, size_max)
        availability = "".join("1" if random.random() < availability_chance else "0" for _ in range(4))
        code = f"c{i}"
        courses.append(Course(code, size, availability))

    for i in range(student_count):
        choices = [course.name for course in courses]
        random.shuffle(choices)
        count = random.randint(periods - 1, periods + 1)
        students.append(Student(f"s{i}", choices[:count]))

    with open(os.path.join(directory, "vakken.csv"), "w") as f:
        f.write("code,size,periods,name\n")
        for course in courses:
            availability = "".join("1" if available else "0" for available in course.availability)
            f.write(f"{course.name},{course.size},{availability},{course.name}\n")

    with open(os.path.join(directory, f"keuzes-a.csv"), "w") as f:
        f.write("naam,k1,k2,k3,k4,k5,k6\n")
        for student in students:
            f.write(f"{student.name},{','.join(student.choices)}\n")
    print()


generate_data(
    seed=42,
    periods=5,
    course_count=20,
    student_count=200,
    size_min=10,
    size_max=20,
    availability_chance=0.9
)
