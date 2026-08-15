import numpy as np
import pandas as pd
import re
from scipy import stats
from backend.database import DatabaseConnection
from backend.data_processor import get_capabilities

def execute_custom_query(sql_query: str):
    """Executes a custom SQL query in a read-only fashion."""
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "create", "replace"]
    q_lower = sql_query.lower()
    for word in forbidden:
        if re.search(r'\b' + word + r'\b', q_lower):
            raise ValueError(f"Execution blocked: query contains forbidden writing command '{word}'.")
            
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        result = []
        for r in rows:
            result.append(dict(zip(columns, r)))
        return result

def get_sql_analytics(passing_threshold: float = 40.0) -> dict:
    """Runs advanced analytics dynamically on the flat raw_records table and returns structured dashboard cards."""
    analytics = {}
    
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
        if not cursor.fetchone():
            return {}
        df = pd.read_sql_query("SELECT * FROM raw_records", conn)
        
    if df.empty:
        return {}
        
    caps = get_capabilities(df)
    
    # 1. Summary card values
    summary = {}
    if "current_gpa" in df.columns:
        summary["avg_gpa"] = round(float(df["current_gpa"].dropna().mean()), 2) if not df["current_gpa"].dropna().empty else 0.0
    if "attendance" in df.columns:
        summary["avg_attendance"] = round(float(df["attendance"].dropna().mean()), 2) if not df["attendance"].dropna().empty else 0.0
        
    # Get distinct student count
    student_id_col = "student_id" if "student_id" in df.columns else ("student_name" if "student_name" in df.columns else None)
    if student_id_col:
        summary["total_students"] = int(df[student_id_col].nunique())
    else:
        summary["total_students"] = len(df)
        
    analytics["summary"] = summary
    
    # 2. Subject stats
    subject_stats = []
    if caps["format"] == "wide":
        wide_cols = caps["wide_subjects"]
        for col in wide_cols:
            series = df[col].dropna()
            total_students = len(series)
            if total_students > 0:
                passed_students = int((series >= passing_threshold).sum())
                pass_rate = round((passed_students / total_students) * 100, 2)
                fail_rate = round(100.0 - pass_rate, 2)
                avg_score = round(float(series.mean()), 2)
                
                subject_stats.append({
                    "subject_id": col.upper()[:10],
                    "subject_name": col.replace("_", " ").title(),
                    "department": "All",
                    "total_students": total_students,
                    "passed_students": passed_students,
                    "pass_rate": pass_rate,
                    "fail_rate": fail_rate,
                    "avg_score": avg_score,
                    "avg_final_exam": avg_score
                })
    else:
        if "subject" in df.columns:
            grouped = df.groupby("subject")
            for sub_name, group in grouped:
                total_students = len(group)
                score_col = "performance_index" if "performance_index" in group.columns else ("final_exam" if "final_exam" in group.columns else None)
                if score_col:
                    score_series = group[score_col].dropna()
                    if not score_series.empty:
                        th = passing_threshold
                        passed_students = int((score_series >= th).sum())
                        pass_rate = round((passed_students / total_students) * 100, 2)
                        fail_rate = round(100.0 - pass_rate, 2)
                        avg_score = round(float(score_series.mean()), 2)
                    else:
                        passed_students, pass_rate, fail_rate, avg_score = 0, 0.0, 0.0, 0.0
                else:
                    passed_students, pass_rate, fail_rate, avg_score = 0, 0.0, 0.0, 0.0
                    
                subject_stats.append({
                    "subject_id": sub_name.upper()[:10],
                    "subject_name": sub_name,
                    "department": group["department"].iloc[0] if "department" in group.columns else "All",
                    "total_students": total_students,
                    "passed_students": passed_students,
                    "pass_rate": pass_rate,
                    "fail_rate": fail_rate,
                    "avg_score": avg_score,
                    "avg_final_exam": round(float(group["final_exam"].dropna().mean()), 2) if "final_exam" in group.columns and not group["final_exam"].dropna().empty else avg_score
                })
    analytics["subjects"] = subject_stats
    
    # 3. Department statistics
    dept_stats = []
    if "department" in df.columns:
        grouped = df.groupby("department")
        for dept_name, group in grouped:
            item = {
                "department": dept_name,
                "student_count": int(group[student_id_col].nunique()) if student_id_col else len(group)
            }
            if "current_gpa" in group.columns:
                gpas = group["current_gpa"].dropna()
                item["avg_gpa"] = round(float(gpas.mean()), 2) if not gpas.empty else 0.0
            if "attendance" in group.columns:
                atts = group["attendance"].dropna()
                item["avg_attendance"] = round(float(atts.mean()), 2) if not atts.empty else 0.0
            dept_stats.append(item)
            
        sort_col = "avg_gpa" if "current_gpa" in df.columns else None
        if sort_col:
            dept_stats = sorted(dept_stats, key=lambda x: x.get(sort_col, 0), reverse=True)
            for idx, item in enumerate(dept_stats):
                item["dept_rank"] = idx + 1
    analytics["departments"] = dept_stats
    
    # 4. Top 10 performed students
    top_students = []
    if "current_gpa" in df.columns and student_id_col:
        agg_dict = {"current_gpa": "mean"}
        if "attendance" in df.columns and student_id_col != "attendance":
            agg_dict["attendance"] = "mean"
        if "department" in df.columns and student_id_col != "department":
            agg_dict["department"] = "first"
        if "student_name" in df.columns and student_id_col != "student_name":
            agg_dict["student_name"] = "first"
            
        student_gpas = df.groupby(student_id_col).agg(agg_dict).reset_index()
        student_gpas = student_gpas.sort_values(by="current_gpa", ascending=False).head(10).reset_index(drop=True)
        
        for idx, row in student_gpas.iterrows():
            top_students.append({
                "student_id": str(row[student_id_col]),
                "student_name": str(row.get("student_name", row[student_id_col])),
                "department": str(row.get("department", "All")),
                "gpa": round(float(row["current_gpa"]), 2),
                "attendance": round(float(row["attendance"]), 2) if "attendance" in row else 0.0,
                "rnk": idx + 1
            })
    analytics["top_students"] = top_students
    
    # 5. Attendance vs GPA ranges
    att_vs_gpa = []
    if "attendance" in df.columns and "current_gpa" in df.columns:
        df_temp = df.copy()
        conditions = [
            (df_temp["attendance"] >= 90),
            (df_temp["attendance"] >= 75) & (df_temp["attendance"] < 90),
            (df_temp["attendance"] >= 60) & (df_temp["attendance"] < 75)
        ]
        choices = ["90% - 100%", "75% - 89%", "60% - 74%"]
        df_temp["attendance_group"] = np.select(conditions, choices, default="Below 60%")
        
        grouped = df_temp.groupby("attendance_group")
        for group_name, group in grouped:
            att_vs_gpa.append({
                "attendance_group": group_name,
                "avg_gpa": round(float(group["current_gpa"].dropna().mean()), 2) if not group["current_gpa"].dropna().empty else 0.0,
                "student_count": int(group[student_id_col].nunique()) if student_id_col else len(group)
            })
        order = {"90% - 100%": 1, "75% - 89%": 2, "60% - 74%": 3, "Below 60%": 4}
        att_vs_gpa = sorted(att_vs_gpa, key=lambda x: order.get(x["attendance_group"], 5))
    analytics["attendance_vs_gpa"] = att_vs_gpa
    
    # 6. Performance trends
    trends = []
    if "performance_trend" in df.columns:
        grouped = df.groupby("performance_trend")
        for trend_name, group in grouped:
            trends.append({
                "performance_trend": trend_name,
                "count": int(group[student_id_col].nunique()) if student_id_col else len(group),
                "avg_gpa": round(float(group["current_gpa"].dropna().mean()), 2) if "current_gpa" in group.columns and not group["current_gpa"].dropna().empty else 0.0
            })
    analytics["trends"] = trends
    
    return analytics

