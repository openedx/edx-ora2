Feature: An author can configured required reviews per student.
  As an author
  I can configure a number of required reviews per student
  Before the student can see their reviewed submission.

  Scenario: Author configures required reviewers per submission
      Given: I am an author
      And: I configure "<RequiredPeerReviews>" required reviews per student
      And: A student submits a submission
      When: Enough students review the submission
      And: The student requests a grade
      Then: The student is notified they did not review enough peer submissions
      And: A student reviews "<RequiredPeerReviews>" peer submissions
      Then: The student receives reviews.

  Examples:
  | RequiredPeerReviews |
  | 2                   |
  | 5                   |
  | 12                  |