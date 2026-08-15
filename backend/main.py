import os
import shutil
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Main")

# Import custom backend modules
from backend.database import initialize_schema, get_db_info, DatabaseConnection
from backend.data_processor import (
    detect_file_and_sheets,
    load_data_preview,
    analyze_data_quality,
    clean_and_normalize_data,
    load_to_database
)
from backend.analytics import (
    get_sql_analytics,
    get_python_eda_data,
    run_statistical_analysis,
    execute_custom_query
)
from backend.models import (
    segment_students,
    train_risk_prediction_models,
    apply_selected_model_predictions
)

app = FastAPI(title="Smart Education Analytics Backend")

# Setup CORS middleware for frontend-backend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ensure database tables are created at startup
@app.on_event("startup")
def startup_db_init():
    try:
        initialize_schema()
        logger.info("Startup schema initialization completed.")
    except Exception as e:
        logger.error(f"Database schema initialization failed at startup: {e}")

@app.get("/api/db-status")
def db_status():
    """Checks the operational status of the PostgreSQL / SQLite database and returns data capabilities."""
    import pandas as pd
    from backend.data_processor import get_capabilities
    from backend.database import use_sqlite
    try:
        info = get_db_info()
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            
            if use_sqlite:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
                table_exists = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'raw_records')")
                table_exists = cursor.fetchone()[0]
                
            if table_exists:
                df = pd.read_sql("SELECT * FROM raw_records", conn)
                st_count = len(df)
                capabilities = get_capabilities(df)
            else:
                st_count = 0
                capabilities = {}
                
        info["student_count"] = st_count
        info["status"] = "ONLINE"
        info["capabilities"] = capabilities
        return info
    except Exception as e:
        return {"status": "OFFLINE", "error": str(e)}

@app.post("/api/upload")
def upload_file(file: UploadFile = File(...)):
    """Uploads a dataset file (CSV/Excel) and reads its structure/preview."""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".csv", ".xls", ".xlsx"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV and Excel sheets are supported.")
        
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_meta = detect_file_and_sheets(temp_path)
        
        # Load a default preview of first sheet or file
        sheet_name = file_meta["sheets"][0] if file_meta["sheets"] else None
        preview_meta = load_data_preview(temp_path, sheet_name=sheet_name)
        
        return {
            "success": True,
            "filename": file.filename,
            "file_path": temp_path,
            "file_type": file_meta["file_type"],
            "sheets": file_meta["sheets"],
            **preview_meta
        }
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SheetPreviewRequest(BaseModel):
    file_path: str
    sheet_name: str

