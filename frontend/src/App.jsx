import React, { useState, useEffect } from 'react';
import './App.css';

// Components
import UploadSection from './components/UploadSection';
import DataCleaning from './components/DataCleaning';
import DatabaseExplorer from './components/DatabaseExplorer';
import StatisticalEDA from './components/StatisticalEDA';
import ModelTrainer from './components/ModelTrainer';
import EarlyWarning from './components/EarlyWarning';

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [mapping, setMapping] = useState({});
  const [sheetName, setSheetName] = useState('');
  const [weights, setWeights] = useState({
    internal: 30,
    assignment: 20,
    quiz: 10,
    final_exam: 40
  });
  const [passingThreshold, setPassingThreshold] = useState(40);
  const [dbStatus, setDbStatus] = useState({ status: 'CHECKING', db_type: 'Unknown', student_count: 0 });
  const [cleaningResult, setCleaningResult] = useState(null);
  const [dataCleaned, setDataCleaned] = useState(false);

  // Poll database status on load
  const checkDbStatus = async () => {
    try {
      const res = await fetch('/api/db-status');
      const data = await res.json();
      setDbStatus(data);
      if (data.status === 'ONLINE' && data.student_count > 0) {
        setDataCleaned(true);
      }
    } catch (e) {
      setDbStatus({ status: 'OFFLINE', db_type: 'None', error: e.message });
    }
  };

  useEffect(() => {
    checkDbStatus();
  }, []);

  const handleFileUploadSuccess = (fileData) => {
    setUploadedFile(fileData);
    setMapping(fileData.auto_mapping || {});
    if (fileData.sheets && fileData.sheets.length > 0) {
      setSheetName(fileData.sheets[0]);
    }
    setDataCleaned(false);
    setCleaningResult(null);
    setActiveTab('cleaning');
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-container">
          <h2 className="logo-text">Academic Intelligence</h2>
          <span className="subtitle">Performance Intelligence System</span>
        </div>

        {/* Database Status indicator */}
        <div className="db-status-container">
          <div className="db-status-badge">
            <span className={`status-dot ${dbStatus.status === 'ONLINE' ? 'online' : 'offline'}`}></span>
            <span className="status-label">
              Database: {dbStatus.status === 'ONLINE' ? `${dbStatus.db_type}` : 'OFFLINE'}
            </span>
          </div>
          {dbStatus.student_count > 0 && (
            <div className="db-records-count">
              {dbStatus.student_count} Students Seeded
            </div>
          )}
        </div>

        {/* Tab Links */}
        <nav className="nav-list">
          <div 
            className={`nav-item ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            <span className="nav-icon">📤</span>
            <span>Upload & Preview</span>
          </div>

          <div 
            className={`nav-item ${activeTab === 'cleaning' ? 'active' : ''} ${!uploadedFile ? 'disabled' : ''}`}
            onClick={() => uploadedFile && setActiveTab('cleaning')}
          >
            <span className="nav-icon">🧹</span>
            <span>Data Cleaning</span>
          </div>

          <div 
            className={`nav-item ${activeTab === 'database' ? 'active' : ''}`}
            onClick={() => setActiveTab('database')}
          >
            <span className="nav-icon">🗄️</span>
            <span>SQL Database</span>
          </div>

          <div 
            className={`nav-item ${activeTab === 'statistics' ? 'active' : ''} ${!dataCleaned ? 'disabled' : ''}`}
            onClick={() => dataCleaned && setActiveTab('statistics')}
          >
            <span className="nav-icon">📈</span>
            <span>EDA & Statistics</span>
          </div>

          <div 
            className={`nav-item ${activeTab === 'modeling' ? 'active' : ''} ${!dataCleaned ? 'disabled' : ''}`}
            onClick={() => dataCleaned && setActiveTab('modeling')}
          >
            <span className="nav-icon">🤖</span>
            <span>Cluster & ML</span>
          </div>

          <div 
            className={`nav-item ${activeTab === 'warnings' ? 'active' : ''} ${!dataCleaned ? 'disabled' : ''}`}
            onClick={() => dataCleaned && setActiveTab('warnings')}
          >
            <span className="nav-icon">⚠</span>
            <span>Early Warning</span>
          </div>
        </nav>

        {/* Sidebar Footer with system versions */}
        <div className="sidebar-footer">
          <p>Model Engine: Python 3.13</p>
          <p>Vite React UI 1.0</p>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="main-content">
        {activeTab === 'upload' && (
          <UploadSection 
            onUploadSuccess={handleFileUploadSuccess} 
            uploadedFile={uploadedFile}
            mapping={mapping}
            setMapping={setMapping}
            sheetName={sheetName}
            setSheetName={setSheetName}
          />
        )}

        {activeTab === 'cleaning' && uploadedFile && (
          <DataCleaning 
            uploadedFile={uploadedFile} 
            mapping={mapping} 
            sheetName={sheetName}
            weights={weights}
            setWeights={setWeights}
            cleaningResult={cleaningResult}
            setCleaningResult={setCleaningResult}
            setDataCleaned={(val) => {
              setDataCleaned(val);
              checkDbStatus(); // reload status
            }}
            dataCleaned={dataCleaned}
            passingThreshold={passingThreshold}
            setPassingThreshold={setPassingThreshold}
          />
        )}

        {activeTab === 'database' && (
          <DatabaseExplorer dbStatus={dbStatus} checkDbStatus={checkDbStatus} />
        )}

        {activeTab === 'statistics' && dataCleaned && (
          <StatisticalEDA dbStatus={dbStatus} passingThreshold={passingThreshold} />
        )}

        {activeTab === 'modeling' && dataCleaned && (
          <ModelTrainer dbStatus={dbStatus} />
        )}

        {activeTab === 'warnings' && dataCleaned && (
          <EarlyWarning dbStatus={dbStatus} />
        )}
      </main>
    </div>
  );
}

export default App;
