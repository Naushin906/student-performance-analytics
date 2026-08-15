import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import logging
import subprocess
import sys

# Self-healing import check for XGBoost to prevent deadlocks and missing libomp library crashes on macOS
def _check_xgboost_availability():
    try:
        # Run import in a separate subprocess with a 1.5 second timeout
        res = subprocess.run(
            [sys.executable, "-c", "import xgboost"],
            capture_output=True,
            timeout=1.5
        )
        return res.returncode == 0
    except Exception:
        return False

_XGBOOST_AVAILABLE = _check_xgboost_availability()
if _XGBOOST_AVAILABLE:
    try:
        import xgboost as xgb
    except Exception:
        xgb = None
        _XGBOOST_AVAILABLE = False
else:
    xgb = None

logger = logging.getLogger("Models")
if not _XGBOOST_AVAILABLE:
    logger.warning("XGBoost is unavailable (likely missing libomp on macOS). System will fall back to Random Forest.")

from backend.database import DatabaseConnection
from backend.data_processor import get_capabilities

def segment_students() -> dict:
    """Performs K-Means clustering to segment students and returns profiling results."""
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
        if not cursor.fetchone():
            return {"error": "No records in database to run clustering."}
        df = pd.read_sql_query("SELECT * FROM raw_records", conn)
        
    if df.empty:
        return {"error": "Insufficient data to run clustering"}
        
    # Scale features for clustering (MinMax scaling)
    possible_feature_cols = ["current_gpa", "attendance", "study_hours", "assignment_completion", "quiz_score", "final_exam", "lms_activity"]
    feature_cols = [c for c in possible_feature_cols if c in df.columns]
    
    if len(feature_cols) < 2:
        return {"error": "Clustering requires at least 2 numeric data fields to be present in the dataset."}
        
    # Aggregate by student to avoid duplicate entries per student in clustering
    id_col = "student_id" if "student_id" in df.columns else ("student_name" if "student_name" in df.columns else None)
    if id_col:
        agg_dict = {col: "mean" for col in feature_cols}
        if "department" in df.columns:
            agg_dict["department"] = "first"
        if "student_name" in df.columns:
            agg_dict["student_name"] = "first"
        df_features = df.groupby(id_col).agg(agg_dict).reset_index()
    else:
        df_features = df.copy()
        df_features["student_id"] = [f"Student {i+1}" for i in range(len(df_features))]
        id_col = "student_id"
        
    X = df_features[feature_cols].copy()
    X = X.fillna(X.median())
    
    # Check if there are enough rows for clustering
    if len(df_features) < 3:
        return {"error": "Clustering requires at least 3 student records."}
        
    X_scaled = (X - X.min()) / (X.max() - X.min() + 1e-9)
    
    best_k = 3
    best_score = -1
    silhouette_scores = {}
    
    max_k = min(5, len(df_features) - 1)
    if max_k >= 2:
        for k in range(2, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels)
            silhouette_scores[k] = round(float(score), 3)
            if score > best_score:
                best_score = score
                best_k = k
                
    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    df_features["cluster"] = km_final.fit_predict(X_scaled)
    
    # Profile clusters based on available columns
    profile_agg = {col: "mean" for col in feature_cols}
    cluster_profiles = df_features.groupby("cluster").agg(profile_agg).reset_index()
    
    # Rank clusters based on GPA if present, else first feature
    rank_feature = "current_gpa" if "current_gpa" in feature_cols else feature_cols[0]
    cluster_profiles["rank_score"] = cluster_profiles[rank_feature]
    sorted_profiles = cluster_profiles.sort_values(by="rank_score", ascending=False).reset_index(drop=True)
    
    cluster_mapping = {}
    for rank_idx, cluster_id in enumerate(sorted_profiles["cluster"]):
        if rank_idx == 0:
            name = "High Performer"
        elif rank_idx == len(sorted_profiles) - 1:
            name = "At Risk"
        else:
            name = "Consistent Performer"
        cluster_mapping[int(cluster_id)] = name
        
    df_features["segment"] = df_features["cluster"].map(cluster_mapping)
    
    # Format properties for frontend
    if "attendance" in df_features.columns:
        df_features = df_features.rename(columns={"attendance": "attendance_pct"})
        
    students_list = df_features[[id_col, "segment"] + [c for c in ["current_gpa", "attendance_pct", "study_hours", "lms_activity"] if c in df_features.columns]].to_dict(orient="records")
    for r in students_list:
        if "student_name" in df_features.columns:
            name_val = df_features[df_features[id_col] == r[id_col]]["student_name"].iloc[0]
            r["student_name"] = str(name_val) if pd.notna(name_val) else str(r[id_col])
        else:
            r["student_name"] = str(r[id_col])
            
    # Segment profile averages
    current_features = [col if col != "attendance" else "attendance_pct" for col in feature_cols]
    seg_agg_dict = {col: "mean" for col in current_features if col in df_features.columns}
    seg_agg_dict[id_col] = "count"
    
    segment_summary_df = df_features.groupby("segment").agg(seg_agg_dict).round(2).rename(columns={id_col: "student_count"}).reset_index()
    segment_summary = segment_summary_df.to_dict(orient="records")
    
    return {
        "best_k": best_k,
        "silhouette_scores": silhouette_scores,
        "students": students_list,
        "segments": segment_summary
    }

