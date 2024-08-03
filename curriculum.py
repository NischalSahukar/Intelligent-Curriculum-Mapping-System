import sqlite3
from typing import List, Dict, Tuple
from dataclasses import dataclass
import re

@dataclass
class Skill:
    id: str
    name: str
    description: str

@dataclass
class IndustryStandard:
    id: str
    name: str
    skills: List[Skill]

@dataclass
class JobRequirement:
    id: str
    job_title: str
    skills: List[Skill]

@dataclass
class LearningObjective:
    id: str
    description: str
    skills: List[Skill]

@dataclass
class Course:
    id: str
    name: str
    objectives: List[LearningObjective]

class Database:
    def __init__(self, db_name: str):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS industry_standards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS industry_standard_skills (
            standard_id TEXT,
            skill_id TEXT,
            PRIMARY KEY (standard_id, skill_id),
            FOREIGN KEY (standard_id) REFERENCES industry_standards (id),
            FOREIGN KEY (skill_id) REFERENCES skills (id)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_requirements (
            id TEXT PRIMARY KEY,
            job_title TEXT NOT NULL
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_requirement_skills (
            job_id TEXT,
            skill_id TEXT,
            PRIMARY KEY (job_id, skill_id),
            FOREIGN KEY (job_id) REFERENCES job_requirements (id),
            FOREIGN KEY (skill_id) REFERENCES skills (id)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_objectives (
            id TEXT PRIMARY KEY,
            course_id TEXT,
            description TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_objective_skills (
            objective_id TEXT,
            skill_id TEXT,
            PRIMARY KEY (objective_id, skill_id),
            FOREIGN KEY (objective_id) REFERENCES learning_objectives (id),
            FOREIGN KEY (skill_id) REFERENCES skills (id)
        )
        ''')
        self.conn.commit()

    def add_skill(self, skill: Skill):
        self.cursor.execute('INSERT OR REPLACE INTO skills (id, name, description) VALUES (?, ?, ?)',
                            (skill.id, skill.name, skill.description))
        self.conn.commit()

    def add_industry_standard(self, standard: IndustryStandard):
        self.cursor.execute('INSERT OR REPLACE INTO industry_standards (id, name) VALUES (?, ?)',
                            (standard.id, standard.name))
        for skill in standard.skills:
            self.cursor.execute('INSERT OR REPLACE INTO industry_standard_skills (standard_id, skill_id) VALUES (?, ?)',
                                (standard.id, skill.id))
        self.conn.commit()

    def add_job_requirement(self, job: JobRequirement):
        self.cursor.execute('INSERT OR REPLACE INTO job_requirements (id, job_title) VALUES (?, ?)',
                            (job.id, job.job_title))
        for skill in job.skills:
            self.cursor.execute('INSERT OR REPLACE INTO job_requirement_skills (job_id, skill_id) VALUES (?, ?)',
                                (job.id, skill.id))
        self.conn.commit()

    def add_course(self, course: Course):
        self.cursor.execute('INSERT OR REPLACE INTO courses (id, name) VALUES (?, ?)',
                            (course.id, course.name))
        for obj in course.objectives:
            self.cursor.execute('INSERT OR REPLACE INTO learning_objectives (id, course_id, description) VALUES (?, ?, ?)',
                                (obj.id, course.id, obj.description))
            for skill in obj.skills:
                self.cursor.execute('INSERT OR REPLACE INTO learning_objective_skills (objective_id, skill_id) VALUES (?, ?)',
                                    (obj.id, skill.id))
        self.conn.commit()

    def get_all_skills(self) -> List[Skill]:
        self.cursor.execute('SELECT id, name, description FROM skills')
        return [Skill(id, name, description) for id, name, description in self.cursor.fetchall()]

    def get_all_industry_standards(self) -> List[IndustryStandard]:
        self.cursor.execute('SELECT id, name FROM industry_standards')
        standards = []
        for standard_id, name in self.cursor.fetchall():
            self.cursor.execute('SELECT skill_id FROM industry_standard_skills WHERE standard_id = ?', (standard_id,))
            skill_ids = [row[0] for row in self.cursor.fetchall()]
            skills = [skill for skill in self.get_all_skills() if skill.id in skill_ids]
            standards.append(IndustryStandard(standard_id, name, skills))
        return standards

    def get_all_job_requirements(self) -> List[JobRequirement]:
        self.cursor.execute('SELECT id, job_title FROM job_requirements')
        jobs = []
        for job_id, job_title in self.cursor.fetchall():
            self.cursor.execute('SELECT skill_id FROM job_requirement_skills WHERE job_id = ?', (job_id,))
            skill_ids = [row[0] for row in self.cursor.fetchall()]
            skills = [skill for skill in self.get_all_skills() if skill.id in skill_ids]
            jobs.append(JobRequirement(job_id, job_title, skills))
        return jobs

    def get_all_courses(self) -> List[Course]:
        self.cursor.execute('SELECT id, name FROM courses')
        courses = []
        for course_id, name in self.cursor.fetchall():
            self.cursor.execute('SELECT id, description FROM learning_objectives WHERE course_id = ?', (course_id,))
            objectives = []
            for obj_id, description in self.cursor.fetchall():
                self.cursor.execute('SELECT skill_id FROM learning_objective_skills WHERE objective_id = ?', (obj_id,))
                skill_ids = [row[0] for row in self.cursor.fetchall()]
                skills = [skill for skill in self.get_all_skills() if skill.id in skill_ids]
                objectives.append(LearningObjective(obj_id, description, skills))
            courses.append(Course(course_id, name, objectives))
        return courses

    def close(self):
        self.conn.close()

@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    description: str

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Skill):
            return NotImplemented
        return self.id == other.id
    
class CurriculumMapper:
    def __init__(self, db: Database):
        self.db = db

    def map_course_to_industry_standards(self, course: Course) -> Dict[str, float]:
        standards = self.db.get_all_industry_standards()
        results = {}
        course_skills = self._get_course_skills(course)
        
        for standard in standards:
            matching_skills = set(skill.id for skill in standard.skills) & set(skill.id for skill in course_skills)
            percentage = len(matching_skills) / len(standard.skills) * 100 if standard.skills else 0
            results[standard.name] = round(percentage, 2)
        
        return results

    def map_course_to_job_requirements(self, course: Course) -> Dict[str, float]:
        jobs = self.db.get_all_job_requirements()
        results = {}
        course_skills = self._get_course_skills(course)
        
        for job in jobs:
            matching_skills = set(skill.id for skill in job.skills) & set(skill.id for skill in course_skills)
            percentage = len(matching_skills) / len(job.skills) * 100 if job.skills else 0
            results[job.job_title] = round(percentage, 2)
        
        return results

    def _get_course_skills(self, course: Course) -> set[Skill]:
        skills = set()
        for objective in course.objectives:
            skills.update(objective.skills)
        return skills

    def suggest_curriculum_improvements(self, courses: List[Course]) -> List[str]:
        all_standards = self.db.get_all_industry_standards()
        all_jobs = self.db.get_all_job_requirements()
        
        required_skills = set()
        for standard in all_standards:
            required_skills.update(skill.id for skill in standard.skills)
        for job in all_jobs:
            required_skills.update(skill.id for skill in job.skills)
        
        covered_skills = set()
        for course in courses:
            covered_skills.update(skill.id for skill in self._get_course_skills(course))
        
        missing_skills = required_skills - covered_skills
        all_skills = {skill.id: skill for skill in self.db.get_all_skills()}
        
        suggestions = []
        if missing_skills:
            suggestions.append("Consider adding the following skills to your curriculum:")
            for skill_id in missing_skills:
                skill = all_skills.get(skill_id)
                if skill:
                    suggestions.append(f"- {skill.name}: {skill.description}")
        
        return suggestions
    
def input_skill() -> Skill:
    skill_id = input("Enter skill ID: ")
    name = input("Enter skill name: ")
    description = input("Enter skill description: ")
    return Skill(skill_id, name, description)

def input_learning_objective() -> LearningObjective:
    obj_id = input("Enter learning objective ID: ")
    description = input("Enter learning objective description: ")
    print("Enter skills for this learning objective:")
    skills = []
    while True:
        skill = input_skill()
        skills.append(skill)
        if input("Add another skill? (y/n): ").lower() != 'y':
            break
    return LearningObjective(obj_id, description, skills)

def input_course() -> Course:
    course_id = input("Enter course ID: ")
    name = input("Enter course name: ")
    print("Enter learning objectives for this course:")
    objectives = []
    while True:
        objective = input_learning_objective()
        objectives.append(objective)
        if input("Add another learning objective? (y/n): ").lower() != 'y':
            break
    return Course(course_id, name, objectives)

def main():
    db = Database("curriculum_mapping.db")

    # Sample skills
    skills = [
        Skill("SKILL1", "Python Programming", "Ability to write Python code"),
        Skill("SKILL2", "Data Structures", "Understanding of basic data structures"),
        Skill("SKILL3", "Machine Learning", "Knowledge of ML algorithms"),
        Skill("SKILL4", "Database Design", "Ability to design and implement databases"),
        Skill("SKILL5", "Web Development", "Skills in HTML, CSS, and JavaScript"),
        Skill("SKILL6", "Cloud Computing", "Understanding of cloud platforms and services"),
        Skill("SKILL7", "Cybersecurity", "Knowledge of security principles and practices"),
        Skill("SKILL8", "Agile Methodologies", "Experience with Agile development processes"),
        Skill("SKILL9", "DevOps", "Understanding of DevOps practices and tools"),
        Skill("SKILL10", "Big Data", "Experience with big data technologies"),
    ]

    for skill in skills:
        db.add_skill(skill)

    industry_standards = [
        IndustryStandard("STD1", "Software Development", [skills[0], skills[1], skills[4], skills[7]]),
        IndustryStandard("STD2", "Data Science", [skills[0], skills[2], skills[3], skills[9]]),
        IndustryStandard("STD3", "Cloud Architecture", [skills[5], skills[6], skills[8]]),
        IndustryStandard("STD4", "Web Technologies", [skills[4], skills[5], skills[8]]),
        IndustryStandard("STD5", "Artificial Intelligence", [skills[2], skills[9], skills[0]]),
    ]

    for standard in industry_standards:
        db.add_industry_standard(standard)

    job_requirements = [
        JobRequirement("JOB1", "Junior Developer", [skills[0], skills[1], skills[4], skills[7]]),
        JobRequirement("JOB2", "Data Analyst", [skills[0], skills[2], skills[3], skills[9]]),
        JobRequirement("JOB3", "Cloud Engineer", [skills[5], skills[6], skills[8], skills[0]]),
        JobRequirement("JOB4", "Web Developer", [skills[4], skills[0], skills[5]]),
        JobRequirement("JOB5", "Machine Learning Engineer", [skills[2], skills[0], skills[9], skills[3]]),
        JobRequirement("JOB6", "DevOps Engineer", [skills[8], skills[5], skills[6], skills[0]]),
        JobRequirement("JOB7", "Full Stack Developer", [skills[0], skills[4], skills[3], skills[5], skills[8]]),
    ]

    for job in job_requirements:
        db.add_job_requirement(job)

    # Input courses from user
    courses = []
    while True:
        print("\nEnter a new course:")
        course = input_course()
        courses.append(course)
        db.add_course(course)
        if input("Add another course? (y/n): ").lower() != 'y':
            break

    mapper = CurriculumMapper(db)

    # Analyze courses
    for course in courses:
        print(f"\nAnalyzing course: {course.name}")
        industry_mapping = mapper.map_course_to_industry_standards(course)
        job_mapping = mapper.map_course_to_job_requirements(course)
        
        print("Industry Standards Alignment:")
        for standard, percentage in industry_mapping.items():
            print(f"- {standard}: {percentage}%")
        
        print("Job Requirements Alignment:")
        for job, percentage in job_mapping.items():
            print(f"- {job}: {percentage}%")

    # Suggest improvements
    suggestions = mapper.suggest_curriculum_improvements(courses)
    if suggestions:
        print("\nSuggested Improvements:")
        for suggestion in suggestions:
            print(suggestion)
    else:
        print("\nNo improvements suggested. The curriculum aligns well with industry standards and job requirements.")

    db.close()

if __name__ == "__main__":
    main()