import React from 'react';
import ReactDOM from 'react-dom';

class ReactRendererException extends Error {
  constructor(message) {
    super(`ReactRendererException: ${message}`);
    Error.captureStackTrace(this, ReactRendererException);
  }
}

export class ReactRenderer {
  constructor({ component, element, props = {} }) {
    this.component = component;
    // make sure it is a html dom and not jquery dom
    this.element = element instanceof Element ? element : element.get(0);
    this.props = props;
    this.handleArgumentErrors();
    this.renderComponent();
  }

  handleArgumentErrors() {
    if (this.component === null) {
      throw new ReactRendererException('Component is not defined.');
    }
    if (!(this.props instanceof Object && this.props.constructor === Object)) {
      let propsType = typeof this.props;
      if (Array.isArray(this.props)) {
        propsType = 'array';
      } else if (this.props === null) {
        propsType = 'null';
      }
      throw new ReactRendererException(
        `Invalid props passed to component. Expected an object, but received a ${propsType}.`,
      );
    }
  }

  renderComponent() {
    ReactDOM.render(
      React.createElement(this.component, this.props, null),
      this.element,
    );
  }
}

export default ReactRenderer;
