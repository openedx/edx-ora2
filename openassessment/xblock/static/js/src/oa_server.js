/**
 * Encapsulate interactions with OpenAssessment XBlock handlers.
 */

const jsonContentType = 'application/json; charset=utf-8';

export class Server {
  /**
   * Interface for server-side XBlock handlers.
   *
   * @param {runtime} runtime - An XBlock runtime instance.
   * @param {element} element - The DOM element representing this XBlock.
   * @constructor
   */
  constructor(runtime, element) {
    this.runtime = runtime;
    this.element = element;

    this.url = this.url.bind(this);
    this.render = this.render.bind(this);
    this.renderLatex = this.renderLatex.bind(this);
    this.renderContinuedPeer = this.renderContinuedPeer.bind(this);
    this.studentInfo = this.studentInfo.bind(this);
    this.staffGradeForm = this.staffGradeForm.bind(this);
    this.staffGradeCounts = this.staffGradeCounts.bind(this);
    this.submit = this.submit.bind(this);
    this.save = this.save.bind(this);
    this.submitFeedbackOnAssessment = this.submitFeedbackOnAssessment.bind(this);
    this.submitAssessment = this.submitAssessment.bind(this);
    this.peerAssess = this.peerAssess.bind(this);
    this.selfAssess = this.selfAssess.bind(this);
    this.staffAssess = this.staffAssess.bind(this);
    this.trainingAssess = this.trainingAssess.bind(this);
    this.scheduleTraining = this.scheduleTraining.bind(this);
    this.rescheduleUnfinishedTasks = this.rescheduleUnfinishedTasks.bind(this);
    this.updateEditorContext = this.updateEditorContext.bind(this);
    this.checkReleased = this.checkReleased.bind(this);
    this.getUploadUrl = this.getUploadUrl.bind(this);
    this.removeUploadedFile = this.removeUploadedFile.bind(this);
    this.saveFilesDescriptions = this.saveFilesDescriptions.bind(this);
    this.getDownloadUrl = this.getDownloadUrl.bind(this);
    this.cancelSubmission = this.cancelSubmission.bind(this);
    this.publishEvent = this.publishEvent.bind(this);
    this.getTeamDetail = this.getTeamDetail.bind(this);
    this.listTeams = this.listTeams.bind(this);
    this.getUsername = this.getUsername.bind(this);
  }

  /**
   * Returns the URL for the handler, specific to one instance of the XBlock on the page.
   *
   * @param {string} handler The name of the XBlock handler.
   * @returns {*} The URL for the handler.
   */
  url(handler) {
    return this.runtime.handlerUrl(this.element, handler);
  }

  /**
   * Render the XBlock.
   *
   * @param {string} component The component to render.
   * @returns {*} A JQuery promise, which resolves with the HTML of the rendered XBlock
   *     and fails with an error message.
   */
  render(component) {
    const view = this;
    const url = this.url(`render_${component}`);
    return $.Deferred((defer) => {
      $.ajax({
        url,
        type: 'POST',
        dataType: 'html',
      }).done((data) => {
        defer.resolveWith(view, [data]);
      }).fail(() => {
        defer.rejectWith(view, [gettext('This section could not be loaded.')]);
      });
    }).promise();
  }

  /**
   * Render Latex for all new DOM elements with class 'allow--latex'.
   *
   * @param {element} element - The element to modify.
   */
  renderLatex(element) {
    element.filter('.allow--latex').each(function () {
      MathJax.Hub.Queue(['Typeset', MathJax.Hub, this]);
    });
  }

  /**
   * Render the Peer Assessment Section after a complete workflow, in order to
   * continue grading peers.
   *
   * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered peer
   *     assessment section or fails with an error message.
   */
  renderContinuedPeer() {
    const view = this;
    const url = this.url('render_peer_assessment');

    return $.Deferred((defer) => {
      $.ajax({
        url,
        type: 'POST',
        dataType: 'html',
        data: { continue_grading: true },
      }).done((data) => {
        defer.resolveWith(view, [data]);
      }).fail(() => {
        defer.rejectWith(view, [gettext('This section could not be loaded.')]);
      });
    }).promise();
  }

