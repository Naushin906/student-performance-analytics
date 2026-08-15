import React, { useState, useEffect } from 'react';

function EarlyWarning() {
  const [warningData, setWarningData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedStudent, setSelectedStudent] = useState(null);

  // Filters
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [deptFilter, setDeptFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchWarningData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/early-warning');
      if (!res.ok) throw new Error('Failed to fetch warning details');
      const data = await res.json();
      setWarningData(data);
      if (data.risk_list && data.risk_list.length > 0) {
        setSelectedStudent(data.risk_list[0].student_id);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWarningData();
  }, []);

  const handleUpdateIntervention = async (id, currentStatus) => {
    const newStatus = currentStatus === 'PENDING' ? 'RESOLVED' : 'PENDING';
    try {
      const res = await fetch('/api/update-intervention', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status: newStatus }),
      });
      if (res.ok) {
        // update local state
        setWarningData(prev => ({
          ...prev,
          interventions: prev.interventions.map(item => 
            item.id === id ? { ...item, status: newStatus } : item
          )
        }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div style={{ color: 'var(--text-muted)' }}>Retrieving Early Warning signals...</div>;
  if (error) return <div className="card" style={{ borderLeft: '4px solid var(--accent-danger)', color: 'var(--accent-danger)' }}>Error: {error}</div>;

  const { risk_list, student_indicators, interventions } = warningData;

  if (!risk_list || risk_list.length === 0) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Early Warning Center</h1>
          <p className="page-subtitle">Identify students with high risk signals and execute targeted academic recommendations.</p>
        </div>
        <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>⚠️</div>
          <h3>No Risk Prediction Data Available</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '500px', margin: '0.5rem auto 1.5rem auto', lineHeight: '1.5' }}>
            The Early Warning system relies on machine learning predictions. Please go to the <strong>Cluster & ML</strong> tab, train a model, and click <strong>"Save Predictions & Re-build Interventions"</strong>.
          </p>
        </div>
      </div>
    );
  }

  // Extract unique departments for filter
  const departments = ['ALL', ...new Set(risk_list.map(s => s.department))];

  // Filters logic
  const filteredStudents = risk_list.filter(student => {
    const matchesRisk = riskFilter === 'ALL' || student.risk_level === riskFilter;
    const matchesDept = deptFilter === 'ALL' || student.department === deptFilter;
    const matchesSearch = student.student_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          student.student_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesRisk && matchesDept && matchesSearch;
  });

  const highRiskCount = risk_list.filter(s => s.risk_level === 'HIGH').length;
  const medRiskCount = risk_list.filter(s => s.risk_level === 'MEDIUM').length;
  const lowRiskCount = risk_list.filter(s => s.risk_level === 'LOW').length;

  const activeStudentInfo = student_indicators[selectedStudent];
  const activeStudentProfile = risk_list.find(s => s.student_id === selectedStudent);
  const activeStudentInterventions = interventions.filter(i => i.student_id === selectedStudent);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Early Warning Center</h1>
        <p className="page-subtitle">Identify students with high risk signals and execute targeted academic recommendations.</p>
      </div>

      {/* Summary Row */}
      <div className="grid-3">
        <div className="card" style={{ borderTop: '4px solid var(--accent-danger)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>High Risk Students</span>
          <h2 style={{ fontSize: '2.5rem', color: 'var(--accent-danger)', margin: '0.5rem 0 0 0' }}>{highRiskCount}</h2>
        </div>
        <div className="card" style={{ borderTop: '4px solid var(--accent-warning)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Medium Risk Students</span>
          <h2 style={{ fontSize: '2.5rem', color: 'var(--accent-warning)', margin: '0.5rem 0 0 0' }}>{medRiskCount}</h2>
        </div>
        <div className="card" style={{ borderTop: '4px solid var(--accent-success)' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Low Risk Students</span>
          <h2 style={{ fontSize: '2.5rem', color: 'var(--accent-success)', margin: '0.5rem 0 0 0' }}>{lowRiskCount}</h2>
        </div>
      </div>

      {/* Filters Panel */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <input 
              type="text" 
              className="form-control" 
              placeholder="Search by student name or roll number..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div>
            <select className="form-control" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
              <option value="ALL">All Risk Levels</option>
              <option value="HIGH">High Risk</option>
              <option value="MEDIUM">Medium Risk</option>
              <option value="LOW">Low Risk</option>
            </select>
          </div>
          <div>
            <select className="form-control" value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
              {departments.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Student List & Detailed Dashboard */}
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        
        {/* Left Column: Student List */}
        <div className="card" style={{ flex: '1 1 350px', padding: '1rem', maxHeight: '550px', overflowY: 'auto' }}>
          <h3 style={{ padding: '0.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Students ({filteredStudents.length})</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>Probability Sort</span>
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
            {filteredStudents.length > 0 ? filteredStudents.map(student => {
              const badgeClass = student.risk_level === 'HIGH' ? 'danger' : (student.risk_level === 'MEDIUM' ? 'warning' : 'success');
              const isSelected = selectedStudent === student.student_id;
              return (
                <div 
                  key={student.student_id} 
                  style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    padding: '0.75rem 1rem', 
                    borderRadius: '6px', 
                    border: '1px solid var(--border-color)', 
                    backgroundColor: isSelected ? 'var(--bg-tertiary)' : 'var(--bg-primary)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    borderLeft: isSelected ? '4px solid var(--accent-primary)' : '1px solid var(--border-color)'
                  }}
                  onClick={() => setSelectedStudent(student.student_id)}
                >
                  <div>
                    <strong style={{ display: 'block', color: 'var(--text-primary)' }}>{student.student_name}</strong>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{student.student_id} • {student.department}</span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className={`badge badge-${badgeClass}`} style={{ fontSize: '0.7rem' }}>
                      {student.risk_level} ({student.risk_probability.toFixed(0)}%)
                    </span>
                  </div>
                </div>
              );
            }) : (
              <p style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)' }}>No students match the active filters.</p>
            )}
          </div>
        </div>

        {/* Right Column: Active Student Warning Dashboard & Recommendations */}
        <div className="card" style={{ flex: '2 1 600px' }}>
          {activeStudentProfile && activeStudentInfo ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1.25rem' }}>
                <div>
                  <h2>{activeStudentProfile.student_name}</h2>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    Roll: <code>{activeStudentProfile.student_id}</code> | Dept: {activeStudentProfile.department} | Semester: {activeStudentProfile.semester}
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className={`badge badge-${activeStudentProfile.risk_level === 'HIGH' ? 'danger' : (activeStudentProfile.risk_level === 'MEDIUM' ? 'warning' : 'success')}`} style={{ fontSize: '0.9rem' }}>
                    {activeStudentProfile.risk_level} RISK PROFILE
                  </span>
                  <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Risk Prob: {activeStudentProfile.risk_probability}%</span>
                </div>
              </div>

              {/* Bivariate Performance Metrics for active student */}
              <h4 style={{ marginBottom: '0.5rem' }}>Key Performance Indicators (Associated with Higher Risk)</h4>
              <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
                <div style={{ padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Attendance Avg</span>
                  <strong style={{ fontSize: '1.25rem', color: activeStudentInfo.attendance_avg < 75 ? 'var(--accent-danger)' : 'var(--text-primary)' }}>
                    {activeStudentInfo.attendance_avg}%
                  </strong>
                </div>
                <div style={{ padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Internal Exam Avg</span>
                  <strong style={{ fontSize: '1.25rem', color: activeStudentInfo.internals_avg < 18 ? 'var(--accent-warning)' : 'var(--text-primary)' }}>
                    {activeStudentInfo.internals_avg} / 30
                  </strong>
                </div>
                <div style={{ padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Study Hours/Week</span>
                  <strong style={{ fontSize: '1.25rem', color: activeStudentInfo.study_hours < 8 ? 'var(--accent-warning)' : 'var(--text-primary)' }}>
                    {activeStudentInfo.study_hours} hrs
                  </strong>
                </div>
                <div style={{ padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Previous GPA</span>
                  <strong style={{ fontSize: '1.25rem' }}>{activeStudentInfo.previous_gpa}</strong>
                </div>
                <div style={{ padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Assignment Completion</span>
                  <strong style={{ fontSize: '1.25rem', color: activeStudentInfo.assign_completion < 60 ? 'var(--accent-danger)' : 'var(--text-primary)' }}>
                    {activeStudentInfo.assign_completion}%
                  </strong>
                </div>
              </div>

              {/* Actionable Interventions Feed */}
              <h4>Actionable Recommendations & Interventions</h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                Automated recommendations derived from actual student indicators. Toggle to track resolutions.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {activeStudentInterventions.length > 0 ? activeStudentInterventions.map(item => {
                  const isResolved = item.status === 'RESOLVED';
                  return (
                    <div 
                      key={item.id} 
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center', 
                        padding: '1rem', 
                        border: '1px solid var(--border-color)', 
                        borderRadius: '6px', 
                        backgroundColor: 'var(--bg-primary)',
                        opacity: isResolved ? 0.6 : 1,
                        transition: 'opacity 0.2s ease',
                        borderLeft: isResolved ? '4px solid var(--accent-success)' : '4px solid var(--accent-danger)'
                      }}
                    >
                      <div style={{ flex: 1, paddingRight: '1rem' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'block' }}>{item.category}</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{item.recommendation_text}</span>
                      </div>
                      <div>
                        <button 
                          className={`btn ${isResolved ? 'btn-secondary' : 'btn-primary'}`}
                          style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', whiteSpace: 'nowrap' }}
                          onClick={() => handleUpdateIntervention(item.id, item.status)}
                        >
                          {isResolved ? '✓ Resolved' : 'Mark Resolved'}
                        </button>
                      </div>
                    </div>
                  );
                }) : (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No intervention alerts triggered for this profile.</p>
                )}
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>Select a student from the sidebar list to inspect warning triggers.</p>
          )}
        </div>

      </div>
    </div>
  );
}

export default EarlyWarning;
