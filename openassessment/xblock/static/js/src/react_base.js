import React from 'react';
import ReactDOM from 'react-dom';

import { IntlProvider } from 'react-intl';

import Loading from './react/components/loading';

import * as OA_BASE from './lms/oa_base';

import '../../sass/react.scss';

export function render_react(runtime, element, data) {
  const reactElement = element.lastElementChild;
  const { PAGE_NAME, ON_MOUNT_FUNC, IS_DEV_SERVER } = data;

  // this is necessary for webpack-dev-server to work
  if (!IS_DEV_SERVER) __webpack_public_path__ = window.baseUrl + 'dist/';
  
  const Page = React.lazy(async () => {
    try {
      return await import(`./react/${PAGE_NAME}`);
    }
    catch (error) {
      console.error(error);
      return
    }
  });

  ReactDOM.render(
    <React.Suspense fallback={<Loading />}>
      <IntlProvider locale="en">
        <Page {...data.PROPS} onMount={() => ON_MOUNT_FUNC && OA_BASE[ON_MOUNT_FUNC](runtime, element, data)} />
      </IntlProvider>
    </React.Suspense>,
    reactElement
  );
}

window.render_react = render_react;