import React from 'react';
import moment from 'moment';
import PropTypes from 'prop-types';
import { Button, DataTable } from '@openedx/paragon';

const getReadableTime = (timestamp) => moment(timestamp).fromNow(true);

const WaitingStepList = ({
  studentList,
  refreshData,
  findLearner,
  selectableLearnersEnabled,
}) => {
  const studentListWithTimeAgo = studentList.map((item) => ({
    ...item,
    created_at: getReadableTime(item.created_at),
  }));

  const RefreshAction = () => (
    <Button onClick={() => refreshData()}>{gettext('Refresh')}</Button>
  );

  const reviewLearnerAction = (learnerUsername) => {
    findLearner(learnerUsername);
  };

  return (
    <DataTable
      itemCount={studentListWithTimeAgo.length}
      data={studentListWithTimeAgo}
      isSelectable={selectableLearnersEnabled}
      maxSelectedRows={1}
      additionalColumns={
        selectableLearnersEnabled
          ? [
            {
              id: 'action',
              Header: gettext('Action'),
              // eslint-disable-next-line react/prop-types
              Cell: ({ row: { isSelected, original: { username: learnerUsername } } }) => (isSelected ? (
                <Button
                  variant="link"
                  size="sm"
                  data-testid="review-learner-button"
                  onClick={() => reviewLearnerAction(learnerUsername)}
                >
                  {gettext('Review')}
                </Button>
              ) : null),
            },
          ]
          : []
      }
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
      tableActions={[<RefreshAction />]}
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
  findLearner: PropTypes.func,
  selectableLearnersEnabled: PropTypes.bool,
};

WaitingStepList.defaultProps = {
  refreshData: () => ({}),
  findLearner: () => ({}),
  selectableLearnersEnabled: false,
};

export default WaitingStepList;
