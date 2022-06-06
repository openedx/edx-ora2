import React from 'react';
import { DataTable } from '@edx/paragon';

export const InstructorDashboard = ({ ora_items, ora_item_view_enabled }) => {
  const items = JSON.parse(ora_items);

  debugger;
  return (
    <DataTable
      isSelectable
      columns={[
        {
          accessor: 'parent_name',
          Header: gettext('Unit Name'),
        },
        {
          accessor: 'name',
          Header: gettext('Assessment'),
        },
        {
          accessor: 'total',
          Header: gettext('Total Responses'),
        },
        {
          accessor: 'training',
          Header: gettext('Training'),
        },
        {
          accessor: 'peer',
          Header: gettext('Peer'),
        },
        {
          accessor: 'self',
          Header: gettext('Self'),
        },
        {
          accessor: 'waiting',
          Header: gettext('Waiting'),
        },
        {
          accessor: 'staff',
          Header: gettext('Staff'),
        },
        {
          accessor: 'done',
          Header: gettext('Final Grade Received'),
        },
        {
          accessor: 'staff_grader',
          Header: gettext('Staff Grader'),
        },
        // {
        //   Header: 'Name',
        //   accessor: 'name',
        // },
        // {
        //   Header: 'Age',
        //   accessor: 'age',
        // },
        // {
        //   Header: 'Famous For',
        //   accessor: 'famous_for',
        // },
        // {
        //   Header: 'Coat Color',
        //   accessor: 'color',
        // },
      ]}
      // columns={items.map(item => ({
      //   Header: ''
      // }))}
      itemCount={items.length}
      data={items}
      // additionalColumns={[
      //   {
      //     id: 'action',
      //     Header: 'Action',
      //     // Proptypes disabled as this prop is passed in separately
      //     Cell: ({ row }) => (
      //       <Button variant='link' onClick={() => console.log('Assign', row)}>
      //         Assign
      //       </Button>
      //     ),
      //   },
      // ]}
    >
      <DataTable.TableControlBar />
      <DataTable.Table />
      <DataTable.EmptyTable content='No results found' />
      <DataTable.TableFooter />
    </DataTable>
  );

  // return (<pre>
  //   {
  //     JSON.stringify(items, null, 2)
  //   }
  // </pre>)
};

export default InstructorDashboard;

window.ora = window.ora || {};
window.ora.InstructorDashboard = InstructorDashboard;
