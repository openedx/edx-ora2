from openassessment.xblock.assessment_block import AssessmentBlock


class SelfAssessmentBlock(AssessmentBlock):

    assessment_type = "self-assessment"
    navigation_text = "Your assessment of your response"
    path = "static/html/oa_self_assessment.html"
    title = "Assess Your Response"