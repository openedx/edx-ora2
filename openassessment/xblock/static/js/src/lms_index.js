import './oa_shared';

import {
  OpenAssessmentBlock,
  CourseOpenResponsesListingBlock,
  StaffAssessmentBlock,
} from './lms/oa_base';

console.log("Webpack ORA - LMS")
window.OpenAssessmentBlock = OpenAssessmentBlock;
window.CourseOpenResponsesListingBlock = CourseOpenResponsesListingBlock;
window.StaffAssessmentBlock = StaffAssessmentBlock;
