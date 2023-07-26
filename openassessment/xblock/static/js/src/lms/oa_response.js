import DateTimeFactory from './oa_datefactory';
import ConfirmationAlert from './oa_confirmation_alert';
import Prompts from './oa_prompts';

/**
 Interface for response (submission) view.

 Args:
 element (DOM element): The DOM element representing the XBlock.
 server (OpenAssessment.Server): The interface to the XBlock server.
 fileUploader (OpenAssessment.FileUploader): File uploader instance.
 baseView (OpenAssessment.BaseView): Container view.
 data (Object): The data object passed from XBlock backend.

 Returns:
 OpenAssessment.ResponseView
 * */
export class ResponseView {
    // Milliseconds between checks for whether we should autosave.
    AUTO_SAVE_POLL_INTERVAL = 2000;

    // Required delay after the user changes a response or a save occurs
    // before we can autosave.
    AUTO_SAVE_WAIT = 2000;

    // Maximum size (500 * 2^20 bytes, approx. 500MB) of a single uploaded file.
    MAX_FILE_SIZE = 500 * (1024 ** 2);

    // For user-facing upload limit text.
    MAX_FILES_MB = 500;

    UNSAVED_WARNING_KEY = 'learner-response';

    ICON_SAVED = 'fa-check-circle-o';

    ICON_SAVING = 'fa-refresh';

    ICON_ERROR = 'fa-exclamation-circle';

    constructor(element, server, fileUploader, responseEditorLoader, baseView, data) {
      this.element = element;
      this.server = server;
      this.fileUploader = fileUploader;
      this.responseEditorLoader = responseEditorLoader;
      this.baseView = baseView;
      this.savedResponse = [];
      this.textResponse = 'required';
      this.textResponseEditor = 'text';
      this.fileUploadResponse = '';
      this.files = null;
      this.filesDescriptions = [];
      this.fileNames = [];
      this.filesType = null;
      this.lastChangeTime = Date.now();
      this.errorOnLastSave = false;
      this.autoSaveTimerId = null;
      this.data = data;
      this.filesUploaded = false;
      this.announceStatus = false;
      this.isRendering = false;
      this.fileCountBeforeUpload = 0;
      this.dateFactory = new DateTimeFactory(this.element);
    }

    /**
     Load the response (submission) view.
     * */
    load(usageID) {
      const view = this;
      const stepID = '.step--response';
      const focusID = `[id='oa_response_${usageID}']`;

      view.isRendering = true;
      this.server.render('submission').done(
        (html) => {
          // Load the HTML and install event handlers
          $(stepID, view.element).replaceWith(html);
          view.server.renderLatex($(stepID, view.element));
          view.setupPromptDisplays();
          // First load response editor then apply other things
          view.loadResponseEditor().then((editorController) => {
            view.responseEditorController = editorController;
            view.installHandlers();
            view.setAutoSaveEnabled(true);
            view.isRendering = false;
            view.baseView.announceStatusChangeToSRandFocus(stepID, usageID, false, view, focusID);
            view.announceStatus = false;
            view.dateFactory.apply();
          });
        },
      ).fail(() => {
        view.baseView.showLoadError('response');
      });
    }

    /**
     * Load currently selected editor.
     *
     * Returns: promise
     */
    loadResponseEditor() {
      const sel = $('.step--response', this.element);
      const editorElements = sel.find('.submission__answer__part__text__value');
      return this.responseEditorLoader.load(this.data.TEXT_RESPONSE_EDITOR, editorElements);
    }

