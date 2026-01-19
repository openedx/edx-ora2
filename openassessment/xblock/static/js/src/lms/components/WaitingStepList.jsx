import React, { useMemo, useCallback } from 'react';
import moment from 'moment';
import PropTypes from 'prop-types';
import { Button, DataTable } from '@openedx/paragon';

const getReadableTime = (timestamp) => moment(timestamp).fromNow(true);

const RefreshAction = ({ refreshData }) => (
  <Button onClick={() => refreshData()}>{gettext('Refresh')}</Button>
);

RefreshAction.propTypes = {
  refreshData: PropTypes.func.isRequired,
};

const ActionCell = ({ row, reviewLearnerAction }) => {
  const { isSelected, original: { username: learnerUsername } } = row;
  return isSelected ? (
    <Button
      variant="link"
      size="sm"
      data-testid="review-learner-button"
      onClick={() => reviewLearnerAction(learnerUsername)}
    >
      {gettext('Review')}
    </Button>
  ) : null;
};

ActionCell.propTypes = {
  row: PropTypes.shape({
    isSelected: PropTypes.bool.isRequired,
    original: PropTypes.shape({
      username: PropTypes.string.isRequired,
    }).isRequired,
  }).isRequired,
  reviewLearnerAction: PropTypes.func.isRequired,
};

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

  const reviewLearnerAction = useCallback((learnerUsername) => {
    findLearner(learnerUsername);
  }, [findLearner]);

  const additionalColumns = useMemo(() => (
    selectableLearnersEnabled
      ? [
        {
          id: 'action',
          Header: gettext('Action'),
          // eslint-disable-next-line react/no-unstable-nested-components
          Cell: (props) => <ActionCell {...props} reviewLearnerAction={reviewLearnerAction} />,
        },
      ]
      : []
  ), [selectableLearnersEnabled, reviewLearnerAction]);

  return (
    <DataTable
      itemCount={studentListWithTimeAgo.length}
      data={studentListWithTimeAgo}
      isSelectable={selectableLearnersEnabled}
      maxSelectedRows={1}
      additionalColumns={additionalColumns}
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
      tableActions={[<RefreshAction refreshData={refreshData} />]}
    >
      <DataTable.TableControlBar />
      <DataTable.Table />
      <DataTable.TableFooter />
    </DataTable>
  );
};

WaitingStepList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
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
