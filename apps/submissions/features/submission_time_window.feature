Feature: An author can configure the submission start and end dates
    As an author
    I can configure the date when a question is open for submissions
    I can configure the date when a question is closed for submissions

    Scenario: An author can configure the submission start and end dates
        Given: I am an author
        And: I configure a start date in the "<RelativeStartTime>"
        And: I configure an end date in the "<RelativeEndTime>"
        When: I attempt to submit a submission
        Then: My attempt to submit a submission "<Result>"

    Examples:
    | RelativeStartTime | RelativeEndTime   | Result |
    | past              | future            | passes |
    | future            | future            | fails  |
    | future            | past              | fails  |
    | past              | past              | fails  |
