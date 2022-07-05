/* eslint-disable no-new */
import { camelCaseObject } from '@edx/frontend-platform';

const loadUrls = ({ cssUrl, jsUrl }) => new Promise((resolve, reject) => {
  if (!window.OraReactRenderer) {
    const cssElement = document.createElement('link');
    cssElement.rel = 'stylesheet';
    cssElement.type = 'text/css';
    cssElement.href = cssUrl;
    document.head.append(cssElement);

    const jsElement = document.createElement('script');
    jsElement.onload = resolve;
    jsElement.src = jsUrl;
    document.head.append(jsElement);
  } else {
    resolve();
  }
});

const InitializeReact = function (runtime, element, data) {
  // camelCaseObject is doing deep camel case
  const { componentName, props, prevOraSupport } = camelCaseObject(data);

  loadUrls(prevOraSupport).then(() => {
    new window.OraReactRenderer({
      componentName,
      element,
      props: {
        ...camelCaseObject(props),
        prevOra: {
          runtime,
          element,
          // I do not want object in prev_ora_support to be camelCase
          prevOraSupport: data.prev_ora_support,
        },
      },
    });
  });
};

window.InitializeReact = InitializeReact;