    /**
     Install event handlers for the view.
     * */
    installHandlers() {
      const sel = $('.step--response', this.element);
      const view = this;
      let uploadType = '';
      if (sel.find('.submission__answer__display__file').length) {
        uploadType = sel.find('.submission__answer__display__file').data('upload-type');
      }
      // Install a click handler for collapse/expand
      this.baseView.setUpCollapseExpand(sel);

      // Install change handler for editor (to enable submission button)
      this.savedResponse = this.response();
      this.responseEditorController.setOnChangeListener(this.handleResponseChanged.bind(this));

      const handlePrepareUpload = function (eventData) { view.prepareUpload(eventData.target.files, uploadType); };
      sel.find('input[type=file]').on('change', handlePrepareUpload);

      const submit = $('.step--response__submit', this.element);
      this.textResponse = $(submit).attr('text_response');
      this.fileUploadResponse = $(submit).attr('file_upload_response');

      // Install a click handler for submission
      sel.find('.step--response__submit').click(
        (eventObject) => {
          // Override default form submission
          eventObject.preventDefault();
          view.handleSubmitClicked();
        },
      );

      // Install a click handler for the save button
      sel.find('.submission__save').click(
        (eventObject) => {
          // Override default form submission
          eventObject.preventDefault();
          view.save();
        },
      );

      // Install click handler for the preview button
      this.baseView.bindLatexPreview(sel);

      // Install a click handler for the save button
      sel.find('.file__upload').click(
        (eventObject) => {
          // Override default form submission
          eventObject.preventDefault();
          $('.submission__answer__display__file', view.element).removeClass('is--hidden');
          if (view.hasAllUploadFiles()) {
            view.uploadFiles();
          }
        },
      );

      // Install click handlers for delete file buttons.
      sel.find('.delete__uploaded__file').click((eventObject) => {
        eventObject.preventDefault();
        view.handleDeleteFileClick(eventObject.target);
      });

      // Install a click handler to close the text response warning
      sel.find('#team_text_response_warning_closebtn').click(
        (eventObject) => {
          eventObject.preventDefault();
          sel.find('#team_text_response_warning').remove();
        },
      );
      this.confirmationDialog = new ConfirmationAlert(sel.find('.step--response__dialog-confirm'));
    }

    /**
     Set up prompts and attempt to resolve any unresolved Studio URLs
     * */
    setupPromptDisplays() {
      this.prompts = new Prompts(this.element);
      this.prompts.resolveStaticLinks();
    }

    /**
     Enable or disable autosave polling.

     Args:
     enabled (boolean): If true, start polling for whether we need to autosave.
     Otherwise, stop polling.
     * */
    setAutoSaveEnabled(enabled) {
      if (enabled) {
        if (this.autoSaveTimerId === null) {
          this.autoSaveTimerId = setInterval(
            $.proxy(this.autoSave, this),
            this.AUTO_SAVE_POLL_INTERVAL,
          );
        }
      } else if (this.autoSaveTimerId !== null) {
        clearInterval(this.autoSaveTimerId);
      }
    }

    /**
     * Check if submission is valid before submitting
     * Returns: boolean
     */
    isValidForSubmit() {
      const textFieldsIsNotBlank = !this.response().every(
        (element) => $.trim(element) === '',
      );
      let filesFiledIsNotBlank = false;
      $('.submission__answer__file', this.element).each(function () {
        if (
          ($(this).prop('tagName') === 'IMG' && $(this).attr('src') !== '')
          || ($(this).prop('tagName') === 'A' && $(this).attr('href') !== '')
        ) {
          filesFiledIsNotBlank = true;
        }
      });
      if (this.textResponse === 'required' && !textFieldsIsNotBlank) {
        this.baseView.toggleActionError(
          'submit',
          gettext('Please provide a response.'),
        );
        return false;
      }
      if (this.fileUploadResponse === 'required' && !filesFiledIsNotBlank) {
        this.baseView.toggleActionError(
          'submit',
          gettext('Please upload a file.'),
        );
        return false;
      }
      if ((this.textResponse === 'optional') && (this.fileUploadResponse === 'optional')
            && !textFieldsIsNotBlank && !filesFiledIsNotBlank) {
        this.baseView.toggleActionError(
          'submit',
          gettext('Cannot submit empty response even everything is optional.'),
        );
        return false;
      }

      if (this.hasPendingUploadFiles()) {
        this.collectFilesDescriptions();
        this.baseView.toggleActionError(
          'submit',
          gettext(
            'There is still file upload in progress. Please wait until it is finished.',
          ),
        );
        return false;
      }

      return true;
    }

    /**
     * Check that "save" button could be enabled (or disabled)
     *
     */
    checkSaveAbility() {
      const textFieldsIsNotBlank = !this.response().every((element) => $.trim(element) === '');

      return !((this.textResponse === 'required') && !textFieldsIsNotBlank);
    }

