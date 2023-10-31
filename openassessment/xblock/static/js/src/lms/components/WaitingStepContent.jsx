import React from 'react';
import PropTypes from 'prop-types';
import { Alert } from '@openedx/paragon';
import WaitingStepList from './WaitingStepList';

const WaitingStepContent = ({ waitingStepDetails, refreshData }) => {
  const oraDescriptionText = gettext(
    'The "{name}" problem is configured to require a minimum of {min_grades} '
    + 'peer grades, and asks to review {min_graded} peers.',
  ).replace(
    '{name}', waitingStepDetails.display_name,
  ).replace(
    '{min_grades}', waitingStepDetails.must_be_graded_by,
  ).replace(
    '{min_graded}', waitingStepDetails.must_grade,
  );

  const stuckLearnersText = gettext(
    'There are currently {stuck_learners} learners in the waiting state, '
    + 'meaning they have not yet met all requirements for Peer Assessment. ',
  ).replace(
    '{stuck_learners}',
    waitingStepDetails.waiting_count + waitingStepDetails.overwritten_count,
  );

  const overwrittenLearnersText = gettext(
    'However, {overwritten_count} of these students have received a grade '
    + 'through the staff grade override tool already.',
  ).replace(
    '{overwritten_count}',
    waitingStepDetails.overwritten_count,
  );

  return (
    <div>
      <p>
        {oraDescriptionText}
      </p>

      <Alert variant="info" className="mx-0">
        <p className="mb-0">
          {stuckLearnersText}
          {waitingStepDetails.overwritten_count !== 0 && overwrittenLearnersText}
        </p>
      </Alert>

      <WaitingStepList
        studentList={waitingStepDetails.student_data}
        refreshData={refreshData}
      />
    </div>
  );
};

WaitingStepContent.propTypes = {
  waitingStepDetails: PropTypes.shape({
    display_name: PropTypes.string,
    must_be_graded_by: PropTypes.string,
    must_grade: PropTypes.string,
    waiting_count: PropTypes.string,
    overwritten_count: PropTypes.string,
    student_data: PropTypes.arrayOf(PropTypes.object),
  }).isRequired,
  refreshData: PropTypes.func,
};

WaitingStepContent.defaultProps = {
  refreshData: () => ({}),
};

export default WaitingStepContent;
