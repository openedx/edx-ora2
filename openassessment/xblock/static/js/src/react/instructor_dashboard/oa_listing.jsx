import React from 'react';

import { DataTable } from '@edx/paragon';

function OAListing(props) {
  const { ora_item_view_enabled: oraItemViewEnabled, ora_items: oraItems } =
    props;
  const oraData = JSON.parse(oraItems);
  return (
    <>
      <DataTable
        isPaginated
        isSelectable
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
          },
          {
            Header: 'Total Responses',
            accessor: 'total_responses',
          },
          {
            Header: 'Training',
            accessor: 'training',
          },
          {
            Header: 'Peer',
            accessor: 'peer',
          },
          {
            Header: 'Self',
            accessor: 'self',
          },
          {
            Header: 'Waiting',
            accessor: 'waiting',
          },
          {
            Header: 'Staff',
            accessor: 'staff',
          },
          {
            Header: 'Done',
            accessor: 'done',
          },
          {
            Header: 'Staff Grader',
            accessor: 'staff_grader',
          }
        ]}
      >
        {/* <DataTable.TableControlBar /> */}
        <DataTable.Table />
        <DataTable.EmptyTable content='No results found' />
        <DataTable.TableFooter />
      </DataTable>
    </>
  );
}

export default OAListing;
