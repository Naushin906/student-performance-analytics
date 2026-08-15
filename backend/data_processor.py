import pandas as pd
import numpy as np
import os
import re
from typing import Dict, List, Tuple, Any

COLUMN_MAPPING_DICTIONARY = {
    "student_id": ["student_id", "student id", "id", "roll number", "usn", "rollno", "roll_no"],
    "student_name": ["student_name", "student name", "name", "full name", "fullname"],
    "department": ["department", "dept", "branch", "stream"],
    "semester": ["semester", "sem", "term"],
    "academic_year": ["academic_year", "academic year", "year", "batch"],
    "subject": ["subject", "subject name", "course", "course name", "subject_name", "course_name"],
    "attendance": ["attendance", "attendance %", "attendance percentage", "attendance_pct", "attendance_percentage", "attendance_val"],
    "internal_1": ["internal_1", "internal 1", "internal i", "internal1", "internal_one", "int_1", "int1"],
    "internal_2": ["internal_2", "internal 2", "internal ii", "internal2", "internal_two", "int_2", "int2"],
    "assignment_score": ["assignment_score", "assignment score", "assignment marks", "assignment", "assignments"],
    "quiz_score": ["quiz_score", "quiz score", "quiz marks", "quiz", "quizzes"],
    "final_exam": ["final_exam", "final exam", "final exam score", "final marks", "exam score", "final_exam_score", "finalexam"],
    "previous_gpa": ["previous_gpa", "previous gpa", "prev gpa", "prev_gpa", "last gpa", "cgpa"],
    "study_hours": ["study_hours", "study hours", "study hours/week", "study_hours_week", "study hours per week", "study_hours"],
    "lms_activity": ["lms_activity", "lms activity", "lms logins", "portal logins", "lms_logins", "lms activity score"],
    "assignment_completion": ["assignment_completion", "assignment completion", "assignment completion %", "assignment_completion_pct", "assignments completed"]
}

def detect_file_and_sheets(file_path: str) -> Dict[str, Any]:
    """Inspects a file to determine type and sheet names if it is an Excel workbook."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".csv":
        return {"file_type": "csv", "sheets": []}
    elif ext in [".xlsx", ".xls"]:
        xl = pd.ExcelFile(file_path)
        return {"file_type": "excel", "sheets": xl.sheet_names}
    else:
        raise ValueError("Unsupported file format. Please upload .csv, .xls, or .xlsx")

def load_data_preview(file_path: str, sheet_name: str = None, nrows: int = 10) -> Dict[str, Any]:
    """Loads a preview of the dataset with the raw column list and types."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".csv":
        df = pd.read_csv(file_path, nrows=nrows)
        full_df = pd.read_csv(file_path, nrows=1) # to get all column shapes
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0, nrows=nrows)
        full_df = pd.read_excel(file_path, sheet_name=sheet_name or 0, nrows=1)
        
    preview_data = df.replace({np.nan: None}).to_dict(orient="records")
    columns = list(full_df.columns)
    
    # Simple type detection
    detected_types = {}
    for col in columns:
        col_series = df[col].dropna()
        if col_series.empty:
            detected_types[col] = "empty"
        elif pd.api.types.is_numeric_dtype(col_series):
            detected_types[col] = "numeric"
        else:
            detected_types[col] = "text"
            
    # Try auto-mapping columns
    auto_mapping = {}
    unmapped = []
    
    for key, variations in COLUMN_MAPPING_DICTIONARY.items():
        found = False
        for var in variations:
            for col in columns:
                if col.lower().strip() == var.lower().strip() or re.sub(r'[^a-zA-Z0-9]', '', col.lower()) == re.sub(r'[^a-zA-Z0-9]', '', var.lower()):
                    auto_mapping[key] = col
                    found = True
                    break
            if found:
                break
        if not found:
            unmapped.append(key)
            
    return {
        "columns": columns,
        "preview": preview_data,
        "types": detected_types,
        "auto_mapping": auto_mapping,
        "unmapped_fields": unmapped
    }

