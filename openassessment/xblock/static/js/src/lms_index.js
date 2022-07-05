import './oa_shared';

import {
  OpenAssessmentBlock,
  CourseOpenResponsesListingBlock,
  StaffAssessmentBlock,
  WaitingStepDetailsBlock,
} from './lms/oa_base';
import ReactRenderer from './react/ReactRenderer';

window.OpenAssessmentBlock = OpenAssessmentBlock;
window.CourseOpenResponsesListingBlock = CourseOpenResponsesListingBlock;
window.StaffAssessmentBlock = StaffAssessmentBlock;
window.WaitingStepDetailsBlock = WaitingStepDetailsBlock;
window.OraReactRenderer = ReactRenderer;
