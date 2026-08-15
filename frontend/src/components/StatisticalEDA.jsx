import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Scatter } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function StatisticalEDA() {
  const [edaData, setEdaData] = useState(null);
  const [statData, setStatData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAnalyticsData = async () => {
    setLoading(true);
    setError('');
    try {
      const edaRes = await fetch('/api/python-eda');
      const statRes = await fetch('/api/statistics');

      if (!edaRes.ok || !statRes.ok) {
        throw new Error('Failed to fetch analytics or statistics reports');
      }

      const eda = await edaRes.json();
      const stat = await statRes.json();

      setEdaData(eda);
      setStatData(stat);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  if (loading) return <div style={{ color: 'var(--text-muted)' }}>Running Exploratory Data Analysis & Statistical Tests...</div>;
  if (error) return <div className="card" style={{ borderLeft: '4px solid var(--accent-danger)', color: 'var(--accent-danger)' }}>Error: {error}</div>;

  const hasGpaDist = edaData && edaData.distributions && edaData.distributions.gpa;
  const hasDeptAnalysis = edaData && edaData.department_analysis && edaData.department_analysis.length > 0;
  const hasScatterPlots = edaData && edaData.scatter_plots && edaData.scatter_plots.length > 0;
  const hasOutliers = edaData && edaData.outliers && edaData.outliers.length > 0;
  const hasCorrelations = statData && statData.correlations && statData.correlations.length > 0;

  // Chart 1: GPA Distribution
  let gpaChartData = null;
  if (hasGpaDist) {
    const gpaBins = edaData.distributions.gpa.bins;
    const gpaLabels = gpaBins.slice(0, -1).map((b, i) => `${b} - ${gpaBins[i+1]}`);
    gpaChartData = {
      labels: gpaLabels,
      datasets: [{
        label: 'Student Count',
        data: edaData.distributions.gpa.counts,
        backgroundColor: 'rgba(56, 189, 248, 0.4)',
        borderColor: 'rgba(56, 189, 248, 1)',
        borderWidth: 1,
      }]
    };
  }

  // Chart 2: Department GPA Comparison
  let deptChartData = null;
  if (hasDeptAnalysis) {
    const deptLabels = edaData.department_analysis.map(d => d.department);
    const deptGpas = edaData.department_analysis.map(d => d.current_gpa || d.average_gpa || 0);
    deptChartData = {
      labels: deptLabels,
      datasets: [{
        label: 'Average GPA',
        data: deptGpas,
        backgroundColor: 'rgba(16, 185, 129, 0.4)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1,
      }]
    };
  }

  // Chart 3: Study Hours vs GPA Scatter
  let scatterChartData = null;
  let scatterXLabel = 'Study Hours / Week';
  if (hasScatterPlots) {
    const sample = edaData.scatter_plots[0];
    const useStudyHours = sample.study_hours !== undefined;
    scatterXLabel = useStudyHours ? 'Study Hours / Week' : 'Attendance %';

    const scatterPoints = edaData.scatter_plots.map(d => ({
      x: useStudyHours ? d.study_hours : d.attendance_pct,
      y: d.current_gpa || 0,
      studentName: d.student_name || d.student_id,
      dept: d.department || 'All'
    }));

    scatterChartData = {
      datasets: [{
        label: `Students (${scatterXLabel} vs GPA)`,
        data: scatterPoints,
        backgroundColor: 'rgba(245, 158, 11, 0.6)',
        pointRadius: 5,
      }]
    };
  }

  const scatterOptions = {
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const pt = ctx.raw;
            return `${pt.studentName} (${pt.dept}): Value: ${pt.x}, GPA: ${pt.y}`;
          }
        }
      }
    },
    scales: {
      x: { title: { display: true, text: scatterXLabel, color: 'hsl(215, 20%, 75%)' }, grid: { color: 'hsl(222, 25%, 20%)' } },
      y: { title: { display: true, text: 'Current GPA', color: 'hsl(215, 20%, 75%)' }, grid: { color: 'hsl(222, 25%, 20%)' } }
    }
  };

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: 'hsl(215, 20%, 75%)' } }
    },
    scales: {
      x: { grid: { color: 'hsl(222, 25%, 20%)' }, ticks: { color: 'hsl(215, 20%, 75%)' } },
      y: { grid: { color: 'hsl(222, 25%, 20%)' }, ticks: { color: 'hsl(215, 20%, 75%)' } }
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Exploratory Data Analysis & Statistics</h1>
        <p className="page-subtitle">Scientific analysis of grades, attendance, behaviors, and correlation tests.</p>
      </div>

      {/* Statistical Hypothesis Tests */}
      {hasCorrelations ? (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3>Scientific Association & Hypothesis Testing</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
            Hypothesis testing on student parameters using SciPy. Null Hypothesis assumes no linear correlation. p-value &lt; 0.05 rejects H0.
          </p>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Analyzed Variables</th>
                  <th>Pearson Coefficient (r)</th>
                  <th>Pearson p-value</th>
                  <th>Spearman Rank (ρ)</th>
                  <th>Statistical Signif.</th>
                  <th>Interpretation</th>
                </tr>
              </thead>
              <tbody>
                {statData.correlations.map(corr => (
                  <tr key={corr.variable}>
                    <td><strong>{corr.label}</strong></td>
                    <td>{corr.pearson_coef}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{corr.pearson_p_value.toExponential(2)}</td>
                    <td>{corr.spearman_coef}</td>
                    <td>
                      <span className={`badge badge-${corr.significant ? 'success' : 'danger'}`}>
                        {corr.significant ? 'Significant' : 'Not Significant'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{corr.interpretation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ borderLeft: '4px solid var(--accent-warning)', backgroundColor: 'rgba(245, 158, 11, 0.04)', padding: '1rem', borderRadius: '4px', marginTop: '1rem' }}>
            <strong style={{ color: 'var(--accent-warning)', display: 'block', marginBottom: '0.25rem' }}>⚠️ Correlation vs. Causation Warning</strong>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              {statData.disclaimer}
            </span>
          </div>
        </div>
      ) : (
        <div className="card" style={{ marginBottom: '1.5rem', opacity: 0.7 }}>
          <h3>Scientific Association & Hypothesis Testing</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            ℹ Hypothesis testing is not available because it requires both GPA and learning behavior/attendance columns to evaluate correlation.
          </p>
        </div>
      )}

      {/* Visual EDA Charts Grid */}
      <div className="grid-2">
        <div className="card">
          <h3>GPA Distribution Histogram</h3>
          {hasGpaDist ? (
            <div style={{ height: '250px', position: 'relative' }}>
              <Bar data={gpaChartData} options={defaultOptions} />
            </div>
          ) : (
            <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              ℹ GPA distribution histogram is not available (GPA column missing).
            </div>
          )}
        </div>

        <div className="card">
          <h3>Department GPA Performance</h3>
          {hasDeptAnalysis ? (
            <div style={{ height: '250px', position: 'relative' }}>
              <Bar data={deptChartData} options={defaultOptions} />
            </div>
          ) : (
            <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              ℹ Department GPA comparison is not available (Department column missing).
            </div>
          )}
        </div>
      </div>

      <div className="grid-2" style={{ marginTop: '1.5rem' }}>
        <div className="card">
          <h3>Dataset Correlation Scatter</h3>
          {hasScatterPlots ? (
            <div style={{ height: '250px', position: 'relative' }}>
              <Scatter data={scatterChartData} options={scatterOptions} />
            </div>
          ) : (
            <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              ℹ Bivariate scatter plot is not available (Requires GPA and at least one behavior column).
            </div>
          )}
        </div>

        <div className="card">
          <h3>Academic Outlier Profiling (IQR Check)</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
            Identifies students falling outside 1.5 * IQR bounds on current GPA distribution.
          </p>
          <div className="table-container" style={{ maxHeight: '200px' }}>
            <table>
              <thead>
                <tr>
                  <th>Student ID</th>
                  <th>Name</th>
                  <th>Department</th>
                  <th>GPA</th>
                </tr>
              </thead>
              <tbody>
                {hasOutliers ? edaData.outliers.map(out => (
                  <tr key={out.student_id}>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{out.student_id}</td>
                    <td>{out.student_name}</td>
                    <td>{out.department}</td>
                    <td><strong style={{ color: 'var(--accent-danger)' }}>{out.current_gpa}</strong></td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No distribution outliers detected or GPA column is missing.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StatisticalEDA;
