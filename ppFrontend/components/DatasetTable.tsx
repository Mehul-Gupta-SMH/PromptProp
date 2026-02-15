
import React, { useRef } from 'react';
import { DatasetRow } from '../types';

interface DatasetTableProps {
  data: DatasetRow[];
  setData: (data: DatasetRow[]) => void;
}

const DatasetTable: React.FC<DatasetTableProps> = ({ data, setData }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addRow = () => {
    const newRow: DatasetRow = {
      id: Math.random().toString(36).substr(2, 9),
      query: '',
      expectedOutput: '',
      softNegatives: '',
      hardNegatives: ''
    };
    setData([...data, newRow]);
  };

  const updateRow = (id: string, field: keyof DatasetRow, value: string) => {
    setData(data.map(row => (row.id === id ? { ...row, [field]: value } : row)));
  };

  const removeRow = (id: string) => {
    setData(data.filter(row => row.id !== id));
  };

  const handleCsvUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split('\n');
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      
      const newRows: DatasetRow[] = lines.slice(1).filter(l => l.trim()).map(line => {
        const values = line.split(',');
        const row: any = { id: Math.random().toString(36).substr(2, 9) };
        headers.forEach((header, i) => {
          if (header.includes('query')) row.query = values[i];
          if (header.includes('expected') || header.includes('output')) row.expectedOutput = values[i];
          if (header.includes('soft')) row.softNegatives = values[i];
          if (header.includes('hard')) row.hardNegatives = values[i];
        });
        return row as DatasetRow;
      });

      setData([...data, ...newRows]);
    };
    reader.readAsText(file);
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-blue-400">Ground Truth Dataset</h2>
          <p className="text-xs text-gray-500 mt-1 uppercase tracking-wider">Test cases for prompt validation</p>
        </div>
        <div className="flex gap-2">
          <input 
            type="file" 
            accept=".csv" 
            ref={fileInputRef} 
            onChange={handleCsvUpload} 
            className="hidden" 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Import CSV
          </button>
          <button
            onClick={addRow}
            className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Add Case
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="py-3 px-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest w-1/4">User Query</th>
              <th className="py-3 px-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest w-1/4">Expected Output</th>
              <th className="py-3 px-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest w-1/4">Soft Negatives</th>
              <th className="py-3 px-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest w-1/4">Hard Negatives</th>
              <th className="py-3 px-4 w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {data.map((row) => (
              <tr key={row.id} className="group hover:bg-gray-750 transition-colors">
                <td className="py-2 px-2 align-top">
                  <textarea
                    value={row.query}
                    onChange={(e) => updateRow(row.id, 'query', e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[80px]"
                    placeholder="Input query..."
                  />
                </td>
                <td className="py-2 px-2 align-top">
                  <textarea
                    value={row.expectedOutput}
                    onChange={(e) => updateRow(row.id, 'expectedOutput', e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[80px]"
                    placeholder="Desired answer..."
                  />
                </td>
                <td className="py-2 px-2 align-top">
                  <textarea
                    value={row.softNegatives}
                    onChange={(e) => updateRow(row.id, 'softNegatives', e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[80px]"
                    placeholder="Bad style..."
                  />
                </td>
                <td className="py-2 px-2 align-top">
                  <textarea
                    value={row.hardNegatives}
                    onChange={(e) => updateRow(row.id, 'hardNegatives', e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[80px]"
                    placeholder="Critical errors..."
                  />
                </td>
                <td className="py-2 px-2 align-top pt-4">
                  <button
                    onClick={() => removeRow(row.id)}
                    className="text-gray-600 hover:text-red-500 transition-colors p-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 && (
          <div className="text-center py-12 text-gray-600 italic">
            Dataset is empty. Add rows manually or import a CSV.
          </div>
        )}
      </div>
    </div>
  );
};

export default DatasetTable;
