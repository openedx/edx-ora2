import React, { useState, useEffect } from 'react';
import { IntlProvider } from 'react-intl';
import PropTypes from 'prop-types';
import {
  Alert, Container, Row, Spinner,
} from '@openedx/paragon';
import { fetchWaitingStepDetails } from '../api/waiting_step_details';
import WaitingStepContent from '../components/WaitingStepContent';

const WaitingStepDetailsContainer = ({
  waitingStepDataUrl,
  onMount,
  selectableLearnersEnabled,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [waitingStepDetails, setWaitingStepDetails] = useState({
    display_name: '',
    must_be_graded_by: '',
    must_grade: '',
    student_data: [],
  });

  const updateData = async () => {
    // Clear error and display loading component
    setLoading(true);
    setError(false);

    // Make request using API
    try {
      const { success, waitingStepData } = await fetchWaitingStepDetails(
        waitingStepDataUrl,
      );

      // Check response and save contents on state
      if (success) {
        setWaitingStepDetails(waitingStepData);
      } else {
        setError(true);
      }
    } catch (err) {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const getUsernameSelected = (username) => {
    const button = document.querySelector('.button-staff-tools');
    if (button) {
      if (
        !button.classList.contains('is--active')
        && button.getAttribute('aria-expanded') === 'false'
      ) {
        button.click();
      }

      const inputUsername = document.querySelector(
        '.openassessment__student_username.value',
      );
      const submitButtonUsername = document.querySelector(
        '.action--submit-username',
      );

      if (inputUsername && submitButtonUsername) {
        inputUsername.value = username;
        submitButtonUsername.click();
      }
    }
  };

  useEffect(() => {
    // Callback onMount
    onMount();

    // Fetch waiting step data from API
    updateData();
  }, []);

  return (
    // Using en locale for now until we have translations. This is a temporary solution
    // for paragon version 20+. https://github.com/openedx/paragon/releases/tag/v20.0.0
    <IntlProvider locale="en">
      <div className="paragon-styles">
        <div className="mt-3 mb-1">
          {/* Displayed when loading */}
          {loading && (
            <Container className="my-3">
              <Row className="justify-content-md-center">
                <Spinner animation="border" variant="primary" />
              </Row>
            </Container>
          )}

          {/* Displayed after waiting step details are retrieved */}
          {!loading && !error && (
            <WaitingStepContent
              waitingStepDetails={waitingStepDetails}
              refreshData={updateData}
              findLearner={getUsernameSelected}
              selectableLearnersEnabled={selectableLearnersEnabled}
            />
          )}

          {/* Displayed if there's any issue with the request */}
          {error && (
            <Alert variant="danger">
              {gettext('Error while fetching student data.')}
            </Alert>
          )}

          <div className="waiting-details-staff-area mt-n4">
            <div className="openassessment__staff-area" />
          </div>
        </div>
      </div>
    </IntlProvider>
  );
};

WaitingStepDetailsContainer.propTypes = {
  waitingStepDataUrl: PropTypes.string.isRequired,
  onMount: PropTypes.func,
  selectableLearnersEnabled: PropTypes.bool,
};

WaitingStepDetailsContainer.defaultProps = {
  onMount: () => ({}),
  selectableLearnersEnabled: false,
};

export default WaitingStepDetailsContainer;