def get_python_eda_data() -> dict:
    """Prepares numpy/pandas EDA distribution lists and dataset summaries."""
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
        if not cursor.fetchone():
            return {}
        df = pd.read_sql_query("SELECT * FROM raw_records", conn)
        
    if df.empty:
        return {}
        
    result = {"distributions": {}}
    
    # 1. Compute Histograms
    if "current_gpa" in df.columns:
        gpa_series = df["current_gpa"].dropna()
        if not gpa_series.empty:
            gpa_counts, gpa_bins = np.histogram(gpa_series, bins=10)
            result["distributions"]["gpa"] = {
                "counts": gpa_counts.tolist(), 
                "bins": [round(float(b), 2) for b in gpa_bins]
            }
            
    if "attendance" in df.columns:
        att_series = df["attendance"].dropna()
        if not att_series.empty:
            att_counts, att_bins = np.histogram(att_series, bins=10)
            result["distributions"]["attendance"] = {
                "counts": att_counts.tolist(), 
                "bins": [round(float(b), 2) for b in att_bins]
            }
            
    # 2. Department comparisons
    if "department" in df.columns:
        agg_dict = {}
        for col in ["current_gpa", "attendance", "study_hours", "lms_activity"]:
            if col in df.columns:
                agg_dict[col] = "mean"
        if agg_dict:
            dept_comparison = df.groupby("department").agg(agg_dict).round(2).reset_index()
            rename_map = {"attendance": "attendance_pct"}
            dept_comparison = dept_comparison.rename(columns=rename_map)
            result["department_analysis"] = dept_comparison.to_dict(orient="records")
            
    # 3. Scatter Plot points
    scatter_cols = ["student_id", "student_name", "department", "study_hours", "attendance", "current_gpa", "lms_activity"]
    active_scatter_cols = [c for c in scatter_cols if c in df.columns]
    if len(active_scatter_cols) >= 2:
        scatter_df = df[active_scatter_cols].dropna().copy()
        if "attendance" in scatter_df.columns:
            scatter_df = scatter_df.rename(columns={"attendance": "attendance_pct"})
        result["scatter_plots"] = scatter_df.to_dict(orient="records")
        
    # 4. Outlier detection
    if "current_gpa" in df.columns:
        gpa_series = df["current_gpa"].dropna()
        if len(gpa_series) >= 4:
            gpa_q1 = gpa_series.quantile(0.25)
            gpa_q3 = gpa_series.quantile(0.75)
            gpa_iqr = gpa_q3 - gpa_q1
            gpa_lower = gpa_q1 - 1.5 * gpa_iqr
            gpa_upper = gpa_q3 + 1.5 * gpa_iqr
            
            outliers_df = df[
                (df["current_gpa"] < gpa_lower) | 
                (df["current_gpa"] > gpa_upper)
            ].copy()
            
            outliers_cols = ["student_id", "student_name", "department", "current_gpa"]
            active_outliers_cols = [c for c in outliers_cols if c in outliers_df.columns]
            result["outliers"] = outliers_df[active_outliers_cols].to_dict(orient="records")
            
    return result

