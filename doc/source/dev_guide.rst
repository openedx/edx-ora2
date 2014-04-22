.. _dev_guide:

Understanding the Workflow
--------------------------

.. warning:: The following section refers to features that are not yet fully
             implemented.

The `openassessment.workflow` application is tasked with managing the overall
life-cycle of a student's submission as it goes through various evaluation steps
(e.g. peer assessment, self assessment). A new workflow entry is created as soon
as the student submits their response to a question, and it is initialized with
the steps (and step order) are initialized at that time.

Canonical Status
   Except in the case of `done`, the `status` value stored in the
   `AssessmentWorkflow` model is not the canonical status. This is because the
   determination of what we need to do in order to be "done" is specified by the
   OpenAssessmentBlock problem definition and can change. So every time we are
   asked where the student is, we have to query the assessment APIs (peer, self,
   AI, etc.) with the latest requirements(e.g. "number of submissions you have
   to assess = 5"). The "status" field on this model is an after the fact
   recording of the last known state of that information so we can search
   easily.

   However, once a workflow has transitioned to `done`, it means that a score
   has been created for this workflow and it should not be possible to pull it
   back into an "in progress" state. Once you're finished, you're finished.

Isolation of Assessment types
   The various assessment types a workflow invokes are not aware of where they
   are in the grander scheme of things. So for instance, the peer assessment API
   is unaware that self assessment exists and vice versa. The overall workflow
   is responsible for querying these sub-APIs through a small set of pre-defined
   calls:

   `bool is_submitter_done(submission_uuid)`
      Has the person submitting the problem (the owner of `submission_uuid`) done
      everything they need to do in order to advance to the next step?
   `bool is_assessment_done(submission_uuid)`
      Is there enough information to score this assessment step? In the case of
      peer grading, this would mean that a sufficient number of people have
      assessed it.
   `dict get_score(submission_uuid)`
      Returns a dict with keys `points_earned` and `points_possible` where both
      values are integers. This represents the recorded score for this
      assessment step. If no score is possible at this time, return `None`. Once
      a non `None` value has been returned by this function for a given
      `submission_uuid`, repeated calls to this function should return the same
      thing.

   In the long run, it could be that `OpenAssessmentBlock` becomes a wrapper
   that talks to child XBlocks via this kind of API, and that each child would
   be responsible for answering these questions and proxy to relevant backend
   APIs as appropriate. For now though, the workflow just calls these things
   directly.

Determining Completion
   We start with the first assessment step as a status (unsubmitted items have
   no workflow, so there is no step for that). As each step completes, we move
   to the next one specified in the XML. If we have completed all steps, then
   we check to see if the `is_assessment_done()` is `True` for all steps. If
   the assessments are complete, we give the submission a `Score` in the
   submissions API. If there are steps for which the assessment is incomplete,
   we move the status to `waiting`.

Simple Order/Dependency Assumptions
   We assume that the user is never blocked from going to the next step because
   a previous step needs assessment. They may be unable to proceed because they
   can't complete a step for reasons beyond their control (e.g. there are no
   other submissions to assess in peer), but the gating thing is always
   `is_submitter_done()`, and never `is_assessment_done()`. There are no gating
   dependencies where, for instance, you might be restricted from starting peer
   grading until AI grading has assessed you and given you a score.

   This assumption will not be true forever, but it's a simplifying assumption
   for the next six months or so.

Steps Stay Completed
   In the interests of not surprising/enraging students, once a step is complete,
   it stays complete. So if peer grading requires two assessors and a particular
   submission meets that threshold, it will be considered complete at that point
   in time. Raising the threshold to three required assessors in the future will
   not cause that step for that submission workflow to be considered incomplete
   again.

Handling Problem Definition Change
   Not all of this is going to be implemented in the first cut, but a longer
   term plan for how conflict resolution should happen in the case of the
   overall submission workflow:

   1. Any completed steps stay completed. If a completed step is no longer part
      of the workflow (e.g. we removed self-assessment), then we keep around
      the model information for that step anyway, but just don't reference it.
   2. If the sequence of steps changes, we look at the new steps and advance to
      the first step that the user has not completed (`is_submitter_done()`
      returns `False`).