  /**
   * Load the student information section inside the Staff Info section.
   *
   * @param {string} studentUsername - The username for the student.
   * @param {object} options - An optional set of configuration options.
   * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered section
   *     fails with an error message.
   */
  studentInfo(studentUsername, options) {
    const url = this.url('render_student_info');
    return $.Deferred((defer) => {
      $.ajax({
        url,
        type: 'POST',
        dataType: 'html',
        data: _.extend({ student_username: studentUsername }, options),
      }).done(function (data) {
        defer.resolveWith(this, [data]);
      }).fail(function () {
        defer.rejectWith(this, [gettext('This section could not be loaded.')]);
      });
    }).promise();
  }

  /**
   * Renders the next submission for staff grading.
   *
   * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered section
   *     fails with an error message.
   */
  staffGradeForm() {
    const url = this.url('render_staff_grade_form');
    return $.Deferred((defer) => {
      $.ajax({
        url,
        type: 'POST',
        dataType: 'html',
      }).done(function (data) {
        defer.resolveWith(this, [data]);
      }).fail(function () {
        defer.rejectWith(this, [gettext('The staff assessment form could not be loaded.')]);
      });
    }).promise();
  }

  /**
   * Renders the count of ungraded and checked out assessemtns.
   *
   * @returns {promise} A JQuery promise, which resolves with the HTML of the rendered section
   *     fails with an error message.
   */
  staffGradeCounts() {
    const url = this.url('render_staff_grade_counts');
    return $.Deferred((defer) => {
      $.ajax({
        url,
        type: 'POST',
        dataType: 'html',
      }).done(function (data) {
        defer.resolveWith(this, [data]);
      }).fail(function () {
        defer.rejectWith(
          this, [gettext('The display of ungraded and checked out responses could not be loaded.')],
        );
      });
    }).promise();
  }