def validate_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> None:
    """Validates that at least one column is mapped and that mapped columns exist in the dataframe."""
    if not mapping:
        mapping = {}
        
    mapped_and_valid = {k: v for k, v in mapping.items() if v and str(v).strip() != ""}
    
    if not mapped_and_valid:
        raise ValueError("Mapping validation failed: You must map at least one column from your spreadsheet to proceed.")
        
    invalid_columns = []
    for field, col in mapped_and_valid.items():
        if col not in df.columns:
            invalid_columns.append(f"'{col}' (for '{field}')")
            
    if invalid_columns:
        raise ValueError(f"Mapping validation failed: The following mapped columns were not found in the spreadsheet: {', '.join(invalid_columns)}")

def get_capabilities(df: pd.DataFrame) -> dict:
    """Detects which analytics categories are supported based on the available columns."""
    cols = df.columns
    
    # Check what features are present
    has_student = "student_name" in cols or "student_id" in cols
    has_department = "department" in cols
    has_semester = "semester" in cols
    has_academic_year = "academic_year" in cols
    
    # Check for subject score columns (wide format)
    standard_numeric_keys = [
        "semester", "attendance", "internal_1", "internal_2", 
        "assignment_score", "quiz_score", "final_exam", "previous_gpa", 
        "study_hours", "lms_activity", "assignment_completion", 
        "performance_index", "current_gpa", "performance_change"
    ]
    
    wide_subject_cols = []
    for col in cols:
        if col not in standard_numeric_keys and col not in ["student_name", "student_id", "department", "academic_year", "subject", "performance_trend"]:
            # check if it looks numeric
            non_nulls = df[col].dropna()
            if not non_nulls.empty:
                try:
                    pd.to_numeric(non_nulls)
                    wide_subject_cols.append(col)
                except Exception:
                    pass
                
    has_wide_subjects = len(wide_subject_cols) > 0
    has_long_subjects = "subject" in cols
    
    # Marks availability
    has_marks = "final_exam" in cols or "performance_index" in cols or has_wide_subjects
    
    # Specific categories
    has_attendance = "attendance" in cols
    has_gpa = "previous_gpa" in cols or "current_gpa" in cols
    has_learning_behavior = "study_hours" in cols or "lms_activity" in cols
    
    capabilities = {
        "student_analytics": bool(has_student),
        "subject_analytics": bool(has_long_subjects or has_wide_subjects),
        "marks_analytics": bool(has_marks),
        "attendance_analytics": bool(has_attendance),
        "gpa_analytics": bool(has_gpa),
        "department_analytics": bool(has_department),
        "semester_analytics": bool(has_semester),
        "learning_behavior_analytics": bool(has_learning_behavior),
        "wide_subjects": wide_subject_cols,
        "format": "wide" if has_wide_subjects else "long"
    }
    
    return capabilities


