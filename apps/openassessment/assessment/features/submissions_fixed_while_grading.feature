Feature: Submissions are fixed once reviews have begun
    As a student
    Once review of my submission has begun
    I cannot modify my submission

  Scenario: A student can modify a submission if reviewing has not begun
      Given: I am a student
      When: I submit a submission for peer review
      And: I modify my submission
      Then: I successfully save changes to my submission

  Scenario: A student cannot modify a submission once reviewing has begun
      Given: I am a student
      When: I submit a submission for peer review
      And: A peer begins to review my submission
      Then: I cannot modify my submission
