Feature: Students will not accidentally submit a submission
    As a student
    When I submit my submission
    I will need to confirm my action.

    Scenario: A student will not accidentally submit a submission
        Given: I am a student
        When: I submit a submission for peer review
        Then: I am prompted to confirm my decision
