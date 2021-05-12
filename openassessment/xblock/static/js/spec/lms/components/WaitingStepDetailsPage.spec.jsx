import React from 'react';
import fetchMock from 'fetch-mock';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import WaitingStepDetailsContainer from 'lms/containers/WaitingStepDetailsContainer';

describe('OpenAssessment.WaitingStepDetailsPage', () => {
  beforeEach(() => {
    fetchMock.get(
      '*',
      {
        display_name: 'ORA_PROBLEM_DISPLAY_NAME',
        must_be_graded_by: '2',
        must_grade: '3',
        student_data: [],
      },
    );
  });

  afterEach(() => {
    fetchMock.restore();
  });

  it('verify it renders correctly', async () => {
    // Render component
    render(<WaitingStepDetailsContainer waitingStepDataUrl="http://example.com" />);

    // Assert that the API was called
    fetchMock.called();

    // Waiting until the `Refresh` button shows up in the UI
    await waitFor(() => screen.getByText('Refresh'));

    // Check that the request data was correctly rendered.
    expect(screen.getByText(
      'The "ORA_PROBLEM_DISPLAY_NAME" problem is configured to require a minimum of 2 peer grades, and asks to review 3 peers.',
    ));
  });

  it('check that the refresh button calls the api', async () => {
    // Render component
    render(<WaitingStepDetailsContainer waitingStepDataUrl="http://example.com" />);

    // Waiting until the `Refresh` button shows up in the UI and click it
    await waitFor(() => screen.getByText('Refresh'));
    fireEvent.click(screen.getByText('Refresh'));

    // Check that the API was called twice (once on initial render and
    // once when clicking `Refresh`).
    const apiCalls = fetchMock.calls();
    expect(apiCalls.length).toBe(2);
  });
});
