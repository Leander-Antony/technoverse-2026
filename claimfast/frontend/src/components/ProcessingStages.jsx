import React from 'react';
import '../styles/ProcessingStages.css';

function ProcessingStages({ currentStage, progressPercentage }) {
  const stages = [
    { id: 1, name: 'FNOL Intake', icon: '📋', progress: 15 },
    { id: 2, name: 'Damage Assessment', icon: '🔍', progress: 30 },
    { id: 3, name: 'Policy Evaluation', icon: '📋', progress: 45 },
    { id: 4, name: 'Fraud Detection', icon: '🔐', progress: 60 },
    { id: 5, name: 'Decision Making', icon: '⚖️', progress: 75 },
    { id: 6, name: 'Explainability', icon: '📄', progress: 100 },
  ];

  const getCurrentStageIndex = () => {
    return stages.findIndex(stage => stage.name === currentStage);
  };

  const currentIndex = getCurrentStageIndex();

  return (
    <div className="processing-stages">
      <h3>Processing Pipeline</h3>
      <div className="stages-timeline">
        {stages.map((stage, idx) => {
          const isCompleted = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const isPending = idx > currentIndex;

          return (
            <React.Fragment key={stage.id}>
              <div
                className={`stage ${isCompleted ? 'completed' : ''} ${
                  isCurrent ? 'current' : ''
                } ${isPending ? 'pending' : ''}`}
              >
                <div className="stage-circle">
                  <span className="stage-number">{stage.icon}</span>
                </div>
                <div className="stage-label">{stage.name}</div>
              </div>
              {idx < stages.length - 1 && (
                <div
                  className={`stage-connector ${
                    isCompleted || isCurrent ? 'active' : ''
                  }`}
                ></div>
              )}
            </React.Fragment>
          );
        })}
      </div>
      <div className="stages-info">
        <p>
          <span className="stage-status current">●</span> Current Stage
          <span className="stage-status completed">●</span> Completed
          <span className="stage-status pending">●</span> Pending
        </p>
      </div>
    </div>
  );
}

export default ProcessingStages;