    /**
     Enable/disable the submit button.
     Check that whether the submit button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.submitEnabled(true);  // enable the button
     >> view.submitEnabled();  // check whether the button is enabled
     >> true
     * */
    submitEnabled(enabled) {
      return this.baseView.buttonEnabled('.step--response__submit', enabled);
    }

    /**
     Enable/disable the preview button.
     Check whether the preview button is enabled.

     Args:
     enabled (bool): If specified, set the state of the button.

     Returns:
     bool: Whether the button is enabled.

     Examples:
     >> view.previewEnabled(true);  // enable the button
     >> view.previewEnabled();  // check whether the button is enabled
     >> true
    */
    previewEnabled(enabled) {
      return this.baseView.buttonEnabled('.submission__preview', enabled);
    }

    /**
      Check if there is a file selected but not uploaded yet
      Returns:
      boolean: if we have pending files or not.
     * */
    hasPendingUploadFiles() {
      return this.files !== null && !this.filesUploaded;
    }

    /**
     Check if there is a selected file moved or deleted before uploading
     Returns:
     boolean: if we have deleted/moved files or not.
     * */
    hasAllUploadFiles() {
      if (!this.files) {
        this.baseView.toggleActionError(
          'upload',
          gettext('No files selected for upload.'),
        );
        return false;
      }
      if (!this.collectFilesDescriptions()) {
        this.baseView.toggleActionError(
          'upload',
          gettext('Please provide a description for each file you are uploading.'),
        );
        return false;
      }
      for (let i = 0; i < this.files?.length; i++) {
        const file = this.files[i];
        if (file.size === 0) {
          this.baseView.toggleActionError(
            'upload',
            gettext('Your file has been deleted or path has been changed: ') + file.name,
          );
          return false;
        }
      }
      return true;
    }

    /**
     Set the save status message.
     Retrieve the save status message.

     Args:
     msg (string): If specified, the message to display.
     iconClass (str): If specified, icon to display with save status.

     Returns:
     string: The current status message.
     * */
    saveStatus(msg, iconClass) {
      // Create save status text
      const saveStatusSel = $('.save__submission__label', this.element);
      if (typeof msg === 'undefined') {
        return saveStatusSel.text();
      }
      saveStatusSel.text(_.escape(msg));

      // Update save status icon, if provided
      const iconSel = $('.save__submission__icon', this.element);
      let iconClasses = 'save__submission__icon icon fa ';
      if (typeof msg === 'string') {
        iconClasses += _.escape(iconClass);
      }
      iconSel.attr('class', iconClasses);

      return saveStatusSel.text();
    }

    /**
     Set the response texts.
     Retrieve the response texts.

     Args:
     texts (array of strings): If specified, the texts to set for the response.

     Returns:
     array of strings: The current response texts.
     * */
    /* eslint-disable-next-line consistent-return */
    response(texts) {
      return this.responseEditorController.response(texts);
    }

    /**
     Check whether the response texts have changed since the last save.

     Returns: boolean
     * */
    responseChanged() {
      const { savedResponse } = this;
      return this.response().some((element, index) => element !== savedResponse[index]);
    }

    /**
     Automatically save the user's response if certain conditions are met.

     Usually, this would be called by a timer (see `setAutoSaveEnabled()`).
     For testing purposes, it's useful to disable the timer
     and call this function synchronously.
     * */
    autoSave() {
      const timeSinceLastChange = Date.now() - this.lastChangeTime;

      // We only autosave if the following conditions are met:
      // (1) The response has changed.  We don't need to keep saving the same response.
      // (2) Sufficient time has passed since the user last made a change to the response.
      //      We don't want to save a response while the user is in the middle of typing.
      if (this.responseChanged() && timeSinceLastChange > this.AUTO_SAVE_WAIT) {
        this.save();
      }
    }

