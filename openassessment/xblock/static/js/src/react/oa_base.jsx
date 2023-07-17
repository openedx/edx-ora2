import React from 'react';

import { Button } from '@edx/paragon';
import { useIntl } from 'react-intl';

function OABase(props) {
  const { title, rubric_assessments, show_staff_area } = props;
  const { formatDate } = useIntl();
  React.useEffect(() => {
    // Callback onMount
    props.onMount();
  }, []);
  return (
    <div className='wrapper wrapper--xblock wrapper--openassessment theme--basic'>
      <div className='openassessment problem'>
        <div className='wrapper--grid'>
            {title && <h3 className='openassessment__title problem__header'>{title}</h3>}
            <h1>{formatDate(new Date())}</h1>
            <Button>Test</Button>
            <div className="wrapper-openassessment__message">
              <div className="openassessment__message message">
                    <div className="message__content">
                        <p>This assignment has several steps. In the first step, you'll provide a response to the prompt. The other steps appear below the Your Response field.</p>
                    </div>
                </div>
            </div>

            <ol className="openassessment__steps">
                {
                    rubric_assessments.map((assessment, index) => (
                        <li key={`assessment-${index}`} className={`${assessment.class_id} openassessment__steps__step is--loading`}>
                        <header className="step__header ui-slidable__container">
                            <h4 className="step__title">
                                <button className="ui-slidable" aria-expanded="false" aria-describedby="oa_step_status oa_step_deadline" disabled>
                                    <span className="step__counter"></span>
                                    <span className="wrapper--copy">
                                        <span className="step__label">{assessment.title}</span>
                                    </span>
                                </button>
                            </h4>
                            <span className="step__status">
                                <span id="oa_step_status" className="step__status__value">
                                  <span className="icon fa fa-spinner fa-spin" aria-hidden="true"></span>
                                  <span className="copy">Loading</span>
                                </span>
                            </span>
                        </header>
                    </li>
                    ))
                }
                    
            </ol>

            {show_staff_area && <div className="openassessment__staff-area"></div>}
        </div>
      </div>
    </div>
  );
}

export default OABase;