def run_statistical_analysis() -> dict:
    """Runs statistical hypotheses tests and correlation engines."""
    with DatabaseConnection() as conn:
        cursor = conn.conn.cursor() if hasattr(conn, 'conn') else conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
        if not cursor.fetchone():
            return {}
        df = pd.read_sql_query("SELECT * FROM raw_records", conn)
        
    if df.empty or "current_gpa" not in df.columns:
        return {}
        
    tests = [
        ("attendance", "Attendance vs GPA"),
        ("study_hours", "Study Hours vs GPA"),
        ("lms_activity", "LMS Activity vs GPA"),
        ("assignment_completion", "Assignment Completion vs GPA")
    ]
    
    correlations = []
    
    for col, label in tests:
        if col in df.columns:
            sub_df = df[[col, "current_gpa"]].dropna()
            if len(sub_df) >= 5:
                x = sub_df[col].values
                y = sub_df["current_gpa"].values
                
                if np.var(x) > 0 and np.var(y) > 0:
                    p_coef, p_val = stats.pearsonr(x, y)
                    s_coef, s_val = stats.spearmanr(x, y)
                    is_significant = p_val < 0.05
                    
                    hypothesis_summary = (
                        f"Null Hypothesis (H0): There is no correlation between {col.replace('_', ' ')} and student GPA.\n"
                        f"Alternative Hypothesis (Ha): There is a statistically significant correlation.\n"
                        f"Decision: {'Reject H0' if is_significant else 'Fail to Reject H0'} (p-value = {p_val:.2e})."
                    )
                    
                    interpretation = (
                        f"Strong positive linear correlation" if p_coef > 0.6 and is_significant else
                        f"Moderate positive correlation" if p_coef > 0.3 and is_significant else
                        f"Weak correlation" if is_significant else "No statistically significant correlation"
                    )
                    
                    correlations.append({
                        "variable": "attendance_pct" if col == "attendance" else col,
                        "label": label,
                        "pearson_coef": round(float(p_coef), 3),
                        "pearson_p_value": float(p_val),
                        "spearman_coef": round(float(s_coef), 3),
                        "spearman_p_value": float(s_val),
                        "significant": bool(is_significant),
                        "hypothesis_summary": hypothesis_summary,
                        "interpretation": interpretation
                    })
                    
    return {
        "correlations": correlations,
        "disclaimer": (
            "Disclaimer on Causation: The statistical correlations and association levels above "
            "do NOT prove that improving a single indicator (e.g. study hours or attendance) will "
            "directly cause an increase in grades. These variables are associated with success "
            "and are valuable predictive indicators, but they may be driven by confounding variables "
            "such as background knowledge, motivation, external support, or student wellbeing."
        )
    }

