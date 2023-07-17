import { DataTableContext, Stack } from '@edx/paragon';
import React, { useContext, useEffect, useState } from 'react';

function SummaryGrid() {
  const { columns, data } = useContext(DataTableContext);
  const [summaryState, setSummaryState] = useState([]);

  useEffect(() => {
    const summaries = [];
    const summaryMap = {};
    for (let i = 0; i < columns.length; i++) {
      const column = columns[i];
      if (!column.hideSummary) {
        const summary = {
          title: column.Header,
          value: 0,
          num: column.num,
        };
        summaries.push(summary);
        summaryMap[column.id] = summary;
      }
    }

    for (let i = 0; i < data.length; i++) {
      const record = data[i];
      Object.keys(record).forEach(key => {
        if (summaryMap[key]) {
          summaryMap[key].value += summaryMap[key].num ? record[key] : 1;
        }
      });
    }

    setSummaryState(summaries);
  }, []);

  return (
    <Stack direction="horizontal" gap={3} className="my-3">
      {summaryState.map((summary) => (
        <div key={summary.title}>
          <div className="h4 text-info">{summary.title}</div>
          <div className="lead text-center">{summary.value}</div>
        </div>
      ))}
    </Stack>
  );
}

export default SummaryGrid;
