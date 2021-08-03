/**
Editing interface for OpenAssessment assessments steps.

Args:
    element (DOM element): The DOM element representing this view.
    assessmentViews (object literal): Mapping of CSS IDs to view objects.

Returns:
    OpenAssessment.EditAssessmentsStepsView

* */
export class EditAssessmentsStepsView {
  constructor(element, assessmentViews) {
    this.assessmentsElement = $(element).siblings('#openassessment_assessment_module_settings_editors').get(0);
    this.tabElement = $('#oa_edit_assessment_steps_tab');
    this.assessmentViews = assessmentViews;

    this.initializeSortableAssessments();
  }

  getTab() {
    return this.tabElement;
  }

  /**
    Installs click listeners which initialize drag and drop functionality for assessment modules.
    * */
  initializeSortableAssessments() {
    const view = this;
    // Initialize Drag and Drop of Assessment Modules
    $('#openassessment_assessment_module_settings_editors', view.element).sortable({
      // On Start, we want to collapse all draggable items so that dragging is visually simple (no scrolling)
      start(event, ui) {
        // Hide all of the contents (not the headers) of the divs, to collapse during dragging.
        $('.openassessment_assessment_module_editor', view.element).hide();

        // Because of the way that JQuery actively resizes elements during dragging (directly setting
        // the style property), the only way to over come it is to use an important tag ( :( ), or
        // to tell JQuery to set the height to be Automatic (i.e. resize to the minimum nescesary size.)
        // Because all of the information we don't want displayed is now hidden, an auto height will
        // perform the apparent "collapse" that we are looking for in the Placeholder and Helper.
        const targetHeight = 'auto';
        // Shrink the blank area behind the dragged item.
        ui.placeholder.height(targetHeight);
        // Shrink the dragged item itself.
        ui.helper.height(targetHeight);
        // Update the sortable to reflect these changes.
        $('#openassessment_assessment_module_settings_editors', view.element)
          .sortable('refresh').sortable('refreshPositions');
      },
      // On stop, we redisplay the divs to their original state
      stop() {
        $('.openassessment_assessment_module_editor', view.element).show();
      },
      snap: true,
      axis: 'y',
      handle: '.drag-handle',
      cursorAt: { top: 20 },
    });
    $('#openassessment_assessment_module_settings_editors .drag-handle', view.element).disableSelection();
  }

  /**
     * Check whether elements are hidden.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to check.
     * @return {boolean} - True if all the elements are hidden, else false.
     */
  isHidden(selector) {
    return selector.hasClass('is--hidden') && selector.attr('aria-hidden') === 'true';
  }

  /**
     * Hide elements, including setting the aria-hidden attribute for screen readers.
     *
     * @param {JQuery.selector} selector - The selector matching the elements to hide.
     * @param {boolean} hidden - Whether to hide or show the elements.
     */
  setHidden(selector, hidden) {
    selector.toggleClass('is--hidden', hidden);
    selector.attr('aria-hidden', hidden ? 'true' : 'false');
  }

  /**
    Construct a list of enabled assessments and their properties.

    Returns:
        list of object literals representing the assessments.

    Example usage:
    >>> editSettingsView.assessmentsDescription()
    [
        {
            name: "peer-assessment",
            start: "2014-04-01T00:00",
            due: null
            must_grade: 5,
            must_be_graded_by: 2,
        }
        {
            name: "self-assessment",
            start: null,
            due: null
        }
    ]
    * */
  assessmentsDescription() {
    const assessmentDescList = [];
    const view = this;

    // Find all assessment modules within our element in the DOM,
    // and append their definitions to the description
    $('.openassessment_assessment_module_settings_editor', this.assessmentsElement).each(
      function () {
        const asmntView = view.assessmentViews[$(this).attr('id')];
        const isVisible = !view.isHidden($(asmntView.element));

        if (asmntView.isEnabled() && isVisible) {
          const description = asmntView.description();
          description.name = asmntView.name;
          assessmentDescList.push(description);
        }
      },
    );
    return assessmentDescList;
  }

  /**
    Retrieve the names of all assessments in the editor,
    in the order that the user defined,
    including assessments that are not currently active.

    Returns:
        list of strings

    * */
  editorAssessmentsOrder() {
    const editorAssessments = [];
    const view = this;
    $('.openassessment_assessment_module_settings_editor', this.assessmentsElement).each(
      function () {
        const asmntView = view.assessmentViews[$(this).attr('id')];
        editorAssessments.push(asmntView.name);
      },
    );
    return editorAssessments;
  }

  /**
    Mark validation errors.

    Returns:
        Boolean indicating whether the view is valid.

    * */
  validate() {
    // Validate the start and due datetime controls
    let isValid = true;

    // Validate each of the *enabled* assessment views
    $.each(this.assessmentViews, function () {
      if (this.isEnabled()) {
        isValid = (this.validate() && isValid);
      }
    });

    return isValid;
  }

  /**
    Return a list of validation errors visible in the UI.
    Mainly useful for testing.

    Returns:
        list of string

    * */
  validationErrors() {
    let errors = [];

    $.each(this.assessmentViews, function () {
      errors = errors.concat(this.validationErrors());
    });

    return errors;
  }

  /**
    Clear all validation errors from the UI.
    * */
  clearValidationErrors() {
    $.each(this.assessmentViews, function () {
      this.clearValidationErrors();
    });
  }
}

export default EditAssessmentsStepsView;
