Feature: An author can configured required reviews per student.
  As an author
  I can configure a number of required reviews per student
  Before the student can see their reviewed submission.

  Scenario: Author configures required reviewers per submission
    Given: I am an author
    And: I configure <RequiredPeerReviews> required reviews per student
    And: A student submits a submission
    And: A student reviews <RequiredPeerReviews> peer submissions
    When: <RequiredReviews> students review the submission
    Then: The student receives reviews.

  Examples:
  | RequiredReviews | RequiredPeerReviews |
  | 1               | 2                   |
  | 3               | 5                   |
  | 7               | 12                  |
