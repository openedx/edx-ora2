import React, { useContext, useEffect } from 'react';
import PropTypes from 'prop-types';

import { DataTable } from '@edx/paragon';
import SummaryGrid from './summary_grid';
import AssessmentCell from './cells/assessment_cell';
import { OAListingContext } from '../../oa_listing_provider';
import WaitingCell from './cells/waiting_cell';
import StaffCell from './cells/staff_cell';
import EsgCell from './cells/esg_cell';

function ListingTable() {
  const { refreshGrid, oraData, showOraBlock } = useContext(OAListingContext);

  useEffect(() => refreshGrid(), []);

  if (showOraBlock) {
    return null;
  }

  return (
    <div id="listing-table">
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
            Cell: AssessmentCell,
          },
          {
            Header: 'Total Responses',
            accessor: 'total',
            num: true,
          },
          {
            Header: 'Training',
            accessor: 'training',
            num: true,
          },
          {
            Header: 'Peer',
            accessor: 'peer',
            num: true,
          },
          {
            Header: 'Self',
            accessor: 'self',
            num: true,
          },
          {
            Header: 'Waiting',
            accessor: 'waiting',
            num: true,
            Cell: WaitingCell,
          },
          {
            Header: 'Staff',
            accessor: 'staff',
            num: true,
            Cell: StaffCell,
          },
          {
            Header: 'Final Grade Received',
            accessor: 'done',
            num: true,
          },
          {
            Header: 'Staff Grader',
            accessor: 'staff_grader',
            hideSummary: true,
            Cell: EsgCell,
          },
        ]}
      >
        <SummaryGrid />
        <hr />
        <DataTable.Table />
        <DataTable.EmptyTable content="No results found" />
        <DataTable.TableFooter />
      </DataTable>
    </div>
  );
}

ListingTable.propTypes = {};

export default ListingTable;