    /**
     Enable/disable the submission and save buttons based on whether
     the user has entered a response.
     * */
    handleResponseChanged() {
      // Update the save button, save status, and "unsaved changes" warning
      // only if the response has changed
      if (this.responseChanged()) {
        const saveAbility = this.checkSaveAbility();
        this.previewEnabled(saveAbility);

        // If there was an error, preserve error status
        if (!this.errorOnLastSave) {
          this.saveStatus(gettext('Saving draft'), this.ICON_SAVING);
        }

        this.baseView.unsavedWarningEnabled(
          true,
          this.UNSAVED_WARNING_KEY,
          // eslint-disable-next-line max-len
          gettext('If you leave this page without saving or submitting your response, you will lose any work you have done on the response.'),
        );
      }

      // Record the current time (used for autosave)
      this.lastChangeTime = Date.now();
    }

    /**
     Save a response without submitting it.
     * */
    save() {
      // Update the save status and error notifications
      // ... unless there was an error, this helps avoid unnecessary UI refreshes.
      if (!this.errorOnLastSave) {
        this.saveStatus(gettext('Saving draft...'), this.ICON_SAVING);
      }

      // Disable the "unsaved changes" warning
      this.baseView.unsavedWarningEnabled(false, this.UNSAVED_WARNING_KEY);

      const view = this;
      const savedResponse = this.response();

      this.server.save(savedResponse).done(() => {
        // Remember which response we saved, once the server confirms that it's been saved...
        view.savedResponse = savedResponse;

        const currentResponse = view.response();
        const currentResponseEqualsSaved = currentResponse.every((element, index) => element === savedResponse[index]);
        if (currentResponseEqualsSaved) {
          const msg = gettext('Draft saved!');
          view.saveStatus(msg, this.ICON_SAVED);
          view.baseView.srReadTexts([msg]);

          // Disable error
          this.baseView.toggleActionError('save', null);
          view.errorOnLastSave = false;
        }
      }).fail((errMsg) => {
        // Debounce error banner, this won't capture new errors, but will keep
        // us from defocusing text area, allowing user to continue to edit their
        // response.
        if (!view.errorOnLastSave) {
          view.saveStatus(gettext('Error'), this.ICON_ERROR);
          view.baseView.toggleActionError('save', errMsg);
        }

        // Remember that an error occurred
        // so we can disable autosave
        // (avoids repeatedly refreshing the error message)
        view.errorOnLastSave = true;
      });
    }

    /**
     Handler for the submit button
     * */
    handleSubmitClicked() {
      if (!this.isValidForSubmit()) { return; }

      // Immediately disable the submit button to prevent multiple submission
      this.submitEnabled(false);

      const view = this;
      const title = gettext('Confirm Submit Response');
      // Keep this on one big line to avoid gettext bug: http://stackoverflow.com/a/24579117
      // eslint-disable-next-line max-len
      const msg = gettext('You\'re about to submit your response for this assignment. After you submit this response, you can\'t change it or submit a new response.');
      this.confirmationDialog.confirm(
        title,
        msg,
        () => view.submit(),
        () => view.submitEnabled(true),
      );
    }

    /**
     Send a response submission to the server and update the view.
     * */
    submit() {
      const submission = this.response();
      this.baseView.toggleActionError('response', null);

      // Send the submission to the server
      this.server.submit(submission)
        .done(() => { this.moveToNextStep(); })
        .fail((errCode, errMsg) => {
          // If the error is "multiple submissions", then we should move to the next step.
          // Otherwise, the user will be stuck on the current step with no way to continue.
          if (errCode === 'ENOMULTI') { this.moveToNextStep(); } else {
            // If there is an error message, display it
            if (errMsg) { this.baseView.toggleActionError('submit', errMsg); }

            // Re-enable the submit button so the user can retry
            this.submitEnabled(true);
          }
        });
    }

    /**
     Transition the user to the next step in the workflow.
     * */
    moveToNextStep() {
      const { baseView } = this;
      const usageID = baseView.getUsageID();
      const view = this;

      this.load(usageID);
      baseView.loadAssessmentModules(usageID);

      view.announceStatus = true;

      // Disable the "unsaved changes" warning if the user
      // tries to navigate to another page.
      baseView.unsavedWarningEnabled(false, this.UNSAVED_WARNING_KEY);
    }

