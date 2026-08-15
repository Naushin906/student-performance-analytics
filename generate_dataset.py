import os
import random
import csv
import openpyxl

def generate_sample_data(num_students=150, output_csv="data/sample_students.csv", output_xlsx="data/sample_students.xlsx"):
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    # Static catalogs
    departments = ["Computer Science", "Information Technology", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering"]
    
    subjects_by_dept = {
        "Computer Science": ["Mathematics", "Programming in C", "Data Structures", "Database Management Systems", "Machine Learning"],
        "Information Technology": ["Mathematics", "Programming in C", "Web Development", "Computer Networks", "Information Security"],
        "Electrical Engineering": ["Mathematics", "Circuit Theory", "Control Systems", "Signals and Systems", "Power Electronics"],
        "Mechanical Engineering": ["Mathematics", "Thermodynamics", "Fluid Mechanics", "Machine Design", "CAD/CAM"],
        "Civil Engineering": ["Mathematics", "Surveying", "Structural Analysis", "Geotechnical Engineering", "Transportation Engineering"]
    }
    
    names_pool = [
        "Aarav Sharma", "Aditya Patel", "Ananya Rao", "Arjun Singh", "Diya Iyer",
        "Ishaan Verma", "Kavya Nair", "Krishna Reddy", "Meera Joshi", "Pranav Gupta",
        "Rohan Das", "Sanya Malhotra", "Siddharth Sen", "Tanvi Bose", "Vivaan Kapoor",
        "John Doe", "Jane Smith", "Michael Johnson", "Emily Davis", "David Miller",
        "Sarah Wilson", "James Taylor", "Linda Anderson", "Robert Thomas", "Patricia Jackson"
    ]
    
    rows = []
    
    # Generate clean records first
    for i in range(1, num_students + 1):
        student_id = f"S{1000 + i}"
        name = random.choice(names_pool)
        dept = random.choice(departments)
        sem = random.randint(1, 8)
        year = "2025-2026"
        prev_gpa = round(random.uniform(5.5, 9.8), 2)
        study_hours = round(random.uniform(2.0, 25.0), 1)
        lms_activity = random.randint(15, 180)
        
        # Determine overall academic capability (higher study hours/prev GPA means higher marks generally)
        capability = (study_hours / 25.0) * 0.4 + (prev_gpa / 10.0) * 0.4 + (lms_activity / 180.0) * 0.2
        
        # Pick subjects
        subjects = subjects_by_dept[dept]
        for sub in subjects:
            # High correlation simulation:
            # attendance depends on study hours slightly, with some random variation
            attendance = min(100.0, max(45.0, round(60.0 + 35.0 * capability + random.uniform(-10.0, 10.0), 1)))
            
            # marks based on capability and attendance
            performance_factor = capability * 0.7 + (attendance / 100.0) * 0.3
            
            # internals (out of 30)
            int_1 = round(min(30.0, max(5.0, 30.0 * performance_factor + random.uniform(-4, 4))), 1)
            int_2 = round(min(30.0, max(5.0, 30.0 * performance_factor + random.uniform(-4, 4))), 1)
            
            # assignments & quizzes (out of 100)
            assign_completion = round(min(100.0, max(20.0, 100.0 * performance_factor + random.uniform(-15, 10))), 1)
            assign_score = round(min(100.0, max(30.0, assign_completion * 0.9 + random.uniform(-10, 10))), 1)
            quiz_score = round(min(100.0, max(30.0, 100.0 * performance_factor + random.uniform(-15, 15))), 1)
            
            # final exam (out of 100)
            final_exam = round(min(100.0, max(20.0, 100.0 * performance_factor + random.uniform(-20, 10))), 1)
            
            # Subject names might have some inconsistencies for mapping tests
            sub_name = sub
            if random.random() < 0.05:
                # Add trailing space or change casing
                sub_name = sub.lower() if random.random() < 0.5 else f"{sub} "
                
            rows.append({
                "Student ID": student_id,
                "Student Name": name,
                "Department": dept,
                "Semester": sem,
                "Academic Year": year,
                "Course Name": sub_name, # Course Name instead of Subject to test column mapping
                "Attendance %": attendance, # Attendance % to test mapping
                "Internal 1": int_1,
                "Internal 2": int_2,
                "Assignment Score": assign_score,
                "Quiz Score": quiz_score,
                "Final Exam Score": final_exam,
                "Previous GPA": prev_gpa,
                "Study Hours/Week": study_hours,
                "LMS Activity": lms_activity,
                "Assignment Completion %": assign_completion
            })

    # Introduce synthetic errors & anomalies (approx 5% of records)
    total_records = len(rows)
    print(f"Generated {total_records} clean base records. Injecting anomalies...")
    
    # 1. Duplicates
    dup_indices = random.sample(range(total_records), 15)
    for idx in dup_indices:
        rows.append(rows[idx].copy())
        
    # 2. Out of bound attendance (>100% or negative)
    for _ in range(8):
        idx = random.randint(0, total_records - 1)
        rows[idx]["Attendance %"] = 112.5 if random.random() < 0.5 else -8.0
        
    # 3. Invalid Marks (internals > 30, final exam > 100, or negative)
    for _ in range(12):
        idx = random.randint(0, total_records - 1)
        field = random.choice(["Internal 1", "Internal 2", "Final Exam Score"])
        if "Internal" in field:
            rows[idx][field] = 45.0 if random.random() < 0.5 else -2.5
        else:
            rows[idx][field] = 125.0 if random.random() < 0.5 else -10.0
            
    # 4. Missing values
    for _ in range(25):
        idx = random.randint(0, total_records - 1)
        field = random.choice(["Attendance %", "Assignment Score", "Quiz Score", "Previous GPA"])
        rows[idx][field] = None
        
    # 5. String formatting issues
    for _ in range(15):
        idx = random.randint(0, total_records - 1)
        # Extra spaces
        rows[idx]["Department"] = f"  {rows[idx]['Department']}  "
        rows[idx]["Student Name"] = f" {rows[idx]['Student Name']}"

    # 6. Completely empty row
    rows.append({k: None for k in rows[0].keys()})
    rows.append({k: None for k in rows[0].keys()})

    # Shuffle rows to distribute anomalies
    random.shuffle(rows)

    # Write CSV
    headers = list(rows[0].keys())
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
            
    # Write XLSX
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Academics"
    ws.append(headers)
    for r in rows:
        ws.append([r[h] for h in headers])
        
    # Add a second dummy sheet to test sheet selector
    ws2 = wb.create_sheet(title="Institution Settings")
    ws2.append(["Setting", "Value"])
    ws2.append(["Academic Term", "Fall 2025"])
    ws2.append(["Institute Code", "EDU-9092"])
    
    wb.save(output_xlsx)
    print(f"Data generation complete: {output_csv} and {output_xlsx} saved successfully.")

if __name__ == "__main__":
    generate_sample_data()
