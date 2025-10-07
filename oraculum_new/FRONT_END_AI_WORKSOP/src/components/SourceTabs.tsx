import React, { useState } from 'react';
import '../styles/SourceTabs.css';

interface Source {
  id: string;
  distance: number;
  metadata: Record<string, any>;
  document: string;
}

interface SourceTabsProps {
  sources: Source[];
}

const SourceTabs: React.FC<SourceTabsProps> = ({ sources }) => {
  // console.log("SourceTabs received sources:", sources);
  const [activeTab, setActiveTab] = useState(0);

  if (!sources || sources.length === 0) {
    // console.log("No sources available in SourceTabs");
    return <div className="no-sources">No sources available</div>;
  }

  return (
    <div className="source-tabs">
      <div className="tab-headers">
        {sources.map((source:any, index:number) => (
          <button
            key={source.id}
            className={`tab-header ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            Document {index + 1}
          </button>
        ))}
      </div>
      <div className="tab-content">
        <h4>ID: {sources[activeTab].id}</h4>
        <p>Distance: {sources[activeTab].distance}</p>
        <h5>Metadata:</h5>
        <pre>{JSON.stringify(sources[activeTab].metadata, null, 2)}</pre>
        <h5>Document:</h5>
        <p>{sources[activeTab].document}</p>
      </div>
    </div>
  );
};

export default SourceTabs;
