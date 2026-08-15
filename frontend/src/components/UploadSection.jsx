import React, { useState } from 'react';

function UploadSection({ onUploadSuccess, uploadedFile, mapping, setMapping, sheetName, setSheetName }) {
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    setLoading(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let errMsg = 'File upload failed';
        try {
          const contentType = res.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errData = await res.json();
            errMsg = errData.detail || errMsg;
          } else {
            const textData = await res.text();
            errMsg = textData || errMsg;
          }
        } catch (parseError) {
          errMsg = `Server error (Status ${res.status})`;
        }
        throw new Error(errMsg);
      }

      const contentType = res.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await res.json();
        onUploadSuccess(data);
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSheetChange = async (newSheet) => {
    setSheetName(newSheet);
    setLoading(true);
    try {
      const res = await fetch('/api/preview-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: uploadedFile.file_path, sheet_name: newSheet }),
      });
      if (!res.ok) throw new Error('Failed to load sheet');
      
      const data = await res.json();
      onUploadSuccess({
        ...uploadedFile,
        columns: data.columns,
        preview: data.preview,
        types: data.types,
        auto_mapping: data.auto_mapping,
        unmapped_fields: data.unmapped_fields
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMappingChange = (key, value) => {
    setMapping(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const mappingFields = [
    { key: "student_id", label: "Student ID / Roll Number", required: false },
    { key: "student_name", label: "Student Name", required: false },
    { key: "department", label: "Department / Stream", required: false },
    { key: "semester", label: "Semester", required: false },
    { key: "academic_year", label: "Academic Year", required: false },
    { key: "subject", label: "Course / Subject", required: false },
    { key: "attendance", label: "Attendance %", required: false },
    { key: "internal_1", label: "Internal Assessment 1 Marks", required: false },
    { key: "internal_2", label: "Internal Assessment 2 Marks", required: false },
    { key: "assignment_score", label: "Assignment Score", required: false },
    { key: "quiz_score", label: "Quiz Score", required: false },
    { key: "final_exam", label: "Final Exam Score", required: false },
    { key: "previous_gpa", label: "Previous GPA", required: false },
    { key: "study_hours", label: "Study Hours per Week", required: false },
    { key: "lms_activity", label: "LMS Activity logs count", required: false },
    { key: "assignment_completion", label: "Assignment Completion %", required: false }
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Educational Data Ingestion</h1>
        <p className="page-subtitle">Upload CSV/Excel spreadsheets containing student profile and performance parameters.</p>
      </div>

      {error && <div className="card" style={{ borderLeft: '4px solid var(--accent-danger)', color: 'var(--accent-danger)', marginBottom: '1.5rem' }}>{error}</div>}

      {/* File Drop Area */}
      <div 
        className={`drag-drop-area ${dragActive ? 'drag-over' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-upload-input').click()}
      >
        <input 
          id="file-upload-input" 
          type="file" 
          style={{ display: 'none' }} 
          accept=".csv,.xls,.xlsx" 
          onChange={handleFileChange}
        />
        <div className="upload-icon">📤</div>
        <h3>{loading ? 'Processing File...' : 'Drag & Drop your spreadsheet here'}</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
          Supports .csv, .xls, and .xlsx files. Clicking here will open file chooser.
        </p>
      </div>

      {uploadedFile && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h3>Active Dataset: <span style={{ color: 'var(--accent-primary)' }}>{uploadedFile.filename}</span></h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Format detected: {uploadedFile.file_type.toUpperCase()}</p>
            </div>
            
            {/* Sheet Selector */}
            {uploadedFile.sheets && uploadedFile.sheets.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Select Sheet:</span>
                <select 
                  className="form-control" 
                  style={{ width: '200px', padding: '0.5rem' }} 
                  value={sheetName} 
                  onChange={(e) => handleSheetChange(e.target.value)}
                >
                  {uploadedFile.sheets.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            )}
          </div>

          <h4 style={{ marginBottom: '0.75rem' }}>Column Schema Mapping</h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            Verify that your dataset fields are correctly mapped to our system targets. Adjust dropdowns manually if needed.
          </p>

          <div className="mapping-grid">
            {mappingFields.map(f => (
              <div className="mapping-card" key={f.key}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="mapping-label">{f.label}</span>
                  {f.required && <span style={{ color: 'var(--accent-danger)', fontSize: '0.7rem' }}>* Required</span>}
                </div>
                <select 
                  className="form-control" 
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                  value={mapping[f.key] || ''} 
                  onChange={(e) => handleMappingChange(f.key, e.target.value)}
                >
                  <option value="">-- Unmapped --</option>
                  {uploadedFile.columns.map(col => <option key={col} value={col}>{col}</option>)}
                </select>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '1.5rem' }}>
            <h4>Raw Dataset Preview (First {uploadedFile.preview.length} Rows)</h4>
            <div className="table-container" style={{ marginTop: '0.75rem', maxHeight: '300px' }}>
              <table>
                <thead>
                  <tr>
                    {uploadedFile.columns.map(col => (
                      <th key={col}>{col} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>({uploadedFile.types[col]})</span></th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {uploadedFile.preview.map((row, idx) => (
                    <tr key={idx}>
                      {uploadedFile.columns.map(col => (
                        <td key={col}>{row[col] === null ? <span style={{ color: 'var(--accent-danger)' }}>Null</span> : String(row[col])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UploadSection;
