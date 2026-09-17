import React from 'react';
import ReactDOM from 'react-dom';
import WaitingStepDetailsContainer from './containers/WaitingStepDetailsContainer';

/**
 * Function to render the Waiting Step Details view.
 *
 * Args:
 *   baseView (OpenAssessment.BaseView): Container view. Used to render
 *             staff assessment views to manage grades.
 *   data (OpenAssessment.Server): Context data passed from view.
 */
export function renderWaitingStepDetailsView(baseView, data) {
  // Retrieves react container on instructor dashboard
  const reactElement = document.getElementById('openassessment__waiting-step-details');

  // Waiting step details API URL
  const waitingStepDataUrl = data.CONTEXT.waiting_step_data_url;
  // Enabled learners selectabled
  const waitingStepSelectableLearners = data.CONTEXT.selectable_learners_enabled;

  // Callback function to render staff area once component loads
  const loadStaffArea = () => {
    // After React components are rendered, retrieve the `staff-area`
    // element and render the ORA Staff area on it.
    // To avoid modifying code internals and tangling the React with the
    // Backbone bits of the codebase, we're just replacing the BaseView
    // and StaffAreaView `element` with our newly created one.
    const staffAreaElement = $('.waiting-details-staff-area', reactElement);
    baseView.element = staffAreaElement;
    baseView.staffAreaView.element = staffAreaElement;
    // Load staff area view
    baseView.staffAreaView.load();
  };

  // Render react
  ReactDOM.render(
    <WaitingStepDetailsContainer
      waitingStepDataUrl={waitingStepDataUrl}
      onMount={loadStaffArea}
      selectableLearnersEnabled={waitingStepSelectableLearners}
    />,
    reactElement,
  );
}

export default renderWaitingStepDetailsView;