def train_risk_prediction_models(risk_threshold: float = 0.5) -> dict:
    """Trains Logistic Regression, Random Forest, and XGBoost models dynamically for risk prediction."""
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
        if not cursor.fetchone():
            return {"error": "No records in database to train models."}
        df = pd.read_sql_query("SELECT * FROM raw_records", conn)
        
    if df.empty:
        return {"error": "Insufficient data to train machine learning models."}
        
    # Check if we have GPA or final exam scores to calculate target risk
    has_target_data = "current_gpa" in df.columns or "final_exam" in df.columns
    if not has_target_data:
        return {"error": "Machine learning risk prediction requires GPA or final exam score columns to calculate the target risk labels."}
        
    # Define features dynamically
    possible_features = ["attendance", "study_hours", "lms_activity", "assignment_completion", "quiz_score", "final_exam", "previous_gpa"]
    feature_cols = [c for c in possible_features if c in df.columns]
    
    if len(feature_cols) < 2:
        return {"error": "Machine learning modeling requires at least 2 feature columns (e.g. attendance, study hours, previous GPA, quiz score)."}
        
    # Aggregate per student
    id_col = "student_id" if "student_id" in df.columns else ("student_name" if "student_name" in df.columns else None)
    if id_col:
        agg_dict = {col: "mean" for col in feature_cols}
        if "current_gpa" in df.columns:
            agg_dict["current_gpa"] = "mean"
        if "final_exam" in df.columns:
            agg_dict["final_exam"] = "mean"
        df_ml = df.groupby(id_col).agg(agg_dict).reset_index()
    else:
        df_ml = df.copy()
        df_ml["student_id"] = [f"Student {i+1}" for i in range(len(df_ml))]
        id_col = "student_id"
        
    # Define Target Risk Label dynamically
    risk_conds = []
    if "current_gpa" in df_ml.columns:
        risk_conds.append(df_ml["current_gpa"] < 6.0)
    if "attendance" in df_ml.columns:
        risk_conds.append(df_ml["attendance"] < 70.0)
    if "final_exam" in df_ml.columns:
        risk_conds.append(df_ml["final_exam"] < 45.0)
        
    if not risk_conds:
        return {"error": "No target metrics available to calculate risk profile."}
        
    is_at_risk = risk_conds[0]
    for cond in risk_conds[1:]:
        is_at_risk = is_at_risk | cond
        
    df_ml["is_at_risk"] = np.where(is_at_risk, 1, 0)
    
    X = df_ml[feature_cols].fillna(df_ml[feature_cols].median())
    y = df_ml["is_at_risk"]
    
    if len(y.unique()) < 2:
        return {"error": "Cannot train models because the dataset does not contain both risk and non-risk examples under the current threshold."}
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    
    display_features = ["attendance_pct" if c == "attendance" else c for c in feature_cols]
    
    results = {}
    
    # 1. Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    lr_probs = lr.predict_proba(X_test)[:, 1]
    lr_preds = (lr_probs >= risk_threshold).astype(int)
    
    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_probs = rf.predict_proba(X_test)[:, 1]
    rf_preds = (rf_probs >= risk_threshold).astype(int)
    
    models = {
        "Logistic Regression": (lr, lr_probs, lr_preds),
        "Random Forest": (rf, rf_probs, rf_preds),
    }
    
    if _XGBOOST_AVAILABLE and xgb is not None:
        try:
            xgb_clf = xgb.XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42, use_label_encoder=False, eval_metric='logloss')
            xgb_clf.fit(X_train, y_train)
            xgb_probs = xgb_clf.predict_proba(X_test)[:, 1]
            xgb_preds = (xgb_probs >= risk_threshold).astype(int)
            models["XGBoost"] = (xgb_clf, xgb_probs, xgb_preds)
        except Exception as e:
            logger.error(f"XGBoost training failed: {e}")
            
    for name, (model, probs, preds) in models.items():
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        roc_auc = roc_auc_score(y_test, probs)
        cm = confusion_matrix(y_test, preds).tolist()
        
        fpr, tpr, _ = roc_curve(y_test, probs)
        roc_points = [{"fpr": round(float(f), 3), "tpr": round(float(t), 3)} for f, t in zip(fpr, tpr)]
        
        importances = []
        if name == "Logistic Regression":
            coefs = model.coef_[0]
            for col, val in zip(display_features, coefs):
                importances.append({"feature": col, "importance": round(float(val), 3)})
        else:
            imp = model.feature_importances_
            for col, val in zip(display_features, imp):
                importances.append({"feature": col, "importance": round(float(val), 3)})
                
        results[name] = {
            "metrics": {
                "accuracy": round(float(acc), 3),
                "precision": round(float(prec), 3),
                "rec_score": round(float(rec), 3),  # key map to frontend
                "recall": round(float(rec), 3),
                "f1_score": round(float(f1), 3),
                "roc_auc": round(float(roc_auc), 3)
            },
            "confusion_matrix": cm,
            "roc_curve": roc_points,
            "feature_importance": sorted(importances, key=lambda x: abs(x["importance"]), reverse=True)
        }
        
    return {
        "model_evaluation": results,
        "features": display_features,
        "total_records": len(df_ml),
        "training_size": len(X_train),
        "testing_size": len(X_test)
    }

