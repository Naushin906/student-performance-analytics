import React, { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';

function ModelTrainer() {
  const [segData, setSegData] = useState(null);
  const [mlData, setMlData] = useState(null);
  const [selectedModel, setSelectedModel] = useState('Random Forest');
  const [riskThreshold, setRiskThreshold] = useState(50);
  const [training, setTraining] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const [error, setError] = useState('');

  const fetchSegmentation = async () => {
    try {
      const res = await fetch('/api/segmentation');
      if (res.ok) {
        const data = await res.json();
        setSegData(data);
      } else {
        const data = await res.json();
        setSegData({ error: data.detail || 'Clustering failed' });
      }
    } catch (e) {
      setSegData({ error: e.message });
    }
  };

  useEffect(() => {
    fetchSegmentation();
  }, []);

  const handleTrainModels = async () => {
    setTraining(true);
    setError('');
    setApplyResult(null);
    try {
      const res = await fetch('/api/train-models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ risk_threshold: riskThreshold }),
      });
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      if (!res.ok) {
        throw new Error(data.detail || 'ML model training failed');
      }
      setMlData(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  };

  const handleApplyPredictions = async () => {
    setApplying(true);
    setError('');
    try {
      const res = await fetch('/api/apply-predictions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: selectedModel, risk_threshold: riskThreshold }),
      });
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save predictions to database');
      }
      setApplyResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setApplying(false);
    }
  };

  // Feature Importance Chart details if ML trained
  let importanceChartData = null;
  if (mlData && mlData.model_evaluation && mlData.model_evaluation[selectedModel]) {
    const featLabels = mlData.model_evaluation[selectedModel].feature_importance.map(f => f.feature.replace('_', ' '));
    const featVals = mlData.model_evaluation[selectedModel].feature_importance.map(f => f.importance);
    importanceChartData = {
      labels: featLabels,
      datasets: [{
        label: 'Feature Weight / Importance',
        data: featVals,
        backgroundColor: 'rgba(56, 189, 248, 0.4)',
        borderColor: 'rgba(56, 189, 248, 1)',
        borderWidth: 1,
      }]
    };
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false }
    },
    scales: {
      x: { grid: { color: 'hsl(222, 25%, 20%)' }, ticks: { color: 'hsl(215, 20%, 75%)' } },
      y: { grid: { color: 'hsl(222, 25%, 20%)' }, ticks: { color: 'hsl(215, 20%, 75%)' } }
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Machine Learning & Student Segmentation</h1>
        <p className="page-subtitle">Run unsupervised K-Means groupings and train risk classification algorithms.</p>
      </div>

      {error && <div className="card" style={{ borderLeft: '4px solid var(--accent-danger)', color: 'var(--accent-danger)', marginBottom: '1.5rem' }}>{error}</div>}

      {/* K-Means clustering segments */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3>Unsupervised Student Segmentation (K-Means Clustering)</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Groups students into academic profile archetypes based on GPA, Attendance, Study Hours, LMS activity, and exams.
        </p>

        {segData ? (
          segData.error ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: '4px', borderLeft: '3px solid var(--text-muted)' }}>
              ℹ {segData.error}
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <span>Optimal Clusters Detected (K): <strong style={{ color: 'var(--accent-primary)' }}>{segData.best_k}</strong></span>
                <span>Silhouette Score: <strong style={{ color: 'var(--accent-success)' }}>{segData.silhouette_scores[segData.best_k]}</strong></span>
              </div>

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Student Segment Profile</th>
                      <th>Students Count</th>
                      <th>Average GPA</th>
                      <th>Average Attendance</th>
                      <th>Study Hours/Week</th>
                      <th>LMS Activity logs</th>
                      <th>Assignment Completion %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {segData.segments.map(seg => (
                      <tr key={seg.segment}>
                        <td><strong>{seg.segment}</strong></td>
                        <td>{seg.student_count}</td>
                        <td>{seg.current_gpa}</td>
                        <td>{seg.attendance_pct || 0}%</td>
                        <td>{seg.study_hours || 0} hrs</td>
                        <td>{seg.lms_activity || 0}</td>
                        <td>{seg.assignment_completion || 0}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ) : (
          <p style={{ color: 'var(--text-muted)' }}>Loading student clusters...</p>
        )}
      </div>

      {/* ML Risk Model Training */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3>Academic Risk Prediction Classifier</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Train Logistic Regression, Random Forest, and XGBoost models on a 70/30 split to classify risk. Set the classification threshold probability.
        </p>

        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div style={{ flex: 1 }}>
            <label className="form-label">Classification Probability Threshold: <strong style={{ color: 'var(--accent-primary)' }}>{riskThreshold}%</strong></label>
            <input 
              type="range" 
              min="20" 
              max="80" 
              value={riskThreshold} 
              onChange={(e) => setRiskThreshold(e.target.value)} 
              style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
            />
          </div>
          <button className="btn btn-primary" onClick={handleTrainModels} disabled={training}>
            {training ? 'Training Classifier Models...' : 'Train Risk Classifier Models'}
          </button>
        </div>

        {mlData && (
          <div>
            <h4>Actual Model Test Set Evaluations (Stratified 30% Test Size)</h4>
            <div className="table-container" style={{ margin: '1rem 0' }}>
              <table>
                <thead>
                  <tr>
                    <th>Model Classifier</th>
                    <th>Accuracy</th>
                    <th>Precision (Positive class)</th>
                    <th>Recall (Risk Sensitivity)</th>
                    <th>F1 Score</th>
                    <th>ROC-AUC Score</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(mlData.model_evaluation).map(([name, res]) => (
                    <tr key={name} style={{ backgroundColor: selectedModel === name ? 'rgba(56, 189, 248, 0.05)' : '' }}>
                      <td><strong>{name}</strong></td>
                      <td>{(res.metrics.accuracy * 100).toFixed(1)}%</td>
                      <td>{(res.metrics.precision * 100).toFixed(1)}%</td>
                      <td>{(res.metrics.recall * 100).toFixed(1)}%</td>
                      <td>{res.metrics.f1_score}</td>
                      <td>{res.metrics.roc_auc}</td>
                      <td>
                        <button 
                          className={`btn ${selectedModel === name ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
                          onClick={() => setSelectedModel(name)}
                        >
                          Select
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Selected Model Profiling and Confusion Matrix */}
            <div className="grid-2" style={{ marginTop: '1.5rem' }}>
              <div>
                <h4>Confusion Matrix ({selectedModel})</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', marginTop: '0.75rem', maxWidth: '240px', fontFamily: 'var(--font-mono)' }}>
                  <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>True Negative</span>
                    <strong>{mlData.model_evaluation[selectedModel].confusion_matrix[0][0]}</strong>
                  </div>
                  <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>False Positive</span>
                    <strong>{mlData.model_evaluation[selectedModel].confusion_matrix[0][1]}</strong>
                  </div>
                  <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>False Negative</span>
                    <strong>{mlData.model_evaluation[selectedModel].confusion_matrix[1][0]}</strong>
                  </div>
                  <div style={{ background: 'var(--bg-primary)', padding: '0.75rem', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>True Positive</span>
                    <strong>{mlData.model_evaluation[selectedModel].confusion_matrix[1][1]}</strong>
                  </div>
                </div>
              </div>

              <div>
                <h4>Feature Importance / Coefficients</h4>
                <div style={{ height: '180px', position: 'relative', marginTop: '0.75rem' }}>
                  {importanceChartData && <Bar data={importanceChartData} options={chartOptions} />}
                </div>
              </div>
            </div>

            {/* Apply Selected Model */}
            <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>Execute Risk Pipeline with {selectedModel}</strong>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>This saves calculated risks to DB tables and triggers recommendations.</p>
                </div>
                <button className="btn btn-primary" onClick={handleApplyPredictions} disabled={applying}>
                  {applying ? 'Applying Pipeline...' : `Save Predictions & Re-build Interventions`}
                </button>
              </div>

              {applyResult && (
                <div style={{ borderLeft: '4px solid var(--accent-success)', color: 'var(--accent-success)', backgroundColor: 'rgba(16, 185, 129, 0.05)', padding: '0.75rem 1rem', borderRadius: '4px', marginTop: '1rem', fontSize: '0.85rem' }}>
                  ✓ Successfully saved <strong>{applyResult.predictions_applied}</strong> student risk calculations to table <code>risk_predictions</code>.
                  <br />
                  ✓ Generated and queued <strong>{applyResult.interventions_created}</strong> action items to table <code>interventions</code>. Check the <strong>Early Warning</strong> tab.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ModelTrainer;
