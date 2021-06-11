import './oa_shared';

import { OpenAssessmentEditor } from './studio/oa_edit';

window.OpenAssessmentEditor = OpenAssessmentEditor;

// Expose a dev API
window.__dev__ = {};