    /**
     When selecting a file for upload, do some quick client-side validation
     to ensure that it is an image, a PDF or other allowed types, and is not
     larger than the maximum file size.

     Args:
     files (list): A collection of files used for upload. This function assumes
     there is only one file being uploaded at any time. This file must
     be less than 5 MB and an image, PDF or other allowed types.
     uploadType (string): uploaded file type allowed, could be none, image,
     file or custom.

     */
    prepareUpload(files, uploadType, descriptions) {
      this.files = null;
      this.filesType = uploadType;
      this.filesUploaded = false;

      let errorCheckerTriggered = false;

      for (let i = 0; i < files.length; i++) {
        if (files[i].size > this.MAX_FILE_SIZE) {
          this.baseView.toggleActionError(
            'upload',
            gettext(
              'Individual file size must be {max_files_mb}MB or less.',
            ).replace(
              '{max_files_mb}',
              this.MAX_FILES_MB,
            ),
          );
          errorCheckerTriggered = true;
          break;
        }

        if (!this.isUploadSupported(files[i], uploadType)) {
          this.baseView.toggleActionError(
            'upload',
            gettext(
              'File upload failed: unsupported file type. '
              + 'Only the supported file types can be uploaded. '
              + 'If you have questions, please reach out to the course team.',
            ),
          );
          errorCheckerTriggered = true;
          break;
        }
      }

      if (this.getSavedFileCount(false) + files.length > this.data.MAXIMUM_FILE_UPLOAD_COUNT) {
        const msg = gettext('The maximum number files that can be saved is ') + this.data.MAXIMUM_FILE_UPLOAD_COUNT;
        this.baseView.toggleActionError(
          'upload',
          gettext(msg),
        );
        errorCheckerTriggered = true;
      }

      if (!errorCheckerTriggered) {
        this.baseView.toggleActionError('upload', null);
        if (files.length > 0) {
          this.files = files;
        }
        this.updateFilesDescriptionsFields(files, descriptions, uploadType);
      }
    }

   isUploadSupported = (file, uploadType) => {
     const ext = file.name.split('.').pop().toLowerCase();
     const fileType = file.type;

     // Check upload type/extension matches allowed types
     if (uploadType === 'image'
        && this.data.ALLOWED_IMAGE_MIME_TYPES.indexOf(fileType) === -1
     ) {
       return false;
     } if (
       uploadType === 'pdf-and-image'
        && this.data.ALLOWED_FILE_MIME_TYPES.indexOf(fileType) === -1
     ) {
       return false;
     } if (
       uploadType === 'custom'
        && this.data.FILE_TYPE_WHITE_LIST.indexOf(ext) === -1
     ) {
       return false;
     } if (this.data.FILE_EXT_BLACK_LIST.indexOf(ext) !== -1) {
       return false;
     }

     return true;
   };

   /**
     Render textarea fields to input description for each uploaded file.

     */
   /* jshint -W083 */
   updateFilesDescriptionsFields(files, descriptions, uploadType) {
     const filesDescriptions = $(this.element).find('.files__descriptions').first();
     let mainDiv = null;
     let divLabel = null;
     let divTextarea = null;
     let divImage = null;
     let img = null;
     let textarea = null;
     let descriptionsExists = true;

     this.filesDescriptions = descriptions || [];
     this.fileNames = [];

     $(filesDescriptions).show().html('');

     for (let i = 0; i < files.length; i++) {
       mainDiv = $('<div/>');

       divLabel = $('<div/>');
       divLabel.addClass('submission__file__description__label');
       divLabel.text(`${gettext('Describe ') + files[i].name} ${gettext('(required):')}`);
       divLabel.appendTo(mainDiv);

       divTextarea = $('<div/>');
       divTextarea.addClass('submission__file__description');
       textarea = $('<textarea />', {
         'aria-label': gettext('Describe ') + files[i].name,
       });
       if ((this.filesDescriptions.indexOf(i) !== -1) && (this.filesDescriptions[i] !== '')) {
         textarea.val(this.filesDescriptions[i]);
       } else {
         descriptionsExists = false;
       }
       textarea.addClass(`file__description file__description__${i}`);
       textarea.appendTo(divTextarea);

       if (uploadType === 'image') {
         img = $('<img/>', {
           src: window.URL.createObjectURL(files[i]),
           height: 80,
           alt: gettext('Thumbnail view of ') + files[i].name,
         });
         img.onload = function () {
           window.URL.revokeObjectURL(this.src);
         };

         divImage = $('<div/>');
         divImage.addClass('submission__img__preview');
         img.appendTo(divImage);
         divImage.appendTo(mainDiv);
       }

       divTextarea.appendTo(mainDiv);

       mainDiv.appendTo(filesDescriptions);
     }
   }

