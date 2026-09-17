/**
Interface for interacting with one specific prompt in an ORA.

Args:
element (DOM element): The DOM element representing one specific prompt.
* */
class Prompt {
  constructor(element) {
    this.element = element;
    this.prompt = this.prompt.bind(this);
    this.resolveStaticLinks = this.resolveStaticLinks.bind(this);
  }

  /**
  * Get or set the prompt html
  */
  prompt(promptContent) {
    if (typeof promptContent !== 'undefined') {
      this.element.innerHTML = promptContent;
    }
    return this.element.innerHTML;
  }

  /**
  * Attempt to replace static studio URLs that may have made their way
  * into this prompt with their resolved web versions.
  */
  resolveStaticLinks(staticURL, baseAssetURL) {
    const newContent = window.rewriteStaticLinks(
      this.prompt(),
      staticURL,
      baseAssetURL,
    );
    this.prompt(newContent);
  }
}

/**
Interface for interacting with the displayed prompts in an ORA.

Args:
element (DOM element): The DOM element representing the response section.
* */
export class Prompts {
  constructor(element) {
    const sel = $('.step--response .step__content', element);
    this.prompts = [];
    const promptElements = sel.find('.submission__answer__part__prompt__copy');
    for (let i = 0; i < promptElements.length; i++) {
      this.prompts.push(new Prompt(promptElements[i]));
    }
    this.staticUrl = '/static/';
    this.baseAssetURL = sel.data('baseAssetUrl');
    this.resolveStaticLinks = this.resolveStaticLinks.bind(this);
  }

  /**
  * For each prompt, attempt to replace static studio URLs that may
  * have made their way into the prompt with their resolved web versions.
  */
  resolveStaticLinks() {
    for (let i = 0; i < this.prompts.length; i++) {
      this.prompts[i].resolveStaticLinks(
        this.staticUrl,
        this.baseAssetURL,
      );
    }
  }
}

export default Prompts;