def apply_selected_model_predictions(model_name: str, risk_threshold: float = 0.5) -> dict:
    """Applies the selected trained model to ALL students, updates tables, and generates interventions."""
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
        if not cursor.fetchone():
            return {"error": "No student records available"}
        df = pd.read_sql_query("SELECT * FROM raw_records", conn)
        
    if df.empty:
        return {"error": "No student records available"}
        
    # Define features dynamically
    possible_features = ["attendance", "study_hours", "lms_activity", "assignment_completion", "quiz_score", "final_exam", "previous_gpa"]
    feature_cols = [c for c in possible_features if c in df.columns]
    
    if len(feature_cols) < 2:
        return {"error": "Insufficient features to apply model predictions."}
        
    # Aggregate per student
    id_col = "student_id" if "student_id" in df.columns else ("student_name" if "student_name" in df.columns else None)
    if id_col:
        agg_dict = {col: "mean" for col in feature_cols}
        for opt in ["current_gpa", "final_exam", "previous_gpa", "attendance"]:
            if opt in df.columns:
                agg_dict[opt] = "mean"
        if "student_name" in df.columns:
            agg_dict["student_name"] = "first"
        if "department" in df.columns:
            agg_dict["department"] = "first"
        if "semester" in df.columns:
            agg_dict["semester"] = "first"
        if "performance_change" in df.columns:
            agg_dict["performance_change"] = "mean"
        if "performance_trend" in df.columns:
            agg_dict["performance_trend"] = lambda x: x.value_counts().index[0] if len(x) > 0 else "STABLE"
            
        df_ml = df.groupby(id_col).agg(agg_dict).reset_index()
    else:
        df_ml = df.copy()
        df_ml["student_id"] = [f"Student {i+1}" for i in range(len(df_ml))]
        id_col = "student_id"
        
    # Define Target Risk Label dynamically
    risk_conds = []
    if "current_gpa" in df_ml.columns:
        risk_conds.append(df_ml["current_gpa"] < 6.0)
    if "attendance" in df_ml.columns:
        risk_conds.append(df_ml["attendance"] < 70.0)
    if "final_exam" in df_ml.columns:
        risk_conds.append(df_ml["final_exam"] < 45.0)
        
    is_at_risk = risk_conds[0]
    for cond in risk_conds[1:]:
        is_at_risk = is_at_risk | cond
        
    df_ml["is_at_risk"] = np.where(is_at_risk, 1, 0)
    
    X = df_ml[feature_cols].fillna(df_ml[feature_cols].median())
    y = df_ml["is_at_risk"]
    
    if model_name == "Logistic Regression":
        model = LogisticRegression(max_iter=1000, random_state=42)
    elif model_name == "XGBoost" and (_XGBOOST_AVAILABLE and xgb is not None):
        model = xgb.XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42, use_label_encoder=False, eval_metric='logloss')
    else:
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        
    model.fit(X, y)
    probs = model.predict_proba(X)[:, 1]
    
    predictions_count = 0
    interventions_count = 0
    
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        
        # Clear predictions and interventions tables to rebuild
        cursor.execute("DELETE FROM risk_predictions")
        cursor.execute("DELETE FROM interventions")
        
        for idx, row in df_ml.iterrows():
            st_id = row[id_col]
            prob = float(probs[idx])
            
            if prob >= 0.70:
                lvl = "HIGH"
            elif prob >= 0.40:
                lvl = "MEDIUM"
            else:
                lvl = "LOW"
                
            cursor.execute(
                """
                INSERT INTO risk_predictions (student_id, risk_probability, risk_level)
                VALUES (?, ?, ?)
                """,
                (str(st_id), round(prob * 100, 2), lvl)
            )
            predictions_count += 1
            
            # Intervention generator
            recs = []
            if "attendance" in row and row["attendance"] < 65.0:
                recs.append(("Attendance Support", f"Critical: Attendance is low at {row['attendance']:.1f}%. Recommend academic counseling."))
            elif "attendance" in row and row["attendance"] < 75.0:
                recs.append(("Attendance Warning", f"Warning: Attendance is at {row['attendance']:.1f}%. Remind student of attendance limits."))
                
            if "assignment_completion" in row and row["assignment_completion"] < 50.0:
                recs.append(("Assignment Assistance", f"Critical: Assignment completion is only {row['assignment_completion']:.1f}%. Peer tutoring recommended."))
                
            if "final_exam" in row and row["final_exam"] < 40.0:
                recs.append(("Exam Remediation", f"Exam alert: Student exam average is low ({row['final_exam']:.1f}%). Remediation program suggested."))
                
            if "performance_trend" in row and row["performance_trend"] == "DECLINING":
                recs.append(("Mentorship Program", f"Declining trend: Performance has declined. Recommend placement in faculty mentorship."))
                
            if lvl == "HIGH" and len(recs) >= 2:
                recs.append(("Personalized Intervention", "High-Risk Profile: Multiple negative indicators. Urgent counselor meeting recommended."))
                
            if lvl == "LOW" and not recs:
                recs.append(("Academic Enrichment", "Excellent: Stable performance. Recommend for honors track or peer tutoring role."))
                
            for category, text in recs:
                cursor.execute(
                    """
                    INSERT INTO interventions (student_id, category, recommendation_text, status)
                    VALUES (?, ?, ?, 'PENDING')
                    """,
                    (str(st_id), category, text)
                )
                interventions_count += 1
                
    return {
        "predictions_applied": predictions_count,
        "interventions_created": interventions_count
    }
