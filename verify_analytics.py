import os
import json
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(__file__))

print("=== STARTING BACKEND PIPELINE VERIFICATION ===")

try:
    # 1. Test Database configuration
    print("\n[1/7] Testing database configuration and fallback...")
    from backend.database import get_db_info, initialize_schema, DatabaseConnection
    db_info = get_db_info()
    print(f"→ Database type active: {db_info['db_type']}")
    print(f"→ SQLite fallback path: {db_info['sqlite_path']}")
    
    # 2. Re-initialize database schema
    print("\n[2/7] Initializing database tables and indexes...")
    initialize_schema()
    print("→ Schema initialized successfully.")
    
    # 3. Analyze data quality of sample CSV
    print("\n[3/7] Running Data Quality analysis on mock dataset...")
    from backend.data_processor import load_data_preview, analyze_data_quality, clean_and_normalize_data, load_to_database
    csv_path = "data/sample_students.csv"
    
    preview = load_data_preview(csv_path)
    mapping = preview["auto_mapping"]
    print(f"→ Mapped columns: {list(mapping.keys())}")
    
    quality_report = analyze_data_quality(csv_path, mapping=mapping)
    print(f"→ Health Status: {quality_report['statuses']['overall']}")
    print(f"→ Rows: {quality_report['total_rows']}, Cols: {quality_report['total_columns']}")
    print(f"→ Duplicates: {quality_report['duplicates']}, Missing count: {quality_report['missing_count']}")
    
    # 4. Run data cleaning and database relational load
    print("\n[4/7] Cleaning records and inserting to database...")
    clean_df, clean_stats = clean_and_normalize_data(csv_path, mapping=mapping)
    print(f"→ Cleaning completed: {clean_stats}")
    
    db_stats = load_to_database(clean_df)
    print(f"→ Database load completed: {db_stats}")
    
    # 5. Run SQL analytics & Custom query tests
    print("\n[5/7] Running advanced SQL CTE & Window analytics...")
    from backend.analytics import get_sql_analytics, get_python_eda_data, run_statistical_analysis
    sql_res = get_sql_analytics()
    print(f"→ Average GPA: {sql_res['summary']['avg_gpa']}")
    print(f"→ Average Attendance: {sql_res['summary']['avg_attendance']}%")
    print(f"→ Top Student: {sql_res['top_students'][0]['student_name']} (GPA {sql_res['top_students'][0]['gpa']})")
    
    # Test python EDA and statistics
    eda_data = get_python_eda_data()
    print(f"→ Number of academic outliers detected: {len(eda_data['outliers'])}")
    
    stats_data = run_statistical_analysis()
    for corr in stats_data["correlations"]:
        print(f"  • {corr['label']}: Pearson r={corr['pearson_coef']} (p={corr['pearson_p_value']:.2e}), Sig: {corr['significant']}")
        
    # 6. Run Student K-Means segmentation
    print("\n[6/7] Running student K-Means segmentation...")
    from backend.models import segment_students, train_risk_prediction_models, apply_selected_model_predictions
    seg_res = segment_students()
    print(f"→ Optimal cluster count K: {seg_res['best_k']}")
    for s in seg_res["segments"]:
        print(f"  • Segment '{s['segment']}': Count={s['student_count']}, Avg GPA={s['current_gpa']}")
        
    # 7. Run Machine Learning models and apply predictions
    print("\n[7/7] Training ML classifiers (Logistic Regression, Random Forest, XGBoost)...")
    ml_res = train_risk_prediction_models(risk_threshold=0.50)
    for model_name, eval_data in ml_res["model_evaluation"].items():
        metrics = eval_data["metrics"]
        print(f"  • {model_name} -> Acc: {metrics['accuracy']:.3f}, F1: {metrics['f1_score']:.3f}, AUC: {metrics['roc_auc']:.3f}")
        
    print("\n→ Applying Random Forest model predictions and generating interventions...")
    apply_res = apply_selected_model_predictions("Random Forest", risk_threshold=0.50)
    print(f"→ Saved {apply_res['predictions_applied']} predictions and {apply_res['interventions_created']} intervention warnings.")
    
    print("\n=== PIPELINE VERIFICATION SUCCESSFUL! ===")
    
except Exception as e:
    print(f"\n❌ PIPELINE VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
