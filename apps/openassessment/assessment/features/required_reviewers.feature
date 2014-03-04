Feature: An author can configured required reviewers per submission.
    As an author
    I can configure a number of required reviewers per submission.

    Scenario: Author configures required reviewers per submission
        Given: I am an author
        And: I configure "<RequiredReviews>" required reviewers per submissions
        And: I submit a submission
        And: I review enough peer submissions
        When: "<RequiredReviews>" students review the submission
        Then: I receive my reviews.

        Examples:
        | RequiredReviews |
        | 1               |
        | 3               |
        | 7               |
