import React, { useState, useEffect } from 'react';

function DataCleaning({ uploadedFile, mapping, sheetName, weights, setWeights, cleaningResult, setCleaningResult, setDataCleaned, dataCleaned, passingThreshold, setPassingThreshold }) {
  const [qualityReport, setQualityReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [cleaningInProgress, setCleaningInProgress] = useState(false);
  const [error, setError] = useState('');

  const allPotentialFields = [
    { key: "student_id", label: "Student ID" },
    { key: "student_name", label: "Student Name" },
    { key: "department", label: "Department" },
    { key: "semester", label: "Semester" },
    { key: "academic_year", label: "Academic Year" },
    { key: "subject", label: "Course / Subject" },
    { key: "attendance", label: "Attendance %" },
    { key: "internal_1", label: "Internal Assessment 1 Marks" },
    { key: "internal_2", label: "Internal Assessment 2 Marks" },
    { key: "assignment_score", label: "Assignment Score" },
    { key: "quiz_score", label: "Quiz Score" },
    { key: "final_exam", label: "Final Exam Score" },
    { key: "previous_gpa", label: "Previous GPA" },
    { key: "study_hours", label: "Study Hours per Week" },
    { key: "lms_activity", label: "LMS Activity logs count" },
    { key: "assignment_completion", label: "Assignment Completion %" }
  ];

  const mappedKeys = Object.keys(mapping).filter(k => mapping[k] && String(mapping[k]).trim() !== "");
  const isMappingValid = mappedKeys.length >= 1;
  const missingFields = allPotentialFields.filter(f => !mapping[f.key]);

  const numericColsCount = uploadedFile.columns ? uploadedFile.columns.filter(col => {
    const t = uploadedFile.types && uploadedFile.types[col];
    return t && (t.includes('int') || t.includes('float') || t.includes('double') || t.includes('num') || t.includes('real'));
  }).length : 0;

  const mappedCount = mappedKeys.length;
  
  const hasStudent = mappedKeys.includes('student_name') || mappedKeys.includes('student_id');
  const hasSubject = mappedKeys.includes('subject') || numericColsCount > mappedCount;
  const hasMarks = mappedKeys.includes('final_exam') || mappedKeys.includes('internal_1') || numericColsCount > mappedCount;
  const hasAttendance = mappedKeys.includes('attendance');
  const hasGPA = mappedKeys.includes('current_gpa') || mappedKeys.includes('previous_gpa') || hasMarks;
  const hasDept = mappedKeys.includes('department');
  const hasSemester = mappedKeys.includes('semester');
  const hasLearningBehavior = mappedKeys.includes('study_hours') || mappedKeys.includes('lms_activity');

  const fetchQualityReport = async () => {
    if (!isMappingValid) {
      setQualityReport(null);
      setError('');
      return;
    }
    setLoadingReport(true);
    setError('');
    try {
      const res = await fetch('/api/analyze-quality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: uploadedFile.file_path,
          sheet_name: sheetName || null,
          mapping: mapping
        }),
      });

      if (!res.ok) throw new Error('Failed to analyze data quality');
      const data = await res.json();
      setQualityReport(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingReport(false);
    }
  };

  useEffect(() => {
    fetchQualityReport();
  }, [mapping, sheetName]);

  const handleWeightChange = (key, val) => {
    setWeights(prev => ({
      ...prev,
      [key]: parseInt(val) || 0
    }));
  };

  const showWeights = mappedKeys.includes('final_exam') || mappedKeys.includes('internal_1') || mappedKeys.includes('internal_2');
  const totalWeights = weights.internal + weights.assignment + weights.quiz + weights.final_exam;
  const weightsValid = !showWeights || totalWeights === 100;

  const handleCleanAndLoad = async () => {
    if (!weightsValid || !isMappingValid) return;
    setCleaningInProgress(true);
    setError('');
    try {
      const normalizedWeights = {
        internal: weights.internal / 100.0,
        assignment: weights.assignment / 100.0,
        quiz: weights.quiz / 100.0,
        final_exam: weights.final_exam / 100.0
      };

      const res = await fetch('/api/clean-and-load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: uploadedFile.file_path,
          sheet_name: sheetName || null,
          mapping: mapping,
          weights: normalizedWeights,
          passing_threshold: passingThreshold
        }),
      });

      if (!res.ok) throw new Error('Data cleaning pipeline failed');
      const data = await res.json();
      setCleaningResult(data);
      setDataCleaned(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setCleaningInProgress(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Data Quality & Cleaning Hub</h1>
        <p className="page-subtitle">Prepare, sanitize, and validate your dataset for analytical processing.</p>
      </div>

      {error && <div className="card" style={{ borderLeft: '4px solid var(--accent-danger)', color: 'var(--accent-danger)', marginBottom: '1.5rem' }}>{error}</div>}

      <div className="grid-2">
        <div className="card">
          <h3>Dataset Profile Card</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span>Total Rows:</span>
              <strong>{(uploadedFile.total_rows || (uploadedFile.preview && uploadedFile.preview.length) || 0).toLocaleString()}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span>Total Columns:</span>
              <strong>{uploadedFile.columns ? uploadedFile.columns.length : 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span>Detected Numeric Columns:</span>
              <strong>{numericColsCount}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span>Mapped Fields:</span>
              <strong style={{ color: 'var(--accent-primary)' }}>{mappedCount} of {allPotentialFields.length}</strong>
            </div>
            {missingFields.length > 0 && (
              <div style={{ marginTop: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Unmapped optional fields:</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.3rem' }}>
                  {missingFields.slice(0, 5).map(f => (
                    <span key={f.key} className="badge" style={{ backgroundColor: 'var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>
                      {f.label}
                    </span>
                  ))}
                  {missingFields.length > 5 && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>+{missingFields.length - 5} more</span>}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h3>Analytics Available for Your Dataset</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: hasStudent ? 'var(--accent-success)' : 'var(--text-muted)', fontWeight: 'bold' }}>{hasStudent ? '✓' : '○'}</span>
              <span style={{ textDecoration: hasStudent ? 'none' : 'line-through', color: hasStudent ? 'var(--text-primary)' : 'var(--text-muted)' }}>Student Performance Analysis</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: hasSubject ? 'var(--accent-success)' : 'var(--text-muted)', fontWeight: 'bold' }}>{hasSubject ? '✓' : '○'}</span>
              <span style={{ textDecoration: hasSubject ? 'none' : 'line-through', color: hasSubject ? 'var(--text-primary)' : 'var(--text-muted)' }}>Subject Comparison Analysis</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: hasAttendance ? 'var(--accent-success)' : 'var(--text-muted)', fontWeight: 'bold' }}>{hasAttendance ? '✓' : '○'}</span>
              <span style={{ textDecoration: hasAttendance ? 'none' : 'line-through', color: hasAttendance ? 'var(--text-primary)' : 'var(--text-muted)' }}>Attendance Analytics</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: hasLearningBehavior ? 'var(--accent-success)' : 'var(--text-muted)', fontWeight: 'bold' }}>{hasLearningBehavior ? '✓' : '○'}</span>
              <span style={{ textDecoration: hasLearningBehavior ? 'none' : 'line-through', color: hasLearningBehavior ? 'var(--text-primary)' : 'var(--text-muted)' }}>Learning Behavior Analysis</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: hasGPA ? 'var(--accent-success)' : 'var(--text-muted)', fontWeight: 'bold' }}>{hasGPA ? '✓' : '○'}</span>
              <span style={{ textDecoration: hasGPA ? 'none' : 'line-through', color: hasGPA ? 'var(--text-primary)' : 'var(--text-muted)' }}>GPA & Trend Tracking</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <span style={{ color: hasDept ? 'var(--accent-success)' : 'var(--text-muted)', fontWeight: 'bold' }}>{hasDept ? '✓' : '○'}</span>
              <span style={{ textDecoration: hasDept ? 'none' : 'line-through', color: hasDept ? 'var(--text-primary)' : 'var(--text-muted)' }}>Department Rankings</span>
            </div>
            {(!hasAttendance || !hasLearningBehavior || !hasStudent) && (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                ℹ Some analytics modules are disabled or limited because columns are missing. The engine will skip them and analyze ONLY present data.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginTop: '1.5rem' }}>
        <div className="card">
          <h3>Data Quality Assessment</h3>
          {loadingReport ? (
            <p style={{ color: 'var(--text-muted)' }}>Analyzing records...</p>
          ) : qualityReport ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Overall Health Status:</span>
                <span className={`badge badge-${qualityReport.statuses.overall === 'GOOD' ? 'success' : (qualityReport.statuses.overall === 'WARNING' ? 'warning' : 'danger')}`}>
                  {qualityReport.statuses.overall}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                  <span>Duplicate Records:</span>
                  <span style={{ display: 'flex', alignItems: 'center' }}>
                    <span className={`dot dot-${qualityReport.statuses.duplicates === 'GOOD' ? 'success' : 'warning'}`}></span>
                    {qualityReport.duplicates}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                  <span>Missing Values Count:</span>
                  <span style={{ display: 'flex', alignItems: 'center' }}>
                    <span className={`dot dot-${qualityReport.statuses.missing === 'GOOD' ? 'success' : (qualityReport.statuses.missing === 'WARNING' ? 'warning' : 'danger')}`}></span>
                    {qualityReport.missing_count} ({qualityReport.missing_percentage}%)
                  </span>
                </div>
                {hasMarks && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                    <span>Invalid Marks Range:</span>
                    <span style={{ display: 'flex', alignItems: 'center' }}>
                      <span className={`dot dot-${qualityReport.statuses.marks === 'GOOD' ? 'success' : 'warning'}`}></span>
                      {qualityReport.invalid_marks} detected
                    </span>
                  </div>
                )}
                {hasAttendance && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                    <span>Invalid Attendance Range:</span>
                    <span style={{ display: 'flex', alignItems: 'center' }}>
                      <span className={`dot dot-${qualityReport.statuses.attendance === 'GOOD' ? 'success' : 'warning'}`}></span>
                      {qualityReport.invalid_attendance} detected
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Assessments will populate once mapping is confirmed.</p>
          )}
        </div>

        <div className="card">
          <h3>Parameters & Configurations</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <label className="form-label" style={{ margin: 0, fontWeight: 'bold' }}>Passing Threshold Mark:</label>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>Used to compute passing/fail rates (default: 40).</p>
            </div>
            <input 
              type="number" 
              className="form-control" 
              style={{ width: '80px', padding: '0.4rem', textAlign: 'center' }}
              value={passingThreshold} 
              onChange={(e) => setPassingThreshold(Math.max(0, Math.min(100, parseInt(e.target.value) || 0)))}
              disabled={dataCleaned}
            />
          </div>

          {showWeights ? (
            <div>
              <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0.75rem 0' }} />
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>Academic Performance Index Weights (Total 100%)</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                  <span>Internal Assessment Weight (%):</span>
                  <input 
                    type="number" 
                    className="form-control" 
                    style={{ width: '70px', padding: '0.3rem', textAlign: 'center' }}
                    value={weights.internal} 
                    onChange={(e) => handleWeightChange('internal', e.target.value)}
                    disabled={dataCleaned}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                  <span>Assignments Weight (%):</span>
                  <input 
                    type="number" 
                    className="form-control" 
                    style={{ width: '70px', padding: '0.3rem', textAlign: 'center' }}
                    value={weights.assignment} 
                    onChange={(e) => handleWeightChange('assignment', e.target.value)}
                    disabled={dataCleaned}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                  <span>Quiz Weight (%):</span>
                  <input 
                    type="number" 
                    className="form-control" 
                    style={{ width: '70px', padding: '0.3rem', textAlign: 'center' }}
                    value={weights.quiz} 
                    onChange={(e) => handleWeightChange('quiz', e.target.value)}
                    disabled={dataCleaned}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                  <span>Final Exam Weight (%):</span>
                  <input 
                    type="number" 
                    className="form-control" 
                    style={{ width: '70px', padding: '0.3rem', textAlign: 'center' }}
                    value={weights.final_exam} 
                    onChange={(e) => handleWeightChange('final_exam', e.target.value)}
                    disabled={dataCleaned}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                  <span>Total Sum:</span>
                  <span style={{ color: weightsValid ? 'var(--accent-success)' : 'var(--accent-danger)' }}>{totalWeights}%</span>
                </div>
                {!weightsValid && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-danger)', textAlign: 'right' }}>
                    Weights must total exactly 100% to run cleaning pipeline.
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
              ℹ No marks weighting configurations are required for this dataset.
            </p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3>Execution Pipeline</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          This will execute deduplication, clean range boundaries, fill missing values dynamically, and load your data into the relational database.
        </p>

        {!isMappingValid && (
          <div className="card" style={{ borderLeft: '4px solid var(--accent-danger)', backgroundColor: 'rgba(255, 0, 0, 0.05)', color: 'var(--accent-danger)', padding: '1rem', marginBottom: '1.25rem' }}>
            <strong>Warning: No Columns Mapped</strong>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Please map at least one column from your spreadsheet to proceed.
            </p>
          </div>
        )}

        {!dataCleaned && (
          <button 
            className="btn btn-primary" 
            onClick={handleCleanAndLoad} 
            disabled={cleaningInProgress || !weightsValid || !isMappingValid}
          >
            {cleaningInProgress ? 'Executing Clean & Normalize...' : 'Clean Data and Load to Relational Database'}
          </button>
        )}

        {dataCleaned && cleaningResult && (
          <div className="cleaning-summary-box" style={{ marginTop: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', color: 'var(--accent-success)', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.5rem', marginRight: '8px' }}>✓</span>
              <strong>Database Load Successful! Data is fully normalized.</strong>
            </div>

            <div className="cleaning-log">
              <div className="log-entry success">✓ {cleaningResult.cleaning_statistics ? cleaningResult.cleaning_statistics.duplicates_removed : 0} duplicate records removed</div>
              <div className="log-entry success">✓ {cleaningResult.cleaning_statistics ? cleaningResult.cleaning_statistics.missing_filled : 0} missing values mapped and filled</div>
              <div className="log-entry success">✓ {cleaningResult.cleaning_statistics ? cleaningResult.cleaning_statistics.marks_corrected : 0} invalid marks range violations corrected</div>
              <div className="log-entry success">✓ {cleaningResult.cleaning_statistics ? cleaningResult.cleaning_statistics.attendance_corrected : 0} invalid attendance percentage entries handled</div>
              <div className="log-entry success">✓ Normalized text casings and trimmed extra whitespaces</div>
              <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '0.5rem 0' }} />
              <div className="log-entry success">=== Relational Ingestion Report ===</div>
              <div className="log-entry">→ Loaded {cleaningResult.records_loaded.students} records into 'students'</div>
              <div className="log-entry">→ Loaded {cleaningResult.records_loaded.subjects} subjects into 'subjects'</div>
              <div className="log-entry">→ Seeded {cleaningResult.records_loaded.attendance} items into 'attendance'</div>
              <div className="log-entry">→ Loaded {cleaningResult.records_loaded.assessments} records into 'assessments'</div>
              <div className="log-entry">→ Loaded {cleaningResult.records_loaded.learning_behavior} logs into 'learning_behavior'</div>
              <div className="log-entry">→ Saved {cleaningResult.records_loaded.student_performance} metrics into 'student_performance'</div>
            </div>
            
            <div style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Navigate to the <strong>SQL Database</strong> or <strong>EDA & Statistics</strong> tabs in the sidebar to run analysis.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DataCleaning;
