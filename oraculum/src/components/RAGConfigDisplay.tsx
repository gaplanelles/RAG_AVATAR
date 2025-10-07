import React from 'react';
import '../styles/RAGConfigDisplay.css';

interface Metadata {
  labels?: {
    EN?: {
      [key: string]: string;
    };
  };
  config?: {
    [section: string]: {
      [key: string]: any;
      dependencies?: {
        [value: string]: any;
      };
    };
  };
}

interface RAGConfigDisplayProps {
  configData?: { [section: string]: { [key: string]: any } }| null;
  metadata?: Metadata| null;
  error?: string | null;
}

function RAGConfigDisplay({ configData, metadata, error }: RAGConfigDisplayProps) {
  const getLabel = (section:any, key?:any) => {
    if (metadata && metadata.labels && metadata.labels.EN) {
      return (
        metadata.labels.EN[`${section}.${key}`] ||
        metadata.labels.EN[section] ||
        metadata.labels.EN[key] ||
        key
      );
    }
    return key;
  };

  const shouldDisplayField = (section:any, key:any) => {
    if (!metadata || !metadata.config || !configData) return true;

    const sectionConfig = metadata.config[section];
    if (!sectionConfig) return true;

    // Always display top-level fields
    if (sectionConfig[key]) return true;

    // Check if this is a nested field
    for (const [topKey, topOptions] of Object.entries(sectionConfig)) {
      if (topOptions.dependencies) {
        const topValue = configData[section][topKey];
        const dependentFields = topOptions.dependencies[topValue];
        if (Array.isArray(dependentFields) && dependentFields.includes(key)) {
          return true;
        }
        // Add this check for object-type dependencies
        if (typeof dependentFields === 'object' && dependentFields[key]) {
          return true;
        }
      }
    }

    return false;
  };

  if (error) {
    return <div className="rag-config-error">{error}</div>;
  }

  if (!configData || !metadata) {
    return <div className="rag-config-loading">Loading RAG Configuration...</div>;
  }

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <div className="rag-config-display">
        <h2>RAG Configuration</h2>
        {Object.entries(configData).map(([section, fields]) => (
          <div key={section} className="config-section">
            <h3>{getLabel(section)}</h3>
            {Object.entries(fields).map(([key, value]) => {
              if (!shouldDisplayField(section, key)) {
                return null;
              }

              return (
                <div key={key} className="config-field">
                  <span className="field-label">{getLabel(section, key)}:</span>
                  <span className="field-value">
                    {value !== null && value !== undefined
                      ? typeof value === 'object'
                        ? JSON.stringify(value)
                        : value.toString()
                      : 'N/A'}
                  </span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default RAGConfigDisplay;
