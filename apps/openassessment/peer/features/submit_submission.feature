Feature: A student can submit a submission
    As a student
    I can submit a submission for peer review

  Scenario: A student can submit a submission for peer review
      Given: I am a student
      When: I submit a submission for peer review
      Then: I am notified that my submission has been submitted

  Scenario: A student can submit a submission with unicode characters
      Given: I am a student
      When: I submit a submission for peer review with unicode characters
      Then: My submission is submitted and the unicode characters are preserved