   /**
     * Called when user updates a file description field:
     * Check that file descriptions exist for all to-be-uploaded files and enable/disable upload button
     * If successful (each file has a non-empty description), save file descriptions to page state
     *
     * @returns {boolean} true if file descriptions were found for each upload (passes validation)
     * or false in the event of an error
     */
   collectFilesDescriptions() {
     let isError = false;
     const filesDescriptions = [];

     $(this.element).find('.file__description').each(function () {
       const filesDescriptionVal = $.trim($(this).val());
       if (filesDescriptionVal) {
         filesDescriptions.push(filesDescriptionVal);
       } else {
         isError = true;
       }
     });

     if (!isError) {
       this.filesDescriptions = filesDescriptions;
     }

     return !isError;
   }

   /**
     Clear field with files descriptions.

     */
   removeFilesDescriptions() {
     const filesDescriptions = $(this.element).find('.files__descriptions').first();
     $(filesDescriptions).hide().html('');
   }

   /**
     Returns the number of file blocks rendered on the page. includeDeleted is necessary in
     order to get the count of all files (even deleted ones) since our url logic is based on an index that
     is always incrementing. When includeDeleted is false - returns only the  count of files that are "live".
     */
   getSavedFileCount(includeDeleted) {
     // There may be multiple ORA blocks in a single vertical/page.
     // Find the content element of THIS ORA block, and then the
     // file submission elements therein.
     if (includeDeleted) {
       return $(this.baseView.element).find('.submission__answer__file__block').length;
     }
     return $(this.baseView.element).find('.submission__answer__file__block').filter(':parent').length;
   }

   /**
    * Handler for file delete button
    */
   handleDeleteFileClick(target) {
     const view = this;
     const filenum = $(target).attr('filenum');
     this.confirmationDialog.confirm(
       gettext('Confirm Delete Uploaded File'),
       this.getConfirmRemoveUploadedFileMessage(filenum),
       () => view.removeUploadedFile(filenum),
       () => {},
     );
   }

   /**
     Remove a previously uploaded file.
     */
   removeUploadedFile(filenum) {
     this.server.removeUploadedFile(filenum).done(() => {
       const sel = $('.step--response', this.element);
       const block = sel.find(`.submission__answer__file__block__${filenum}`);
       block.html('');
       block.prop('deleted', true);
     }).fail((errMsg) => {
       this.baseView.toggleActionError('delete', errMsg);
     });
   }

   /**
   * Build the confirm delete message for a file
   */
   getConfirmRemoveUploadedFileMessage(filenum) {
     let msg = gettext('Are you sure you want to delete the following file? It cannot be restored.\nFile: ');
     msg += this.getFileNameAndDescription(filenum);
     return msg;
   }

   /**
     * Given a filenum, look up the block for that filenum and return the text displayed
     * '<file_description> (<filename>)'
     */
   getFileNameAndDescription(filenum) {
     const fileBlock = $(this.baseView.element).find(`.submission__answer__file__block__${filenum} > a`);
     if (fileBlock.length) {
       return fileBlock[0].text.trim();
     }
     return '';
   }

   /**
     Sends request to server to save all file descriptions.

     */
   saveFilesDescriptions() {
     const view = this;
     const sel = $('.step--response', this.element);
     const fileMetaData = [];
     for (let i = 0; i < this.filesDescriptions.length; i++) {
       this.fileNames.push(this.files[i].name);
       const entry = {
         description: this.filesDescriptions[i],
         fileName: this.files[i].name,
         fileSize: this.files[i].size,
       };
       fileMetaData.push(entry);
     }
     return this.server.saveFilesDescriptions(fileMetaData).done(
       () => {
         view.removeFilesDescriptions();
       },
     ).fail((errMsg) => {
       view.baseView.toggleActionError('upload', errMsg);
     });
   }

