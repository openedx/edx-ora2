/* eslint-disable no-new */
import { ReactRenderer } from './ReactRenderer';

window.ora = window.ora || {};

const loadScript = function (component_url, component_name) {
  return new Promise(function (resolve, reject) {
    if (window.ora[component_name]) resolve();
    else {
      const script = document.createElement('script');
      script.src = component_url;

      script.addEventListener('load', resolve);

      document.head.appendChild(script);
    }
  });
};

window.initialize_react = function (runtime, element, data) {
  const { component_url, component_name, props } = data;

  loadScript(component_url, component_name).then(() => {
    // debugger
    new ReactRenderer({
        component: window.ora[component_name],
        element: element,
        props
      });
  });
};
