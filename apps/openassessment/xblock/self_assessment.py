from openassessment.xblock.assessment import Assessment


class SelfAssessment(Assessment):

    assessment_type = "self-assessment"
    navigation_text = "Your assessment of your response"
    path = "static/html/oa_self_assessment.html"