@app.post("/api/preview-sheet")
def preview_sheet(req: SheetPreviewRequest):
    """Retrieves column preview for a specific sheet of an uploaded Excel file."""
    try:
        preview_meta = load_data_preview(req.file_path, sheet_name=req.sheet_name)
        return {
            "success": True,
            **preview_meta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QualityAnalysisRequest(BaseModel):
    file_path: str
    sheet_name: Optional[str] = None
    mapping: Dict[str, str]

@app.post("/api/analyze-quality")
def analyze_quality(req: QualityAnalysisRequest):
    """Performs validation checks and generates a data quality report."""
    try:
        report = analyze_data_quality(req.file_path, sheet_name=req.sheet_name, mapping=req.mapping)
        return report
    except ValueError as e:
        logger.error(f"Data quality validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Data quality error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class CleanAndLoadRequest(BaseModel):
    file_path: str
    sheet_name: Optional[str] = None
    mapping: Dict[str, str]
    weights: Optional[Dict[str, float]] = None

@app.post("/api/clean-and-load")
def clean_and_load(req: CleanAndLoadRequest):
    """Cleans raw file data, maps columns, and saves to relational tables."""
    try:
        # 1. Initialize DB Schema to clear out old tables or ensure they exist
        initialize_schema()
        
        # 2. Run Cleaning Pipeline
        clean_df, clean_stats = clean_and_normalize_data(
            req.file_path, 
            sheet_name=req.sheet_name, 
            mapping=req.mapping,
            weights=req.weights
        )
        
        # 3. Load into relational tables
        db_stats = load_to_database(clean_df)
        
        return {
            "success": True,
            "cleaning_statistics": clean_stats,
            "records_loaded": db_stats
        }
    except ValueError as e:
        logger.error(f"Clean & Load validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Clean & Load error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sql-analytics")
def sql_analytics(passing_threshold: float = 40.0):
    """Runs SQL queries (CTEs, windows, rankings) on performance data."""
    try:
        return get_sql_analytics(passing_threshold=passing_threshold)
    except Exception as e:
        logger.error(f"SQL analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class CustomQueryRequest(BaseModel):
    query: str

@app.post("/api/custom-query")
def run_custom_query(req: CustomQueryRequest):
    """Executes a custom SQL query in a read-only context."""
    try:
        rows = execute_custom_query(req.query)
        return {"success": True, "data": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/python-eda")
def python_eda():
    """Returns distributions, outliers, and scatter coordinates for plots."""
    try:
        return get_python_eda_data()
    except Exception as e:
        logger.error(f"Python EDA error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statistics")
def statistics():
    """Calculates statistical correlations, hypothesis tests, and warnings."""
    try:
        return run_statistical_analysis()
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/segmentation")
def segmentation():
    """Segments students using K-Means clustering and profiles results."""
    try:
        return segment_students()
    except Exception as e:
        logger.error(f"Segmentation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ModelTrainRequest(BaseModel):
    risk_threshold: float

@app.post("/api/train-models")
def train_models(req: ModelTrainRequest):
    """Trains and compares Logistic Regression, Random Forest, and XGBoost."""
    try:
        results = train_risk_prediction_models(risk_threshold=req.risk_threshold / 100.0)
        return results
    except Exception as e:
        logger.error(f"Model training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ApplyPredictionsRequest(BaseModel):
    model_name: str
    risk_threshold: float

@app.post("/api/apply-predictions")
def apply_predictions(req: ApplyPredictionsRequest):
    """Writes selected model risk values to database and triggers recommendations."""
    try:
        res = apply_selected_model_predictions(req.model_name, risk_threshold=req.risk_threshold / 100.0)
        return res
    except Exception as e:
        logger.error(f"Apply predictions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/early-warning")
def early_warning():
    """Retrieves high risk students, details, and interventions dynamically from database/raw_records."""
    import pandas as pd
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            
            # Fetch raw risk predictions
            cursor.execute("SELECT student_id, risk_probability, risk_level FROM risk_predictions ORDER BY risk_probability DESC")
            pred_cols = [desc[0] for desc in cursor.description]
            risk_list = [dict(zip(pred_cols, r)) for r in cursor.fetchall()]
            
            # Check if raw_records exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_records'")
            raw_records_exists = cursor.fetchone() is not None
            
            student_indicators = {}
            if raw_records_exists:
                df = pd.read_sql_query("SELECT * FROM raw_records", conn)
                id_col = "student_id" if "student_id" in df.columns else ("student_name" if "student_name" in df.columns else None)
                
                # Resolve names and details for risk list
                for item in risk_list:
                    st_id = item["student_id"]
                    if id_col:
                        matches = df[df[id_col].astype(str) == str(st_id)]
                        if not matches.empty:
                            item["student_name"] = str(matches["student_name"].iloc[0]) if "student_name" in df.columns else str(st_id)
                            item["department"] = str(matches["department"].iloc[0]) if "department" in df.columns else "All"
                            item["semester"] = int(matches["semester"].iloc[0]) if "semester" in df.columns else 1
                        else:
                            item["student_name"] = str(st_id)
                            item["department"] = "All"
                            item["semester"] = 1
                    else:
                        item["student_name"] = str(st_id)
                        item["department"] = "All"
                        item["semester"] = 1
                        
                # Compute indicators per student
                if id_col:
                    for st_id in df[id_col].unique():
                        matches = df[df[id_col] == st_id]
                        if not matches.empty:
                            int_1_val = matches["internal_1"].mean() if "internal_1" in df.columns else 0.0
                            int_2_val = matches["internal_2"].mean() if "internal_2" in df.columns else 0.0
                            student_indicators[str(st_id)] = {
                                "student_id": str(st_id),
                                "attendance_avg": round(float(matches["attendance"].mean()), 1) if "attendance" in df.columns else 0.0,
                                "internals_avg": round(float((int_1_val + int_2_val) / 2.0), 1) if ("internal_1" in df.columns or "internal_2" in df.columns) else 0.0,
                                "assign_completion": round(float(matches["assignment_completion"].mean()), 1) if "assignment_completion" in df.columns else 0.0,
                                "study_hours": round(float(matches["study_hours"].mean()), 1) if "study_hours" in df.columns else 0.0,
                                "previous_gpa": round(float(matches["previous_gpa"].mean()), 1) if "previous_gpa" in df.columns else 0.0
                            }
            else:
                for item in risk_list:
                    item["student_name"] = item["student_id"]
                    item["department"] = "All"
                    item["semester"] = 1
                    
            # Fetch interventions
            cursor.execute("SELECT id, student_id, category, recommendation_text, status FROM interventions")
            int_cols = [desc[0] for desc in cursor.description]
            interventions_list = [dict(zip(int_cols, r)) for r in cursor.fetchall()]
            
        return {
            "risk_list": risk_list,
            "student_indicators": student_indicators,
            "interventions": interventions_list
        }
    except Exception as e:
        logger.error(f"Early warning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class UpdateInterventionRequest(BaseModel):
    id: int
    status: str

@app.post("/api/update-intervention")
def update_intervention(req: UpdateInterventionRequest):
    """Updates the action status (PENDING / COMPLETED / REJECTED) of an intervention."""
    try:
        with DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE interventions SET status = ? WHERE id = ?",
                (req.status, req.id)
            )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
