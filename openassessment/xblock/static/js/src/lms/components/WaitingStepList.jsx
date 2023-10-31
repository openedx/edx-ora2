import React from 'react';
import moment from 'moment';
import PropTypes from 'prop-types';
import { Button, DataTable } from '@openedx/paragon';

const getReadableTime = (timestamp) => moment(timestamp).fromNow(true);

const WaitingStepList = ({ studentList, refreshData }) => {
  const studentListWithTimeAgo = studentList.map((item) => ({
    ...item,
    created_at: getReadableTime(item.created_at),
  }));

  const RefreshAction = () => (
    <Button onClick={() => refreshData()}>{gettext('Refresh')}</Button>
  );

  return (
    <DataTable
      itemCount={studentListWithTimeAgo.length}
      data={studentListWithTimeAgo}
      columns={[
        {
          Header: gettext('Username'),
          accessor: 'username',

        },
        {
          Header: gettext('Peers Assessed'),
          accessor: 'graded',
        },
        {
          Header: gettext('Peer Responses Received'),
          accessor: 'graded_by',
        },
        {
          Header: gettext('Time Spent On Current Step'),
          accessor: 'created_at',
        },
        {
          Header: gettext('Staff assessment'),
          accessor: 'staff_grade_status',
        },
        {
          Header: gettext('Grade Status'),
          accessor: 'workflow_status',
        },
      ]}
      tableActions={[
        <RefreshAction />,
      ]}
    >
      <DataTable.TableControlBar />
      <DataTable.Table />
      <DataTable.TableFooter />
    </DataTable>
  );
};

WaitingStepList.propTypes = {
  studentList: PropTypes.arrayOf(PropTypes.object).isRequired,
  refreshData: PropTypes.func,
};

WaitingStepList.defaultProps = {
  refreshData: () => ({}),
};

export default WaitingStepList;