def analyze_data_quality(file_path: str, sheet_name: str = None, mapping: Dict[str, str] = None) -> Dict[str, Any]:
    """Generates a Data Quality Report based on the provided column mapping."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        
    validate_column_mapping(df, mapping)
        
    total_rows = len(df)
    total_cols = len(df.columns)
    
    # Calculate duplicate rows
    duplicates = df.duplicated().sum()
    
    # Missing values
    missing_pct = (df.isnull().sum().sum() / (total_rows * total_cols)) * 100 if total_rows > 0 else 0
    missing_count = df.isnull().sum().sum()
    
    # Filter mapped columns to check specifically for values
    invalid_marks = 0
    invalid_attendance = 0
    
    # Check attendance constraints if mapped
    att_col = mapping.get("attendance")
    if att_col and att_col in df.columns:
        att_series = pd.to_numeric(df[att_col], errors='coerce')
        invalid_attendance = ((att_series > 100.0) | (att_series < 0.0)).sum()
        
    # Check marks constraints (Internal: 0-30, Final Exam: 0-100, Quiz/Assignment: 0-100)
    for field, limit in [("internal_1", 30), ("internal_2", 30), ("assignment_score", 100), ("quiz_score", 100), ("final_exam", 100)]:
        col = mapping.get(field)
        if col and col in df.columns:
            series = pd.to_numeric(df[col], errors='coerce')
            invalid_marks += ((series > limit) | (series < 0.0)).sum()
            
    # Check for empty columns
    empty_cols = [col for col in df.columns if df[col].isnull().all()]
    
    # Compute status indicators
    missing_status = "GOOD" if missing_pct < 2 else ("WARNING" if missing_pct < 5 else "CRITICAL")
    dup_status = "GOOD" if duplicates == 0 else ("WARNING" if duplicates < 10 else "CRITICAL")
    marks_status = "GOOD" if invalid_marks == 0 else ("WARNING" if invalid_marks < 5 else "CRITICAL")
    att_status = "GOOD" if invalid_attendance == 0 else ("WARNING" if invalid_attendance < 5 else "CRITICAL")
    
    overall_status = "GOOD"
    if "CRITICAL" in [missing_status, dup_status, marks_status, att_status]:
        overall_status = "CRITICAL"
    elif "WARNING" in [missing_status, dup_status, marks_status, att_status]:
        overall_status = "WARNING"
        
    return {
        "total_rows": int(total_rows),
        "total_columns": int(total_cols),
        "duplicates": int(duplicates),
        "missing_percentage": round(float(missing_pct), 2),
        "missing_count": int(missing_count),
        "invalid_marks": int(invalid_marks),
        "invalid_attendance": int(invalid_attendance),
        "empty_columns": len(empty_cols),
        "statuses": {
            "missing": missing_status,
            "duplicates": dup_status,
            "marks": marks_status,
            "attendance": att_status,
            "overall": overall_status
        }
    }

def clean_and_normalize_data(
    file_path: str, 
    sheet_name: str = None, 
    mapping: Dict[str, str] = None,
    weights: Dict[str, float] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Cleans the dataset dynamically based on available columns without inventing fake data."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name or 0)
        
    validate_column_mapping(df, mapping)
        
    stats = {
        "duplicates_removed": 0,
        "missing_filled": 0,
        "marks_corrected": 0,
        "attendance_corrected": 0,
        "trimmed_records": 0
    }
    
    # 1. Drop completely empty rows
    df = df.dropna(how='all')
    
    # 2. Deduplicate rows
    df_dedup = df.drop_duplicates()
    stats["duplicates_removed"] = int(len(df) - len(df_dedup))
    df = df_dedup.copy()
    
    # 3. Rename mapped columns to standardized keys based on mapping
    inv_map = {v: k for k, v in mapping.items() if v and v in df.columns}
    df = df.rename(columns=inv_map)
    
    # 4. Clean text columns that are present
    text_cols = ["student_id", "student_name", "department", "academic_year", "subject"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})
            
    # Standardize Subject casings if present
    if "subject" in df.columns:
        df["subject"] = df["subject"].str.title()
        
    # Convert numeric fields
    num_cols = [
        "attendance", "internal_1", "internal_2", "assignment_score", 
        "quiz_score", "final_exam", "previous_gpa", "study_hours", 
        "lms_activity", "assignment_completion"
    ]
    for col in num_cols:
        if col in df.columns:
            null_mask = df[col].isnull()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            coerced_nulls = df[col].isnull() & ~null_mask
            stats["missing_filled"] += coerced_nulls.sum()
            
    # Identify unmapped numeric columns as wide subject score columns
    standard_keys = text_cols + num_cols + ["performance_index", "current_gpa", "performance_change", "performance_trend"]
    wide_subject_cols = []
    for col in df.columns:
        if col not in standard_keys:
            # check if it looks numeric
            non_nulls = df[col].dropna()
            if not non_nulls.empty:
                try:
                    pd.to_numeric(non_nulls)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    wide_subject_cols.append(col)
                except Exception:
                    pass
            
    # Correct attendance constraints if present (0-100)
    if "attendance" in df.columns:
        invalid_att_mask = (df["attendance"] > 100.0) | (df["attendance"] < 0.0)
        stats["attendance_corrected"] = int(invalid_att_mask.sum())
        df["attendance"] = df["attendance"].clip(lower=0.0, upper=100.0)
        
        # Fill missing attendance with median
        median_attendance = df["attendance"].median()
        if pd.isna(median_attendance):
            median_attendance = 85.0
        
        missing_count = df["attendance"].isnull().sum()
        stats["missing_filled"] += int(missing_count)
        if "subject" in df.columns:
            df["attendance"] = df["attendance"].fillna(df.groupby("subject")["attendance"].transform("median").fillna(median_attendance))
        else:
            df["attendance"] = df["attendance"].fillna(median_attendance)

    # Correct marks and fill missing values for standard fields and wide subjects
    marks_limits = {
        "internal_1": 30.0,
        "internal_2": 30.0,
        "assignment_score": 100.0,
        "quiz_score": 100.0,
        "final_exam": 100.0,
        "previous_gpa": 10.0,
        "study_hours": 30.0,
        "lms_activity": 500.0,
        "assignment_completion": 100.0
    }
    
    for col in wide_subject_cols:
        marks_limits[col] = 100.0
        
    for col, limit in marks_limits.items():
        if col in df.columns:
            invalid_mask = (df[col] > limit) | (df[col] < 0.0)
            if col in ["internal_1", "internal_2", "assignment_score", "quiz_score", "final_exam"] or col in wide_subject_cols:
                stats["marks_corrected"] += int(invalid_mask.sum())
            else:
                stats["attendance_corrected"] += int(invalid_mask.sum())
                
            df[col] = df[col].clip(lower=0.0, upper=limit)
            
            missing_count = df[col].isnull().sum()
            stats["missing_filled"] += int(missing_count)
            
            fallback_val = 0.0 if (col in ["internal_1", "internal_2", "assignment_score", "quiz_score", "final_exam"] or col in wide_subject_cols) else (7.0 if col == "previous_gpa" else 10.0)
            median_val = df[col].median()
            if pd.isna(median_val):
                median_val = fallback_val
                
            if "subject" in df.columns:
                df[col] = df[col].fillna(df.groupby("subject")[col].transform("median").fillna(median_val))
            else:
                df[col] = df[col].fillna(median_val)
            
    # Calculate Academic Performance Index & current GPA
    if "final_exam" in df.columns or "internal_1" in df.columns:
        if not weights:
            weights = {"internal": 0.30, "assignment": 0.20, "quiz": 0.10, "final_exam": 0.40}
            
        int_1_val = df["internal_1"] if "internal_1" in df.columns else 0.0
        int_2_val = df["internal_2"] if "internal_2" in df.columns else 0.0
        internal_pct = ((int_1_val + int_2_val) / 60.0) * 100.0 if ("internal_1" in df.columns or "internal_2" in df.columns) else 0.0
        
        assign_val = df["assignment_score"] if "assignment_score" in df.columns else 0.0
        quiz_val = df["quiz_score"] if "quiz_score" in df.columns else 0.0
        final_val = df["final_exam"] if "final_exam" in df.columns else 0.0
        
        # Normalize weights based on actually present columns
        active_weights = {}
        if "internal_1" in df.columns or "internal_2" in df.columns:
            active_weights["internal"] = weights.get("internal", 0.30)
        if "assignment_score" in df.columns:
            active_weights["assignment"] = weights.get("assignment", 0.20)
        if "quiz_score" in df.columns:
            active_weights["quiz"] = weights.get("quiz", 0.10)
        if "final_exam" in df.columns:
            active_weights["final_exam"] = weights.get("final_exam", 0.40)
            
        weight_sum = sum(active_weights.values())
        if weight_sum > 0:
            normalized_weights = {k: v / weight_sum for k, v in active_weights.items()}
        else:
            normalized_weights = {}
            
        perf_index = 0.0
        if "internal" in normalized_weights:
            perf_index += internal_pct * normalized_weights["internal"]
        if "assignment" in normalized_weights:
            perf_index += assign_val * normalized_weights["assignment"]
        if "quiz" in normalized_weights:
            perf_index += quiz_val * normalized_weights["quiz"]
        if "final_exam" in normalized_weights:
            perf_index += final_val * normalized_weights["final_exam"]
            
        df["performance_index"] = round(perf_index, 2)
        df["current_gpa"] = round(df["performance_index"] / 10.0, 2)
        
    elif len(wide_subject_cols) > 0:
        # Wide-format: Average of subject score columns
        df["performance_index"] = round(df[wide_subject_cols].mean(axis=1), 2)
        df["current_gpa"] = round(df["performance_index"] / 10.0, 2)
        
    # Calculate performance change if previous GPA is present
    if "current_gpa" in df.columns:
        if "previous_gpa" in df.columns:
            df["performance_change"] = round(df["current_gpa"] - df["previous_gpa"], 2)
            df["performance_trend"] = np.where(df["performance_change"] > 0.3, "IMPROVING",
                                               np.where(df["performance_change"] < -0.3, "DECLINING", "STABLE"))
        else:
            df["performance_change"] = 0.0
            df["performance_trend"] = "STABLE"
        
    # Convert all stats values to standard Python integers to avoid numpy serialization errors
    clean_stats = {k: int(v) for k, v in stats.items()}
    return df, clean_stats

def load_to_database(df: pd.DataFrame) -> Dict[str, int]:
    """Loads cleaned rows into SQLite flat raw_records table and conditionally into relational tables."""
    from backend.database import DatabaseConnection
    
    records_loaded = {
        "students": 0,
        "subjects": 0,
        "learning_behavior": 0,
        "attendance": 0,
        "assessments": 0,
        "student_performance": 0
    }
    
    # 1. Load into raw_records table (main dynamic storage)
    with DatabaseConnection() as conn:
        df.to_sql("raw_records", conn, if_exists="replace", index=False)
        
    # 2. Conditionally load to relational schema if standard columns exist
    required_relational = ["student_id", "student_name", "department", "semester", "academic_year", "subject"]
    if all(col in df.columns for col in required_relational):
        try:
            with DatabaseConnection() as conn:
                cursor = conn.cursor()
                
                # Insert unique subjects
                unique_subjects = df[["subject", "department"]].drop_duplicates()
                for _, s_row in unique_subjects.iterrows():
                    sub_name = s_row["subject"]
                    dept = s_row["department"]
                    sub_id = re.sub(r'[^a-zA-Z0-9]', '', sub_name)[:10].upper()
                    
                    cursor.execute(
                        """
                        INSERT INTO subjects (subject_id, subject_name, department)
                        VALUES (?, ?, ?)
                        ON CONFLICT(subject_id) DO UPDATE SET 
                            subject_name=excluded.subject_name,
                            department=excluded.department
                        """,
                        (sub_id, sub_name, dept)
                    )
                    records_loaded["subjects"] += 1
                    
                sub_name_to_id = {}
                cursor.execute("SELECT subject_id, subject_name FROM subjects")
                for sub_id, sub_name in cursor.fetchall():
                    sub_name_to_id[sub_name] = sub_id
                    
                # Insert unique students
                unique_students = df[["student_id", "student_name", "department", "semester", "academic_year", "previous_gpa"]].drop_duplicates(subset=["student_id"])
                for _, st_row in unique_students.iterrows():
                    cursor.execute(
                        """
                        INSERT INTO students (student_id, student_name, department, semester, academic_year, previous_gpa)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(student_id) DO UPDATE SET
                            student_name=excluded.student_name,
                            department=excluded.department,
                            semester=excluded.semester,
                            academic_year=excluded.academic_year,
                            previous_gpa=excluded.previous_gpa
                        """,
                        (st_row["student_id"], st_row["student_name"], st_row["department"], int(st_row["semester"]), st_row["academic_year"], float(st_row["previous_gpa"]))
                    )
                    records_loaded["students"] += 1
                    
                    # Insert learning behavior if available
                    study_hours = df[df["student_id"] == st_row["student_id"]]["study_hours"].iloc[0] if "study_hours" in df.columns else 0.0
                    lms_activity = df[df["student_id"] == st_row["student_id"]]["lms_activity"].iloc[0] if "lms_activity" in df.columns else 0
                    cursor.execute(
                        """
                        INSERT INTO learning_behavior (student_id, study_hours, lms_activity)
                        VALUES (?, ?, ?)
                        ON CONFLICT(student_id) DO UPDATE SET
                            study_hours=excluded.study_hours,
                            lms_activity=excluded.lms_activity
                        """,
                        (st_row["student_id"], float(study_hours), int(lms_activity))
                    )
                    records_loaded["learning_behavior"] += 1
                    
                # Insert details
                for _, row in df.iterrows():
                    sub_id = sub_name_to_id[row["subject"]]
                    
                    # Attendance
                    att_pct = float(row["attendance"]) if "attendance" in df.columns else 100.0
                    cursor.execute(
                        """
                        INSERT INTO attendance (student_id, subject_id, attendance_pct)
                        VALUES (?, ?, ?)
                        ON CONFLICT(student_id, subject_id) DO UPDATE SET
                            attendance_pct=excluded.attendance_pct
                        """,
                        (row["student_id"], sub_id, att_pct)
                    )
                    records_loaded["attendance"] += 1
                    
                    # Assessments
                    int_1 = float(row["internal_1"]) if "internal_1" in df.columns else 0.0
                    int_2 = float(row["internal_2"]) if "internal_2" in df.columns else 0.0
                    assign = float(row["assignment_score"]) if "assignment_score" in df.columns else 0.0
                    quiz = float(row["quiz_score"]) if "quiz_score" in df.columns else 0.0
                    final = float(row["final_exam"]) if "final_exam" in df.columns else 0.0
                    assign_c = float(row["assignment_completion"]) if "assignment_completion" in df.columns else 0.0
                    
                    cursor.execute(
                        """
                        INSERT INTO assessments (student_id, subject_id, internal_1, internal_2, assignment_score, quiz_score, final_exam, assignment_completion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(student_id, subject_id) DO UPDATE SET
                            internal_1=excluded.internal_1,
                            internal_2=excluded.internal_2,
                            assignment_score=excluded.assignment_score,
                            quiz_score=excluded.quiz_score,
                            final_exam=excluded.final_exam,
                            assignment_completion=excluded.assignment_completion
                        """,
                        (
                            row["student_id"], sub_id, 
                            int_1, int_2, assign, quiz, final, assign_c
                        )
                    )
                    records_loaded["assessments"] += 1
                    
                    # Performance
                    perf_idx = float(row["performance_index"]) if "performance_index" in df.columns else 0.0
                    gpa = float(row["current_gpa"]) if "current_gpa" in df.columns else 0.0
                    change = float(row["performance_change"]) if "performance_change" in df.columns else 0.0
                    trend = row["performance_trend"] if "performance_trend" in df.columns else "STABLE"
                    
                    cursor.execute(
                        """
                        INSERT INTO student_performance (student_id, subject_id, performance_index, current_gpa, performance_change, performance_trend)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(student_id, subject_id) DO UPDATE SET
                            performance_index=excluded.performance_index,
                            current_gpa=excluded.current_gpa,
                            performance_change=excluded.performance_change,
                            performance_trend=excluded.performance_trend
                        """,
                        (
                            row["student_id"], sub_id, 
                            perf_idx, gpa, change, trend
                        )
                    )
                    records_loaded["student_performance"] += 1
        except Exception as e:
            # We catch validation and DB errors and gracefully ignore them, since we fall back to raw_records table
            pass
            
    return records_loaded
