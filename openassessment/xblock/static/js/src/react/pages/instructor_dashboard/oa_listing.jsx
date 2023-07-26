import React, { useContext } from 'react';

import { DataTable } from '@edx/paragon';
import { OraContext } from '../../ora_provider';
import SummaryGrid from './components/summary_grid';

function OAListing(props) {
  const { ora_item_view_enabled: oraItemViewEnabled, ora_items: oraItems } =
    props;
  const oraData = JSON.parse(oraItems);

  const { runtime, data } = useContext(OraContext);
  console.log(data)
  const esgEnabled = data.context?.ENHANCED_STAFF_GRADER;
  const esgRootUrl = data.context?.ORA_GRADING_MICROFRONTEND_URL;

  return (
    <>
      <DataTable
        isPaginated
        initialState={{
          pageSize: 10,
        }}
        isFilterable
        isSortable
        itemCount={oraData.length}
        data={oraData}
        columns={[
          {
            Header: 'Unit Name',
            accessor: 'parent_name',
          },
          {
            Header: 'Assessment',
            accessor: 'name',
            Cell: ({ row, column }) => {
              const record = row.original;
              const url = record.url_base;
              const value = record[column.id];
              if (oraItemViewEnabled) {
                return <a href={url}>{value}</a>
              }
              return <span>{value}</span>
            }
          },
          {
            Header: 'Total Responses',
            accessor: 'total_responses',
            num: true,
          },
          {
            Header: 'Training',
            accessor: 'training',
            num: true
          },
          {
            Header: 'Peer',
            accessor: 'peer',
            num: true
          },
          {
            Header: 'Self',
            accessor: 'self',
            num: true
          },
          {
            Header: 'Waiting',
            accessor: 'waiting',
            num: true,
            Cell: ({ row, column }) => {
              const record = row.original;
              const url = record.url_base;
              const value = record[column.id];
              const hasAssessmentType = record['peer_assessment'];
              if (oraItemViewEnabled && hasAssessmentType) {
                return <a href={url}>{value}</a>
              }
              return <span>{value}</span>
            }
          },
          {
            Header: 'Staff',
            accessor: 'staff',
            num: true,
            Cell: ({ row, column }) => {
              const record = row.original;
              const url = record.url_base;
              const value = record[column.id];
              const hasAssessmentType = record['staff_assessment'];
              const shouldShowLink = record['team_assignment'] || !esgEnabled;
              if (oraItemViewEnabled && hasAssessmentType && shouldShowLink) {
                return <a href={url}>{value}</a>
              }
              return <span>{value}</span>
            }
          },
          {
            Header: 'Final Grade Received',
            accessor: 'done',
            num: true
          },
          {
            Header: 'Staff Grader',
            accessor: 'staff_grader',
            hideSummary: true,
          }
        ]}
      >
        {/* <DataTable.TableControlBar /> */}
        <SummaryGrid />
        <DataTable.Table />
        <DataTable.EmptyTable content='No results found' />
        <DataTable.TableFooter />
      </DataTable>
    </>
  );
}

export default OAListing;
