import os
import sqlite3
import logging

# Try to import PostgreSQL drivers
try:
    import psycopg2
    from psycopg2 import pool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Database")

# Configuration from environment or defaults
DB_URL = os.environ.get("DATABASE_URL", None)
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "student_analytics.db")

pg_pool = None
use_sqlite = True
active_db_type = "SQLite"

def init_db_connection():
    global pg_pool, use_sqlite, active_db_type
    
    if DB_URL and HAS_POSTGRES:
        try:
            logger.info("Attempting to connect to PostgreSQL...")
            pg_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DB_URL)
            # Test a connection
            conn = pg_pool.getconn()
            pg_pool.putconn(conn)
            use_sqlite = False
            active_db_type = "PostgreSQL"
            logger.info("Successfully connected to PostgreSQL! Using PostgreSQL database.")
            return
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}. Falling back to SQLite.")
    
    logger.info(f"Using SQLite database at {SQLITE_PATH}")
    use_sqlite = True
    active_db_type = "SQLite"

# Initialize connection configurations
init_db_connection()

class DatabaseConnection:
    """Context manager for SQLite or PostgreSQL connections."""
    def __init__(self):
        self.conn = None
        self.db_type = active_db_type

    def __enter__(self):
        if use_sqlite:
            self.conn = sqlite3.connect(SQLITE_PATH)
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self.conn.row_factory = sqlite3.Row
        else:
            self.conn = pg_pool.getconn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
                
            if use_sqlite:
                self.conn.close()
            else:
                pg_pool.putconn(self.conn)

def initialize_schema():
    """Creates tables, indices, and constraints in the database."""
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        
        # SQL Scripts
        # SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT
        # PostgreSQL uses SERIAL PRIMARY KEY or IDENTITY
        id_type = "SERIAL PRIMARY KEY"
        numeric_type = "NUMERIC"
        text_type = "TEXT"
        
        if use_sqlite:
            id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
            numeric_type = "REAL"
            text_type = "TEXT"
        
        queries = [
            # Drop tables if they exist (for complete seeding reset if necessary)
            # Create students table
            f"""
            CREATE TABLE IF NOT EXISTS students (
                student_id VARCHAR(50) PRIMARY KEY,
                student_name VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL,
                semester INT NOT NULL,
                academic_year VARCHAR(20) NOT NULL,
                previous_gpa {numeric_type} CHECK (previous_gpa >= 0.0 AND previous_gpa <= 10.0)
            )
            """,
            # Create subjects table
            """
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id VARCHAR(50) PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL
            )
            """,
            # Create learning behavior table
            f"""
            CREATE TABLE IF NOT EXISTS learning_behavior (
                student_id VARCHAR(50) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
                study_hours {numeric_type},
                lms_activity INT
            )
            """,
            # Create attendance table
            f"""
            CREATE TABLE IF NOT EXISTS attendance (
                student_id VARCHAR(50) REFERENCES students(student_id) ON DELETE CASCADE,
                subject_id VARCHAR(50) REFERENCES subjects(subject_id) ON DELETE CASCADE,
                attendance_pct {numeric_type} CHECK (attendance_pct >= 0.0 AND attendance_pct <= 100.0),
                PRIMARY KEY (student_id, subject_id)
            )
            """,
            # Create assessments table
            f"""
            CREATE TABLE IF NOT EXISTS assessments (
                student_id VARCHAR(50) REFERENCES students(student_id) ON DELETE CASCADE,
                subject_id VARCHAR(50) REFERENCES subjects(subject_id) ON DELETE CASCADE,
                internal_1 {numeric_type},
                internal_2 {numeric_type},
                assignment_score {numeric_type},
                quiz_score {numeric_type},
                final_exam {numeric_type},
                assignment_completion {numeric_type},
                PRIMARY KEY (student_id, subject_id)
            )
            """,
            # Create performance table
            f"""
            CREATE TABLE IF NOT EXISTS student_performance (
                student_id VARCHAR(50) REFERENCES students(student_id) ON DELETE CASCADE,
                subject_id VARCHAR(50) REFERENCES subjects(subject_id) ON DELETE CASCADE,
                performance_index {numeric_type},
                current_gpa {numeric_type},
                performance_change {numeric_type},
                performance_trend VARCHAR(20),
                PRIMARY KEY (student_id, subject_id)
            )
            """,
            # Create risk predictions table
            f"""
            CREATE TABLE IF NOT EXISTS risk_predictions (
                student_id VARCHAR(50) PRIMARY KEY REFERENCES students(student_id) ON DELETE CASCADE,
                risk_probability {numeric_type},
                risk_level VARCHAR(20)
            )
            """,
            # Create interventions table
            f"""
            CREATE TABLE IF NOT EXISTS interventions (
                id {id_type},
                student_id VARCHAR(50) REFERENCES students(student_id) ON DELETE CASCADE,
                category VARCHAR(50),
                recommendation_text {text_type},
                status VARCHAR(20) DEFAULT 'PENDING'
            )
            """
        ]
        
        for q in queries:
            cursor.execute(q)
            
        # Create Indexes for fast querying
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);",
            "CREATE INDEX IF NOT EXISTS idx_students_sem ON students(semester);",
            "CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_assessments_student ON assessments(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_performance_student ON student_performance(student_id);",
            "CREATE INDEX IF NOT EXISTS idx_performance_subject ON student_performance(subject_id);"
        ]
        
        for idx_q in index_queries:
            try:
                cursor.execute(idx_q)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")
                
    logger.info("Database schema initialized successfully.")

def get_db_info():
    """Returns database type and storage details."""
    return {
        "db_type": active_db_type,
        "sqlite_path": SQLITE_PATH if use_sqlite else None,
        "postgresql_configured": DB_URL is not None,
        "has_postgres_driver": HAS_POSTGRES
    }

if __name__ == "__main__":
    initialize_schema()
