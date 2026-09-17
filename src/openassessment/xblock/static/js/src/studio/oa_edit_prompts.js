import Container from './oa_container';
import { Prompt } from './oa_container_item';

/**
 Editing interface for the prompts.

 Args:
 element (DOM element): The DOM element representing this view.

 Returns:
 OpenAssessment.EditPromptsView

 * */
export class EditPromptsView {
  constructor(element, notifier) {
    this.element = element;
    this.editorElement = $(this.element).closest('#openassessment-editor');
    this.tabElement = $('#oa_edit_prompt_tab');

    this.addRemoveEnabled = this.editorElement.attr('data-is-released') !== 'true';

    this.promptsContainer = new Container(
      Prompt, {
        containerElement: $('#openassessment_prompts_list', this.element).get(0),
        templateElement: $('#openassessment_prompt_template', this.element).get(0),
        addButtonElement: $('#openassessment_prompts_add_prompt', this.element).get(0),
        removeButtonClass: 'openassessment_prompt_remove_button',
        containerItemClass: 'openassessment_prompt',
        notifier,
        addRemoveEnabled: this.addRemoveEnabled,
      },
    );
    this.promptsContainer.addEventListeners();
  }

  getTab() {
    return this.tabElement;
  }

  /**
     Construct a list of prompts definitions from the editor UI.

     Returns:
     list of prompt objects

     Example usage:
     >>> editPromptsView.promptsDefinition();
     [
     {
         uuid: "cfvgbh657",
         description: "Description",
         order_num: 0,
     }
     ...
     ]

     * */
  promptsDefinition() {
    const prompts = this.promptsContainer.getItemValues();
    return prompts;
  }

  /**
     Get available prompts mode. In case if tinyMCE is enabled is is "html" mode
     Otherwise it is 'text' mode.

     Returns:
     string: "html" or "text"
     * */
  promptsType() {
    const firstPrompt = this.promptsContainer.getItem(0);
    return (firstPrompt && firstPrompt.tinyMCEEnabled) ? 'html' : 'text';
  }

  /**
     Add a new prompt.
     Uses a client-side template to create the new prompt.
     * */
  addPrompt() {
    if (this.addRemoveEnabled) {
      this.promptsContainer.add();
    }
  }

  /**
     Remove a prompt.

     Args:
     item (OpenAssessment.RubricCriterion): The criterion item to remove.
     * */
  removePrompt(item) {
    if (this.addRemoveEnabled) {
      this.promptsContainer.remove(item);
    }
  }

  /**
     Retrieve all prompts.

     Returns:
     Array of OpenAssessment.Prompt objects.

     * */
  getAllPrompts() {
    return this.promptsContainer.getAllItems();
  }

  /**
     Retrieve a prompt item from the prompts.

     Args:
     index (int): The index of the prompt, starting from 0.

     Returns:
     OpenAssessment.Prompt or null

     * */
  getPromptItem(index) {
    return this.promptsContainer.getItem(index);
  }

  /**
     Mark validation errors.

     Returns:
     Boolean indicating whether the view is valid.

     * */
  validate() {
    return true;
  }

  /**
     Return a list of validation errors visible in the UI.
     Mainly useful for testing.

     Returns:
     list of string

     * */
  validationErrors() {
    const errors = [];
    return errors;
  }

  /**
     Clear all validation errors from the UI.
     * */
  clearValidationErrors() {}
}

export default EditPromptsView;
