class SubmissionUIModel(object):

    def __init__(self):
        self.assessment_type = "submission"
        self.name = "submission"
        self.navigation_text = "Your response to this problem"
        self.title = "Your Response"

    def create_ui_model(self):
        return {
            "assessment_type": self.assessment_type,
            "name": self.name,
            "navigation_text": self.navigation_text,
            "title": self.title
        }


class AssessmentUIModel(object):

    def __init__(self):

        self.assessment_type = None
        self.name = ''
        self.start_datetime = None
        self.due_datetime = None
        self.must_grade = 1
        self.must_be_graded_by = 0
        self.navigation_text = ""
        self.title = ""

    def create_ui_model(self):
        return {
            "assessment_type": self.assessment_type,
            "name": self.name,
            "start_datetime": self.start_datetime,
            "due_datetime": self.due_datetime,
            "must_grade": self.must_grade,
            "must_be_graded_by": self.must_be_graded_by,
            "navigation_text": self.navigation_text,
            "title": self.title
        }


class PeerAssessmentUIModel(AssessmentUIModel):

    def __init__(self):
        super(PeerAssessmentUIModel, self).__init__()
        self.assessment_type = "peer-assessment"
        self.title = "Assess Peers' Responses"
        self.navigation_text = "Your assessment(s) of peer responses"


class SelfAssessmentUIModel(AssessmentUIModel):

    def __init__(self):
        super(SelfAssessmentUIModel, self).__init__()
        self.assessment_type = "self-assessment"
        self.navigation_text = "Your assessment of your response"
        self.title = "Assess Your Response"