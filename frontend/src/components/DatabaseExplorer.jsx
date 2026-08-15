import React, { useState, useEffect } from 'react';

function DatabaseExplorer({ dbStatus, checkDbStatus }) {
  const [activeSchema, setActiveSchema] = useState([]);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [customSql, setCustomSql] = useState('SELECT * FROM raw_records LIMIT 5;');
  const [queryResult, setQueryResult] = useState(null);
  const [runningQuery, setRunningQuery] = useState(false);
  const [queryError, setQueryError] = useState('');

  const prewrittenQueries = [
    {
      name: "Select Raw Loaded Records (raw_records)",
      sql: `SELECT * FROM raw_records LIMIT 10;`
    },
    {
      name: "Top 10 Performing Students (DENSE_RANK Window)",
      sql: `WITH StudentGPAs AS (
  SELECT 
    s.student_id,
    s.student_name,
    s.department,
    ROUND(AVG(sp.current_gpa), 2) as avg_gpa,
    ROUND(AVG(a.attendance_pct), 1) as avg_attendance
  FROM students s
  JOIN student_performance sp ON s.student_id = sp.student_id
  JOIN attendance a ON s.student_id = a.student_id AND sp.subject_id = a.subject_id
  GROUP BY s.student_id, s.student_name, s.department
)
SELECT 
  student_id,
  student_name,
  department,
  avg_gpa,
  avg_attendance,
  DENSE_RANK() OVER (ORDER BY avg_gpa DESC) as gpa_rank
FROM StudentGPAs
LIMIT 10;`
    },
    {
      name: "Department Ranking & Student Metrics (RANK Window)",
      sql: `WITH DeptStats AS (
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
  ROUND(avg_gpa, 2) as department_gpa,
  ROUND(avg_attendance, 1) as department_attendance_pct,
  student_count,
  RANK() OVER (ORDER BY avg_gpa DESC) as dept_rank
FROM DeptStats;`
    },
    {
      name: "Course Pass & Fail Rates (Aggregate CASE CTE)",
      sql: `WITH CourseStats AS (
  SELECT 
    s.subject_id,
    s.subject_name,
    s.department,
    COUNT(p.student_id) as total_students,
    SUM(CASE WHEN p.performance_index >= 50.0 THEN 1 ELSE 0 END) as passed_count
  FROM subjects s
  JOIN student_performance p ON s.subject_id = p.subject_id
  GROUP BY s.subject_id, s.subject_name, s.department
)
SELECT 
  subject_name,
  department,
  total_students,
  ROUND((CAST(passed_count AS REAL) / total_students) * 100, 1) as pass_rate_pct,
  ROUND((1.0 - CAST(passed_count AS REAL) / total_students) * 100, 1) as fail_rate_pct
FROM CourseStats
ORDER BY pass_rate_pct ASC;`
    },
    {
      name: "Attendance Bands vs Average GPA (Group By Range)",
      sql: `SELECT 
  CASE 
    WHEN a.attendance_pct >= 90 THEN '90% - 100% (Excellent)'
    WHEN a.attendance_pct >= 75 THEN '75% - 89% (Good/Required)'
    WHEN a.attendance_pct >= 60 THEN '60% - 74% (Shortage/Warning)'
    ELSE 'Below 60% (Critical Risk)'
  END as attendance_band,
  ROUND(AVG(sp.current_gpa), 2) as avg_gpa,
  COUNT(DISTINCT s.student_id) as student_count
FROM students s
JOIN student_performance sp ON s.student_id = sp.student_id
JOIN attendance a ON s.student_id = a.student_id AND sp.subject_id = a.subject_id
GROUP BY attendance_band
ORDER BY avg_gpa DESC;`
    }
  ];

  const fetchSchemaInfo = async () => {
    if (dbStatus.status !== 'ONLINE') return;
    setLoadingSchema(true);
    try {
      const res = await fetch('/api/sql-analytics');
      if (res.ok) {
        const data = await res.json();
        const counts = [
          { name: "raw_records", description: "Flat table holding all dynamically cleaned spreadsheet columns.", count: dbStatus.student_count },
          { name: "students", description: "Relational: core profiles (only populated if standard keys present).", count: data.summary ? dbStatus.student_count : 0 },
          { name: "subjects", description: "Relational: subjects mapped by department.", count: data.subjects?.length || 0 },
          { name: "attendance", description: "Relational: attendance records mapped per student.", count: data.subjects ? data.subjects.reduce((acc, s) => acc + s.total_students, 0) : 0 },
          { name: "assessments", description: "Relational: raw assessment marks.", count: data.subjects ? data.subjects.reduce((acc, s) => acc + s.total_students, 0) : 0 },
          { name: "student_performance", description: "Relational: GPA and trend metrics.", count: data.subjects ? data.subjects.reduce((acc, s) => acc + s.total_students, 0) : 0 }
        ];
        setActiveSchema(counts);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSchema(false);
    }
  };

  useEffect(() => {
    fetchSchemaInfo();
  }, [dbStatus]);

  const handleRunQuery = async (queryToRun) => {
    setRunningQuery(true);
    setQueryError('');
    setQueryResult(null);
    try {
      const res = await fetch('/api/custom-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryToRun || customSql }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'SQL Query failed');
      }

      const data = await res.json();
      setQueryResult(data.data);
    } catch (e) {
      setQueryError(e.message);
    } finally {
      setRunningQuery(false);
    }
  };

  const selectPrewritten = (sql) => {
    setCustomSql(sql);
    handleRunQuery(sql);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Relational Database Engine</h1>
        <p className="page-subtitle">Inspect relational tables, counts, and execute advanced analytical SQL queries.</p>
      </div>

      <div className="grid-2">
        {/* Left Side: Table Schemas and Counts */}
        <div className="card">
          <h3>Relational Schema Catalog</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            The relational structure enforces Primary Keys, Foreign Keys, indexes, and range checks.
          </p>

          {loadingSchema ? (
            <p style={{ color: 'var(--text-muted)' }}>Retrieving schema statistics...</p>
          ) : activeSchema.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {activeSchema.map(tbl => (
                <div key={tbl.name} style={{ display: 'flex', flexDirection: 'column', padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{tbl.name}</strong>
                    <span className="badge badge-info">{tbl.count} Records</span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>{tbl.description}</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)' }}>Database is empty. Please upload and clean a dataset.</p>
          )}
        </div>

        {/* Right Side: Pre-written SQL Analytics Queries */}
        <div className="card">
          <h3>Pre-written SQL Analytics Panels</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Click any query to populate the SQL editor and execute it immediately against the database.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {prewrittenQueries.map((q, idx) => (
              <button 
                key={idx} 
                className="btn btn-secondary" 
                style={{ textAlign: 'left', justifyContent: 'flex-start', fontSize: '0.85rem', padding: '0.5rem 1rem' }}
                onClick={() => selectPrewritten(q.sql)}
              >
                <span>🔍 {q.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* SQL Editor and Runner Console */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3>SQL Query Console</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
          Run standard SELECT queries. Modifying operations (INSERT, UPDATE, DELETE, DROP) are blocked for safety.
        </p>

        <div className="sql-console">
          <textarea 
            className="sql-editor" 
            value={customSql} 
            onChange={(e) => setCustomSql(e.target.value)}
          />
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary" onClick={() => setCustomSql('')}>Clear</button>
            <button className="btn btn-primary" onClick={() => handleRunQuery()} disabled={runningQuery}>
              {runningQuery ? 'Running Query...' : 'Run Query'}
            </button>
          </div>
        </div>

        {queryError && (
          <div style={{ borderLeft: '4px solid var(--accent-danger)', color: 'var(--accent-danger)', backgroundColor: 'rgba(235, 87, 87, 0.05)', padding: '0.75rem 1rem', borderRadius: '4px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', marginBottom: '1rem' }}>
            Error: {queryError}
          </div>
        )}

        {queryResult && (
          <div>
            <h4 style={{ marginBottom: '0.5rem' }}>Query Result ({queryResult.length} Rows)</h4>
            <div className="table-container" style={{ maxHeight: '350px' }}>
              <table>
                <thead>
                  <tr>
                    {queryResult.length > 0 && Object.keys(queryResult[0]).map(key => (
                      <th key={key} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {queryResult.map((row, idx) => (
                    <tr key={idx}>
                      {Object.values(row).map((val, cellIdx) => (
                        <td key={cellIdx}>{val === null ? 'NULL' : String(val)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DatabaseExplorer;
