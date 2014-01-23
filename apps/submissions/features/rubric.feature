Feature: As an author I can create a rubric
    As an author
    I want to create a rubric
    In order to give feedback on Submissions

    Scenario: As an author I create a rubric
        Given: I have created a rubric for a problem
        When: I review the problem
        Then: I should see the rubric

    Scenario: As an author I update a rubric
        Given: I am an author
        When: I review a published rubric
        Then: I should see the rubric
        And: I update a rubric for a problem
        When: I review the problem
        Then: I should see the changes to the rubric
