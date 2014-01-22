Feature: An author is required to configure less reviews than reviewers
  As an author
  I can configure a number of required reviews per student
  I can configure the number of reviews required per submission
  The reviews required per submission is validated to be less
  than the number of reviews required per student

  Scenario: An author is required to configure less reviews than reviewers
    Given: I am an author
    And: I configure <RequiredPeerReviews> required reviews per student
    And: I configure <RequiredReviews> required reviews per submission
    Then: The validation <Result>

  Examples:
  | RequiredReviews | RequiredPeerReviews | Result |
  | 1               | 2                   | passes |
  | 3               | 5                   | passes |
  | 7               | 12                  | passes |
  | 3               | 3                   | fails  |
  | 3               | 2                   | fails  |
  | 0               | 0                   | fails  |
  | 0               | 1                   | fails  |