   /**
     Manages file uploads for submission attachments.
     * */
   uploadFiles() {
     const view = this;
     let promise = null;
     const fileCount = view.files.length;
     const sel = $('.step--response', this.element);

     promise = view.saveFilesDescriptions();

     view.fileCountBeforeUpload = view.getSavedFileCount(true);
     $.each(view.files, (index, file) => {
       promise = promise.then(() => view.fileUpload(
         view,
         file.type,
         file.name,
         view.fileCountBeforeUpload + index,
         file,
         fileCount === (index + 1),
       ));
     });

     return promise;
   }

   /**
     Retrieves a one-time upload URL from the server, and uses it to upload images
     to a designated location.
     * */
   fileUpload(view, filetype, filename, filenum, file, finalUpload) {
     const sel = $('.step--response', this.element);
     const handleError = function (errMsg) {
       view.baseView.toggleActionError('upload', errMsg);
       sel.find('input.file--upload').val(null);
     };

     // Call getUploadUrl to get the one-time upload URL for this file. Once
     // completed, execute a sequential AJAX call to upload to the returned
     // URL. This request requires appropriate CORS configuration for AJAX
     // PUT requests on the server.
     return view.server.getUploadUrl(filetype, filename, filenum).done(
       (url) => {
         view.fileUploader.upload(url, file)
           .done(() => {
             view.fileUrl(filenum);
             view.baseView.toggleActionError('upload', null);
             if (finalUpload) {
               sel.find('input[type=file]').val('');
               view.filesUploaded = true;
             }
           }).fail(handleError);
       },
     ).fail(handleError);
   }

   /**
     Set the file URL, or retrieve it.
     * */
   fileUrl(filenum) {
     const view = this;
     const sel = $('.step--response', this.element);
     view.server.getDownloadUrl(filenum).done((url) => {
       const className = `submission__answer__file__block__${filenum}`;
       let file = null;
       let img = null;
       let fileBlock = null;
       const fileBlockExists = !!sel.find(`.${className}`).length;
       let div1 = null;
       let div2 = null;
       let ariaLabelledBy = null;
       let button = null;

       if (!fileBlockExists) {
         fileBlock = $('<div/>');
         fileBlock.addClass(`submission__answer__file__block ${className}`);
         fileBlock.appendTo(sel.find('.submission__answer__files').first());
       }

       if (view.filesType === 'image') {
         ariaLabelledBy = `file_description_${Math.random().toString(36).substr(2, 9)}`;

         div1 = $('<div/>', {
           id: ariaLabelledBy,
         });
         div1.addClass('submission__file__description__label');
         div1.text(`${view.filesDescriptions[filenum - view.fileCountBeforeUpload]}:`);
         div1.appendTo(fileBlock);

         img = $('<img />');
         img.addClass('submission__answer__file submission--image');
         img.attr('aria-labelledby', ariaLabelledBy);
         img.attr('src', url);

         // manually trigger resize once the image is loaded
         // because MutationObserver doesn't trigger the resize for the image
         img.on('load', () => window.dispatchEvent(new Event('resize')));

         div2 = $('<div/>');
         div2.html(img);
         div2.appendTo(fileBlock);
       } else {
         const description = view.filesDescriptions[filenum - view.fileCountBeforeUpload];
         const fileName = view.fileNames[filenum - view.fileCountBeforeUpload];
         file = $('<a />', {
           href: url,
           text: `${description} (${fileName})`,
         });
         file.addClass('submission__answer__file submission--file');
         file.attr('target', '_blank');
         file.appendTo(fileBlock);
       }

       button = $('<button />');
       button.text('Delete File');
       button.addClass('delete__uploaded__file');
       button.attr('filenum', filenum);
       button.click((eventObject) => {
         eventObject.preventDefault();
         view.handleDeleteFileClick(eventObject.target);
       });
       button.appendTo(fileBlock);

       return url;
     });
   }
}

export default ResponseView;