  /**
   * Send a submission to the XBlock.
   *
   * @param {string} submission The text of the student's submission.
   * @returns {promise} A JQuery promise, which resolves with the student's ID
   * and attempt number if the call was successful and fails with a status code
   * and error message otherwise.
   */
  submit(submission) {
    const url = this.url('submit');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST',
        url,
        data: JSON.stringify({ submission }),
        contentType: jsonContentType,
      }).done(function (data) {
        const success = data[0];
        if (success) {
          const studentId = data[1];
          const attemptNum = data[2];
          defer.resolveWith(this, [studentId, attemptNum]);
        } else {
          const errorNum = data[1];
          const errorMsg = data[2];
          defer.rejectWith(this, [errorNum, errorMsg]);
        }
      }).fail(function () {
        defer.rejectWith(this, ['AJAX', gettext('This response could not be submitted.')]);
      });
    }).promise();
  }

  /**
   * Save a response without submitting it.
   *
   * @param {string} submission The text of the student's response.
   * @returns {promise} A JQuery promise, which resolves with no arguments on success and
   *      fails with an error message.
   */
  save(submission) {
    const url = this.url('save_submission');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST',
        url,
        data: JSON.stringify({ submission }),
        contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('This response could not be saved.')]);
      });
    }).promise();
  }

  /**
   * Submit feedback on assessments to the XBlock.
   *
   * @param {string} text written feedback from the student.
   * @param {Array.string} options one or more options the student selected.
   * @returns {promise} A JQuery promise, which resolves with no args if successful and
   *     fails with an error message otherwise.
   */
  submitFeedbackOnAssessment(text, options) {
    const url = this.url('submit_feedback');
    const payload = JSON.stringify({
      feedback_text: text,
      feedback_options: options,
    });
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: payload, contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('This feedback could not be submitted.')]);
      });
    }).promise();
  }

  /**
   * Submits an assessment.
   *
   * @param {string} assessmentType - The type of assessment.
   * @param {object} payload - The assessment payload
   * @returns {promise} A promise which resolves with no arguments if successful,
   *     and which fails with an error message otherwise.
   */
  submitAssessment(assessmentType, payload) {
    const url = this.url(assessmentType);
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: JSON.stringify(payload), contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) {
          defer.resolve();
        } else {
          defer.rejectWith(this, [data.msg]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
      });
    }).promise();
  }

  /**
   * Send a peer assessment to the XBlock.
   *
   * @param {object} optionsSelected - The options selected as a dict,
   *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
   * @param {object} criterionFeedback - Feedback on the criterion,
   *     e.g. { clarity: "The essay was very clear." }
   * @param {string} overallFeedback - A string with the staff member's overall feedback.
   * @param {string} submissionID - The ID of the submission being assessed.
   * @returns {promise} A promise which resolves with no arguments if successful,
   *     and which fails with an error message otherwise.
   */
  peerAssess(optionsSelected, criterionFeedback, overallFeedback, submissionID) {
    return this.submitAssessment('peer_assess', {
      options_selected: optionsSelected,
      criterion_feedback: criterionFeedback,
      overall_feedback: overallFeedback,
      submission_uuid: submissionID,
    });
  }

  /**
   * Send a self assessment to the XBlock.
   *
   * @param {object} optionsSelected - The options selected as a dict,
   *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
   * @param {object} criterionFeedback - Feedback on the criterion,
   *     e.g. { clarity: "The essay was very clear." }
   * @param {string} overallFeedback - A string with the staff member's overall feedback.
   * @returns {promise} A promise which resolves with no arguments if successful,
   *     and which fails with an error message otherwise.
   */
  selfAssess(optionsSelected, criterionFeedback, overallFeedback) {
    return this.submitAssessment('self_assess', {
      options_selected: optionsSelected,
      criterion_feedback: criterionFeedback,
      overall_feedback: overallFeedback,
    });
  }

  /**
   * Send a staff assessment to the XBlock.
   *
   * @param {object} optionsSelected - The options selected as a dict,
   *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
   * @param {object} criterionFeedback - Feedback on the criterion,
   *     e.g. { clarity: "The essay was very clear." }
   * @param {string} overallFeedback - A string with the staff member's overall feedback.
   * @param {string} submissionID - The ID of the submission being assessed.
   * @param {string} assessType a string indicating whether this was a 'full-grade' or 'regrade'
   * @returns {promise} A promise which resolves with no arguments if successful,
   *     and which fails with an error message otherwise.
   */
  staffAssess(optionsSelected, criterionFeedback, overallFeedback, submissionID, assessType) {
    return this.submitAssessment('staff_assess', {
      options_selected: optionsSelected,
      criterion_feedback: criterionFeedback,
      overall_feedback: overallFeedback,
      submission_uuid: submissionID,
      assess_type: assessType,
    });
  }

  /**
   * Submit an instructor-provided training example.
   *
   * @param {object} optionsSelected - The options selected as a dict,
   *     e.g. { clarity: "Very clear", precision: "Somewhat precise" }
   * @returns {promise} A promise which resolves with a list of corrections if successful,
   *     and which fails with an error message otherwise.
   */
  trainingAssess(optionsSelected) {
    const url = this.url('training_assess');
    const payload = JSON.stringify({
      options_selected: optionsSelected,
    });
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: payload, contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) {
          defer.resolveWith(this, [data.corrections]);
        } else {
          defer.rejectWith(this, [data.msg]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
      });
    });
  }

  /**
   * Schedules classifier training for Example Based Assessments.
   *
   * @returns {promise} A JQuery promise, which resolves with a
   * message indicating the results of the scheduling request.
   */
  scheduleTraining() {
    const url = this.url('schedule_training');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: '""', contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) {
          defer.resolveWith(this, [data.msg]);
        } else {
          defer.rejectWith(this, [data.msg]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('This assessment could not be submitted.')]);
      });
    });
  }

  /**
   * Reschedules grading tasks for example based assessments
   *
   * @returns {promise} a JQuery Promise which will resolve with a message indicating
   *     success or failure of the scheduling.
   */
  rescheduleUnfinishedTasks() {
    const url = this.url('reschedule_unfinished_tasks');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: '""', contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) {
          defer.resolveWith(this, [data.msg]);
        } else {
          defer.rejectWith(this, [data.msg]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('One or more rescheduling tasks failed.')]);
      });
    });
  }

  /**
   * Update the XBlock's XML definition on the server.
   *
   * @param {object} options - An object with the following options:
   *     title (string): The title of the problem.
   *     prompt (string): The question prompt.
   *     feedbackPrompt (string): The directions to the student for giving overall feedback on a submission.
   *     feedback_default_text (string): The default feedback text used as the student's feedback response
   *     submissionStart (ISO-formatted datetime string or null): The start date of the submission.
   *     submissionDue (ISO-formatted datetime string or null): The date the submission is due.
   *     criteria (list of object literals): The rubric criteria.
   *     assessments (list of object literals): The assessments the student will be evaluated on.
   *     fileUploadType (string): 'image' if image attachments are allowed, 'pdf-and-image' if pdf and
   *     image attachments are allowed, 'custom' if file type is restricted by a white list.
   *     fileTypeWhiteList (string): Comma separated file type white list
   *     latexEnabled: TRUE if latex rendering is enabled.
   *     leaderboardNum (int): The number of scores to show in the leaderboard.
   *     teamsEnabled: TRUE if teams are enabled.
   *     teamset (string): The name of the selected teamset.
   *
   * @returns {promise} A JQuery promise, which resolves with no arguments
   *     and fails with an error message.
   */
  updateEditorContext(options) {
    const url = this.url('update_editor_context');
    const payload = JSON.stringify({
      prompts: options.prompts,
      prompts_type: options.prompts_type,
      feedback_prompt: options.feedbackPrompt,
      feedback_default_text: options.feedback_default_text,
      title: options.title,
      submission_start: options.submissionStart,
      submission_due: options.submissionDue,
      criteria: options.criteria,
      assessments: options.assessments,
      editor_assessments_order: options.editorAssessmentsOrder,
      text_response: options.textResponse,
      text_response_editor: options.textResponseEditor,
      file_upload_response: options.fileUploadResponse,
      file_upload_type: options.fileUploadType,
      white_listed_file_types: options.fileTypeWhiteList,
      allow_multiple_files: options.multipleFilesEnabled,
      allow_latex: options.latexEnabled,
      leaderboard_show: options.leaderboardNum,
      teams_enabled: options.teamsEnabled,
      selected_teamset_id: options.selectedTeamsetId,
      show_rubric_during_response: options.showRubricDuringResponse,
    });
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: payload, contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('This problem could not be saved.')]);
      });
    }).promise();
  }

  /**
   * Check whether the XBlock has been released.
   *
   * @returns {promise} A JQuery promise, which resolves with a boolean indicating
   *     whether the XBlock has been released.  On failure, the promise provides
   *     an error message.
   */
  checkReleased() {
    const url = this.url('check_released');
    const payload = '""';
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: payload, contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolveWith(this, [data.is_released]); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('The server could not be contacted.')]);
      });
    }).promise();
  }

  /**
   * Get an upload URL used to asynchronously post related files for the submission.
   *
   * @param {string} contentType The Content Type for the file being uploaded.
   * @param {string} filename The name of the file to be uploaded.
   * @param {string} filenum The number of the file to be uploaded.
   * @returns {promise} A promise which resolves with a presigned upload URL from the
   * specified service used for uploading files on success, or with an error message
   * upon failure.
   */
  getUploadUrl(contentType, filename, filenum) {
    const url = this.url('upload_url');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST',
        url,
        data: JSON.stringify({ contentType, filename, filenum }),
        contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(data.url); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Could not retrieve upload url.')]);
      });
    }).promise();
  }

  /**
   * Sends request to server to remove specific uploaded file.
   */
  removeUploadedFile(filenum) {
    const url = this.url('remove_uploaded_file');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST',
        url,
        data: JSON.stringify({ filenum }),
        contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Server error.')]);
      });
    }).promise();
  }

  /**
   * Sends request to server to save descriptions for each uploaded file.
   */
  saveFilesDescriptions(fileMetadata) {
    const url = this.url('save_files_descriptions');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST',
        url,
        data: JSON.stringify({ fileMetadata }),
        contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Server error.')]);
      });
    }).promise();
  }

  /**
   * Get a download url used to download related files for the submission.
   *
   * @param {string} filenum The number of the file to be downloaded.
   * @returns {promise} A promise which resolves with a temporary download URL for
   * retrieving documents from s3 on success, or with an error message upon failure.
   */
  getDownloadUrl(filenum) {
    const url = this.url('download_url');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: JSON.stringify({ filenum }), contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) { defer.resolve(data.url); } else { defer.rejectWith(this, [data.msg]); }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Could not retrieve download url.')]);
      });
    }).promise();
  }

  /**
   * Cancel a submission from the peer grading pool.
   *
   * @param {object} submissionID - The id of the submission to be canceled.
   * @param {object} comments - The reason for canceling the submission.
   * @returns {*}
   */
  cancelSubmission(submissionID, comments) {
    const url = this.url('cancel_submission');
    const payload = JSON.stringify({
      submission_uuid: submissionID,
      comments,
    });
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: payload, contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) {
          defer.resolveWith(this, [data.msg]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('The submission could not be removed from the grading pool.')]);
      });
    }).promise();
  }

  /**
   * Submit an event to the runtime for publishing.
   *
   * @param {object} eventName - the name of the event
   * @param {object} eventData - additional context data for the event
   */
  publishEvent(eventName, eventData) {
    eventData.event_name = eventName;
    const url = this.url('publish_event');
    const payload = JSON.stringify(eventData);
    $.ajax({
      type: 'POST', url, data: payload, contentType: jsonContentType,
    });
  }

  /**
   * Calls the team detail endpoint
   *
   * @param {string} teamId - the unique identifier for the team
   */
  getTeamDetail(teamId) {
    const teamsUrl = `${window.location.origin}/api/team/v0/teams/${teamId}`;
    return $.ajax({
      type: 'GET',
      url: teamsUrl,
      contentType: jsonContentType,
    });
  }

  /**
   * Calls the team listing endpoint to recieve the list of teams for this user and course
   *
   * Currently a user should only be in one team per course, so an exception is raised
   * if multiple teams are returned.
   *
   * @param {string} username - The username of the user we are looking up teams for
   * @param {string} courseId - The course id that we are looking up teams for
   */
  listTeams(username, courseId) {
    const teamsUrl = `${window.location.origin}/api/team/v0/teams/`;
    return $.Deferred((defer) => {
      $.ajax({
        type: 'GET',
        url: teamsUrl,
        data: {
          course_id: courseId,
          username,
        },
        contentType: jsonContentType,
      }).done(function (data) {
        if (data.count > 1) {
          defer.rejectWith(this, [gettext('Multiple teams returned for course')]);
        } else if (data.count === 0) {
          defer.resolveWith(this, [null]);
        } else {
          defer.resolveWith(this, [data.results[0]]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Could not load teams information.')]);
      });
    }).promise();
  }

  /**
   * Gets the current student's username.
   *
   * Returns a promise which resolves with the username,
   * or fails if there is an error or the user is not found
   */

  getUsername() {
    const url = this.url('get_student_username');
    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST',
        url,
        data: JSON.stringify({}),
        contentType: jsonContentType,
      }).done(function (data) {
        if (data.username === null) {
          defer.rejectWith(this, [gettext('User lookup failed')]);
        } else {
          defer.resolveWith(this, [data.username]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Error when looking up username')]);
      });
    });
  }

  /**
   * Clone a rubric into ORA from an existing rubric
   * @param {xblock-id} rubricLocation, xblock locator for ORA to clone rubric from
   * @returns {promise} a JQuery Promise which will resolve with rubric data
   */
  cloneRubric(rubricLocation) {
    const url = this.url('get_rubric');
    const payload = { target_rubric_block_id: String(rubricLocation) };

    return $.Deferred((defer) => {
      $.ajax({
        type: 'POST', url, data: JSON.stringify(payload), contentType: jsonContentType,
      }).done(function (data) {
        if (data.success) {
          defer.resolveWith(this, [data.rubric]);
        } else {
          defer.rejectWith(this, [data.msg]);
        }
      }).fail(function () {
        defer.rejectWith(this, [gettext('Failed to clone rubric')]);
      });
    });
  }
}

export default Server;
