import React, { useEffect } from 'react';
import PropTypes from 'prop-types';

export const OABase = ({
  title,
  rubricAssessments,
  showStaffArea,
  prompts,
  promptsType,
  prevOra,
}) => {
  useEffect(() => {
    const { runtime, element, prevOraSupport } = prevOra;
    const { prev_ora_function: prevOraFunction, data } = prevOraSupport;
    if (window[prevOraFunction]) {
      window[prevOraFunction](runtime, element, {
        ...data,
        prompts,
        prompts_type: promptsType,
      });
    }
  }, []);
  return (
    <div className="wrapper wrapper--xblock wrapper--openassessment theme--basic">
      <div className="openassessment problem">
        <div className="wrapper--grid">
          {title ? (
            <h3 className="openassessment__title problem__header">
              {gettext(title)}
            </h3>
          ) : null}

          <div className="wrapper-openassessment__message">
            <div className="openassessment__message message">
              <div className="message__content">
                <p>
                  {gettext(
                    "This assignment has several steps. In the first step, you'll provide a response to the prompt. The other steps appear below the Your Response field.",
                  )}
                </p>
              </div>
            </div>
          </div>

          <ol className="openassessment__steps">
            {rubricAssessments.map((assessment) => (
              <li
                key={assessment.classId}
                className={`${assessment.classId} openassessment__steps__step is--loading`}
              >
                <header className="step__header ui-slidable__container">
                  <h4 className="step__title">
                    <button
                      type="button"
                      className="ui-slidable"
                      aria-expanded="false"
                      aria-describedby="oa_step_status oa_step_deadline"
                      disabled
                    >
                      <span className="step__counter" />
                      <span className="wrapper--copy">
                        <span className="step__label">
                          {gettext(assessment.title)}
                        </span>
                      </span>
                    </button>
                  </h4>
                  <span className="step__status">
                    <span id="oa_step_status" className="step__status__value">
                      <span
                        className="icon fa fa-spinner fa-spin"
                        aria-hidden="true"
                      />
                      <span className="copy">{gettext('Loading')}</span>
                    </span>
                  </span>
                </header>
              </li>
            ))}
          </ol>
          {showStaffArea ? (
            <div className="openassessment__staff-area" />
          ) : null}
        </div>
      </div>
      <div className="sr reader-feedback" aria-live="polite" />
    </div>
  );
};

export const PrevOraProp = PropTypes.shape({
  runtime: PropTypes.any,
  element: PropTypes.any,
  prevOraSupport: PropTypes.shape({
    prev_ora_function: PropTypes.string,
    data: PropTypes.any,
  }),
});

OABase.propTypes = {
  title: PropTypes.string,
  showStaffArea: PropTypes.bool,
  rubricAssessments: PropTypes.arrayOf(PropTypes.any),
  prompts: PropTypes.arrayOf(PropTypes.any),
  promptsType: PropTypes.string,
  prevOra: PrevOraProp.isRequired,
};

OABase.defaultProps = {
  title: null,
  showStaffArea: false,
  rubricAssessments: [],
  prompts: [],
  promptsType: [],
};

export default OABase;
