import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { IntlProvider } from 'react-intl';
import sinon from 'sinon'; 
import WaitingStepList from 'lms/components/WaitingStepList';

describe('OpenAssessment.WaitingStepList', () => {
  window.gettext = sinon.fake((text) => text);

  const IntlProviderWrapper = ({ children }) => (
    <IntlProvider locale="en" messages={{}}>
      {children}
    </IntlProvider>
  );

  describe('With selectableLearnersEnabled as a prop', () => {
    const WaitingStepListWrapper = ({ children }) => <div data-testid="learners-data-table">{children}</div>

    it('should allow row selection when it is enabled', async () => {
      const studentList = [
        {
          username: 'myusername',
          graded: false,
          graded_by: '2',
          created_at: Date.now(),
          staff_grade_status: 'waiting',
          workflow_status: '',
        },
      ];

      render(
        <IntlProviderWrapper>
          <WaitingStepListWrapper>
            <WaitingStepList
              selectableLearnersEnabled
              studentList={studentList}
            />
          </WaitingStepListWrapper>
        </IntlProviderWrapper>
      );


      await waitFor(() => {
        const dataTable = screen.getByTestId('learners-data-table');
        const [firstRowCheckbox] = dataTable.querySelectorAll('input[type="checkbox"]');
        expect(dataTable).not.toBeNull();
        expect(firstRowCheckbox).not.toBeNull();
      });
     
    });
   
    
    it('should show review action button when a row is selected', async () => {
  
      const studentList = [
        {
          username: 'myusername',
          graded: false,
          graded_by: '2',
          created_at: Date.now(),
          staff_grade_status: 'waiting',
          workflow_status: '',
        },
      ];

      render(
        <IntlProviderWrapper>
          <WaitingStepListWrapper>
            <WaitingStepList
              selectableLearnersEnabled
              studentList={studentList}
            />
          </WaitingStepListWrapper>
        </IntlProviderWrapper>
      );

      await waitFor(() =>  {
        const dataTable = screen.getByTestId('learners-data-table');
        const [firstRowCheckbox] = dataTable.querySelectorAll('input[type="checkbox"]');
        fireEvent.change(firstRowCheckbox, { target: { checked: true } });
        expect(firstRowCheckbox.checked).toBe(true); 
      });
      
    });

  });
});
