import sqlite3
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import requests
from collections import Counter

@dataclass
class LearningObjective:
    id: str
    description: str
    difficulty: int
    keywords: List[str]

@dataclass
class Course:
    id: str
    name: str
    objectives: List[LearningObjective]

@dataclass
class IndustryStandard:
    id: str
    name: str
    description: str
    keywords: List[str]

@dataclass
class JobRequirement:
    id: str
    title: str
    skills: List[str]
    
class Database:
    def __init__(self, db_name: str):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
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
            difficulty INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS objective_keywords (
            objective_id TEXT,
            keyword TEXT,
            PRIMARY KEY (objective_id, keyword),
            FOREIGN KEY (objective_id) REFERENCES learning_objectives (id)
        )
        ''')
        # ... (keep the rest of the table creation code)
        self.conn.commit()

    def add_course(self, course: Course):
        self.cursor.execute('INSERT OR REPLACE INTO courses (id, name) VALUES (?, ?)',
                            (course.id, course.name))
        for obj in course.objectives:
            self.cursor.execute('''
            INSERT OR REPLACE INTO learning_objectives (id, course_id, description, difficulty)
            VALUES (?, ?, ?, ?)
            ''', (obj.id, course.id, obj.description, obj.difficulty))
            for keyword in obj.keywords:
                self.cursor.execute('''
                INSERT OR REPLACE INTO objective_keywords (objective_id, keyword)
                VALUES (?, ?)
                ''', (obj.id, keyword))
        self.conn.commit()

    def get_course(self, course_id: str) -> Optional[Course]:
        self.cursor.execute('SELECT id, name FROM courses WHERE id = ?', (course_id,))
        course_data = self.cursor.fetchone()
        if course_data:
            self.cursor.execute('''
            SELECT lo.id, lo.description, lo.difficulty, ok.keyword 
            FROM learning_objectives lo
            LEFT JOIN objective_keywords ok ON lo.id = ok.objective_id
            WHERE lo.course_id = ?
            ''', (course_id,))
            objectives_data = self.cursor.fetchall()
            
            objectives = {}
            for obj_id, desc, diff, keyword in objectives_data:
                if obj_id not in objectives:
                    objectives[obj_id] = LearningObjective(obj_id, desc, diff, [])
                if keyword:
                    objectives[obj_id].keywords.append(keyword)
            
            return Course(course_data[0], course_data[1], list(objectives.values()))
        return None

    def get_all_courses(self) -> List[Course]:
        self.cursor.execute('SELECT id FROM courses')
        course_ids = [row[0] for row in self.cursor.fetchall()]
        return [self.get_course(course_id) for course_id in course_ids]

    # ... (keep the rest of the methods)

    def close(self):
        self.conn.close()

    def add_industry_standard(self, standard: IndustryStandard):
        self.cursor.execute('INSERT OR REPLACE INTO industry_standards (id, name, description) VALUES (?, ?, ?)',
                            (standard.id, standard.name, standard.description))
        for keyword in standard.keywords:
            self.cursor.execute('INSERT OR REPLACE INTO standard_keywords (standard_id, keyword) VALUES (?, ?)',
                                (standard.id, keyword))
        self.conn.commit()

    def get_industry_standards(self) -> List[IndustryStandard]:
        self.cursor.execute('SELECT id, name, description FROM industry_standards')
        standards = []
        for id, name, description in self.cursor.fetchall():
            self.cursor.execute('SELECT keyword FROM standard_keywords WHERE standard_id = ?', (id,))
            keywords = [row[0] for row in self.cursor.fetchall()]
            standards.append(IndustryStandard(id, name, description, keywords))
        return standards

    def add_job_requirement(self, job: JobRequirement):
        self.cursor.execute('INSERT OR REPLACE INTO job_requirements (id, title) VALUES (?, ?)',
                            (job.id, job.title))
        for skill in job.skills:
            self.cursor.execute('INSERT OR REPLACE INTO job_skills (job_id, skill) VALUES (?, ?)',
                                (job.id, skill))
        self.conn.commit()

    def get_job_requirements(self) -> List[JobRequirement]:
        self.cursor.execute('SELECT id, title FROM job_requirements')
        jobs = []
        for id, title in self.cursor.fetchall():
            self.cursor.execute('SELECT skill FROM job_skills WHERE job_id = ?', (id,))
            skills = [row[0] for row in self.cursor.fetchall()]
            jobs.append(JobRequirement(id, title, skills))
        return jobs

class IndustryAlignmentMapper:
    def __init__(self, db: Database):
        self.db = db

    def map_courses_to_standards(self) -> Dict[str, List[str]]:
        courses = self.db.get_all_courses()
        standards = self.db.get_industry_standards()
        
        course_standard_map = {}
        for course in courses:
            course_keywords = set()
            for obj in course.objectives:
                course_keywords.update(obj.keywords)
            
            matched_standards = []
            for standard in standards:
                if set(standard.keywords) & course_keywords:
                    matched_standards.append(standard.id)
            
            course_standard_map[course.id] = matched_standards
        
        return course_standard_map

    def map_courses_to_job_requirements(self) -> Dict[str, List[str]]:
        courses = self.db.get_all_courses()
        jobs = self.db.get_job_requirements()
        
        course_job_map = {}
        for course in courses:
            course_keywords = set()
            for obj in course.objectives:
                course_keywords.update(obj.keywords)
            
            matched_jobs = []
            for job in jobs:
                if set(job.skills) & course_keywords:
                    matched_jobs.append(job.id)
            
            course_job_map[course.id] = matched_jobs
        
        return course_job_map

    def identify_curriculum_gaps(self) -> List[str]:
        courses = self.db.get_all_courses()
        standards = self.db.get_industry_standards()
        jobs = self.db.get_job_requirements()

        curriculum_keywords = set()
        for course in courses:
            for obj in course.objectives:
                curriculum_keywords.update(obj.keywords)

        gaps = []
        for standard in standards:
            missing_keywords = set(standard.keywords) - curriculum_keywords
            if missing_keywords:
                gaps.append(f"Missing keywords for standard {standard.name}: {', '.join(missing_keywords)}")

        for job in jobs:
            missing_skills = set(job.skills) - curriculum_keywords
            if missing_skills:
                gaps.append(f"Missing skills for job {job.title}: {', '.join(missing_skills)}")

        return gaps

    def suggest_course_improvements(self) -> List[str]:
        courses = self.db.get_all_courses()
        standards = self.db.get_industry_standards()
        jobs = self.db.get_job_requirements()

        suggestions = []
        for course in courses:
            course_keywords = set()
            for obj in course.objectives:
                course_keywords.update(obj.keywords)

            for standard in standards:
                missing_keywords = set(standard.keywords) - course_keywords
                if missing_keywords:
                    suggestions.append(f"Course {course.id} ({course.name}) could cover these keywords from {standard.name}: {', '.join(missing_keywords)}")

            for job in jobs:
                missing_skills = set(job.skills) - course_keywords
                if missing_skills:
                    suggestions.append(f"Course {course.id} ({course.name}) could cover these skills for {job.title}: {', '.join(missing_skills)}")

        return suggestions

class JobMarketAnalyzer:
    def __init__(self):
        self.simulated_job_postings = [
            {
                "title": "Software Developer",
                "required_skills": ["python", "javascript", "git", "agile", "react", "django"]
            },
            {
                "title": "Data Analyst",
                "required_skills": ["python", "sql", "data analysis", "statistics", "tableau", "excel"]
            },
            {
                "title": "DevOps Engineer",
                "required_skills": ["linux", "aws", "docker", "kubernetes", "jenkins", "python"]
            },
            {
                "title": "Full Stack Developer",
                "required_skills": ["javascript", "react", "node.js", "mongodb", "express", "git"]
            },
            {
                "title": "Machine Learning Engineer",
                "required_skills": ["python", "tensorflow", "scikit-learn", "numpy", "pandas", "keras"]
            }
        ]

    def fetch_job_postings(self, keyword: str, location: str) -> List[Dict]:
        # Simulate fetching job postings by returning all simulated postings
        return self.simulated_job_postings

    def analyze_job_market_trends(self, job_postings: List[Dict]) -> Dict[str, int]:
        skills = Counter()
        for posting in job_postings:
            skills.update(posting.get('required_skills', []))
        return dict(skills.most_common(10))

def main():
    db = Database("curriculum_industry_alignment.db")
    mapper = IndustryAlignmentMapper(db)
    job_analyzer = JobMarketAnalyzer()  # No API key needed now

    # Sample data (keep your existing sample data)
    courses = [
        Course("CS101", "Introduction to Programming", [
            LearningObjective("CS101-1", "Understand basic programming concepts", 1, ["programming", "algorithms"]),
            LearningObjective("CS101-2", "Write simple programs", 2, ["coding", "python"]),
        ]),
        Course("CS201", "Data Structures", [
            LearningObjective("CS201-1", "Implement basic data structures", 3, ["data structures", "algorithms"]),
            LearningObjective("CS201-2", "Analyze algorithm complexity", 4, ["complexity analysis", "big O notation"]),
        ]),
    ]

    industry_standards = [
        IndustryStandard("IS001", "Programming Fundamentals", "Basic programming concepts and practices", 
                         ["programming", "algorithms", "data structures"]),
        IndustryStandard("IS002", "Software Engineering Principles", "Best practices in software development",
                         ["version control", "agile", "testing"]),
    ]

    job_requirements = [
        JobRequirement("JR001", "Junior Software Developer", 
                       ["python", "javascript", "git", "agile"]),
        JobRequirement("JR002", "Data Analyst", 
                       ["python", "sql", "data analysis", "statistics"]),
    ]

    # Add data to the database
    for course in courses:
        db.add_course(course)
    for standard in industry_standards:
        db.add_industry_standard(standard)
    for job in job_requirements:
        db.add_job_requirement(job)

    # Perform analysis
    course_standard_map = mapper.map_courses_to_standards()
    course_job_map = mapper.map_courses_to_job_requirements()
    curriculum_gaps = mapper.identify_curriculum_gaps()
    improvement_suggestions = mapper.suggest_course_improvements()

    # Analyze job market trends using simulated data
    job_postings = job_analyzer.fetch_job_postings("software developer", "New York")
    job_market_trends = job_analyzer.analyze_job_market_trends(job_postings)

    # Print results
    print("Course to Industry Standard Mapping:", course_standard_map)
    print("Course to Job Requirement Mapping:", course_job_map)
    print("Curriculum Gaps:", curriculum_gaps)
    print("Improvement Suggestions:", improvement_suggestions)
    print("Job Market Trends (Top 10 skills):", job_market_trends)

    db.close()

if __name__ == "__main__":
    main()