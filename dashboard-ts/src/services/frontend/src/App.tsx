
import React, { useState } from 'react';
import './App.css';


type Contact = { Name: string; Email: string; Phone: string };
type Opportunity = { Opportunity: string; Value: number; Stage: string };
type Pipeline = { Pipeline: string; Status: string };
type Summary = { Metric: string; Value: number };

type TabData = {
  Contacts: Contact[];
  Opportunities: Opportunity[];
  Pipelines: Pipeline[];
  Summary: Summary[];
};

// initial placeholder data; opportunities will be replaced with real API results
const sampleData: TabData = {
  Contacts: [
    { Name: 'Alice', Email: 'alice@example.com', Phone: '123-456-7890' },
    { Name: 'Bob', Email: 'bob@example.com', Phone: '987-654-3210' },
  ],
  Opportunities: [], // start empty, we'll fetch real values
  Pipelines: [],
  Summary: [],
};

const tabNames = Object.keys(sampleData) as (keyof TabData)[];

function arrayToCSV(data: Record<string, unknown>[]): string {
  if (!data.length) return '';
  const headers = Object.keys(data[0]);
  const csvRows = [headers.join(',')];
  for (const row of data) {
    csvRows.push(headers.map(h => JSON.stringify(row[h] ?? '')).join(','));
  }
  return csvRows.join('\r\n');
}

function downloadCSV(data: Record<string, unknown>[], filename: string): void {
  const csv = arrayToCSV(data);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}


function App() {
  const [activeTab, setActiveTab] = useState<keyof TabData>(tabNames[0]);
  const [fetched, setFetched] = useState(false);
  const [data, setData] = useState<Record<string, unknown>[]>(sampleData[activeTab]);

  // when activeTab switches to Opportunities load from backend once
  React.useEffect(() => {
    if (activeTab === 'Opportunities' && !fetched) {
      fetch('/api/opportunities')
        .then(res => res.json())
        .then(json => {
          if (json.success && Array.isArray(json.data)) {
            // convert each deal object into displayable row
            const rows = json.data.map((d: any, idx: number) => ({
              'S No.': idx + 1,
              Name: d.name,
              Amount: d.amount,
              Stage: d.stage_name || (d.deal_stage_id ? String(d.deal_stage_id) : 'Unknown'),
              Owner: d.owner_name || (d.owner_id ? String(d.owner_id) : 'N/A'),
              Reference: d.id,
              Created: d.created_at,
            }));
            setData(rows);
          }
        })
        .catch(err => console.error('Error fetching opportunities', err));
      setFetched(true);
    }
    // when switching tabs, update data to the appropriate sample/default
    if (activeTab !== 'Opportunities') {
      setData(sampleData[activeTab]);
    }
  }, [activeTab, fetched]);

  // use the current data for rendering

  return (
    <div className="App">
      <h1>CRM Dashboard</h1>
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center' }}>
        {tabNames.map((tab) => (
          <React.Fragment key={tab}>
            <button
              onClick={() => setActiveTab(tab)}
              style={{
                fontWeight: activeTab === tab ? 'bold' : 'normal',
                marginRight: 10,
                padding: '8px 16px',
                borderRadius: 4,
                border: activeTab === tab ? '2px solid #007bff' : '1px solid #ccc',
                background: activeTab === tab ? '#e6f0ff' : '#fff',
                cursor: 'pointer',
              }}
            >
              {tab}
            </button>
            {tab === 'Contacts' && activeTab === 'Contacts' && (
              <button
                onClick={() => downloadCSV(data, 'Contacts.csv')}
                style={{
                  padding: '8px 16px',
                  borderRadius: 4,
                  background: '#28a745',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  marginRight: 20
                }}
              >
                Download CSV
              </button>
            )}
          </React.Fragment>
        ))}
      </div>
      <table style={{ margin: '0 auto', borderCollapse: 'collapse', minWidth: 300 }}>
        <thead>
          <tr>
            {data.length > 0 && Object.keys(data[0]).map((header: string) => (
              <th key={header} style={{ border: '1px solid #ccc', padding: 8, background: '#f8f9fa' }}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row: Record<string, unknown>, i: number) => (
            <tr key={i}>
              {Object.values(row).map((val: unknown, j: number) => (
                <td key={j} style={{ border: '1px solid #ccc', padding: 8 }}>{String(val)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
