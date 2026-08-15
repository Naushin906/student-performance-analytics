import time
from backend.database import DatabaseConnection

queries = {
    "Query 1: Summary": """
        SELECT 
            ROUND(AVG(current_gpa), 2) as avg_gpa,
            ROUND(AVG(attendance_pct), 2) as avg_attendance,
            COUNT(DISTINCT student_id) as total_students
        FROM (
            SELECT s.student_id, AVG(sp.current_gpa) as current_gpa, AVG(a.attendance_pct) as attendance_pct
            FROM students s
            JOIN student_performance sp ON s.student_id = sp.student_id
            JOIN attendance a ON s.student_id = a.student_id AND sp.subject_id = a.subject_id
            GROUP BY s.student_id
        )
    """,
    "Query 2: Subjects Pass/Fail": """
        WITH SubjectStats AS (
            SELECT 
                s.subject_id,
                s.subject_name,
                s.department,
                COUNT(p.student_id) as total_students,
                SUM(CASE WHEN p.performance_index >= 50.0 THEN 1 ELSE 0 END) as passed_students,
                AVG(p.performance_index) as avg_performance,
                AVG(a.final_exam) as avg_final_exam
            FROM subjects s
            JOIN student_performance p ON s.subject_id = p.subject_id
            JOIN assessments a ON p.student_id = a.student_id AND p.subject_id = a.subject_id
            GROUP BY s.subject_id, s.subject_name, s.department
        )
        SELECT 
            subject_id,
            subject_name,
            department,
            total_students,
            passed_students,
            ROUND((CAST(passed_students AS REAL) / total_students) * 100, 2) as pass_rate,
            ROUND((1.0 - CAST(passed_students AS REAL) / total_students) * 100, 2) as fail_rate,
            ROUND(avg_performance, 2) as avg_score,
            ROUND(avg_final_exam, 2) as avg_final_exam
        FROM SubjectStats
        ORDER BY pass_rate ASC
    """,
    "Query 3: Department Performance": """
        WITH DeptStats AS (
            SELECT 
                s.department,
                AVG(sp.current_gpa) as avg_gpa,
                AVG(a.attendance_pct) as avg_attendance,
                COUNT(DISTINCT s.student_id) as student_count
            FROM students s
            JOIN student_performance sp ON s.student_id = sp.student_id
            JOIN attendance a ON s.student_id = a.student_id AND sp.subject_id = a.subject_id
            GROUP BY s.department
        )
        SELECT 
            department,
            ROUND(avg_gpa, 2) as avg_gpa,
            ROUND(avg_attendance, 2) as avg_attendance,
            student_count,
            RANK() OVER (ORDER BY avg_gpa DESC) as dept_rank
        FROM DeptStats
    """,
    "Query 4: Top 10 Students": """
        WITH StudentGPAs AS (
            SELECT 
                s.student_id,
                s.student_name,
                s.department,
                AVG(sp.current_gpa) as avg_gpa,
                AVG(a.attendance_pct) as avg_attendance
            FROM students s
            JOIN student_performance sp ON s.student_id = sp.student_id
            JOIN attendance a ON s.student_id = a.student_id AND sp.subject_id = a.subject_id
            GROUP BY s.student_id, s.student_name, s.department
        ),
        RankedStudents AS (
            SELECT 
                student_id,
                student_name,
                department,
                ROUND(avg_gpa, 2) as gpa,
                ROUND(avg_attendance, 2) as attendance,
                DENSE_RANK() OVER (ORDER BY avg_gpa DESC) as rnk
            FROM StudentGPAs
        )
        SELECT student_id, student_name, department, gpa, attendance, rnk
        FROM RankedStudents
        WHERE rnk <= 10
        ORDER BY rnk ASC
    """,
    "Query 5: Attendance vs GPA groups": """
        SELECT 
            CASE 
                WHEN a.attendance_pct >= 90 THEN '90% - 100%'
                WHEN a.attendance_pct >= 75 THEN '75% - 89%'
                WHEN a.attendance_pct >= 60 THEN '60% - 74%'
                ELSE 'Below 60%'
            END as attendance_group,
            ROUND(AVG(sp.current_gpa), 2) as avg_gpa,
            COUNT(DISTINCT s.student_id) as student_count
        FROM students s
        JOIN student_performance sp ON s.student_id = sp.student_id
        JOIN attendance a ON s.student_id = a.student_id AND sp.subject_id = a.subject_id
        GROUP BY attendance_group
        ORDER BY avg_gpa DESC
    """,
    "Query 6: Performance Trends": """
        SELECT 
            performance_trend,
            COUNT(DISTINCT student_id) as count,
            ROUND(AVG(current_gpa), 2) as avg_gpa
        FROM student_performance
        GROUP BY performance_trend
    """
}

with DatabaseConnection() as conn:
    for name, sql in queries.items():
        print(f"\nRunning {name}...")
        start = time.time()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            print(f"→ Complete in {time.time() - start:.4f}s. Rows returned: {len(rows)}")
            if rows:
                print(f"  Sample row: {dict(rows[0])}")
        except Exception as e:
            print(f"❌ Error: {e}")
