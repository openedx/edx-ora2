Feature Gating for Open Response Assessments (ORA)
--------------------------------------------------

Status
======

Accepted (March 2020)

Context
=======

The introduction of remote config
(see https://openedx.atlassian.net/wiki/spaces/EdxOps/pages/987202032/How-To+Use+Remote+Config)
allows us to quickly change values of items in Django settings.  A benefit of this approach is that
it is much easier to reason about the differences in feature state between environments
(for example, between staging and production) from Django settings that it is via Django Waffle models.
Lastly, tracking feature state via settings allows us to record "data as code" - that is,
there is a pull request in our configuration repositories corresponding to each state change of a feature toggle.

Decisions
=========

#. **Application-wide feature gating**

   a. We will being to use the Django Settings ``FEATURES`` dictionary to toggle application-wide (that is,
      the feature is enabled/disabled for all courses in an environment) feature state.

   b. We will deprecate the use of the ``WaffleSwitch`` model for enabling application-wide features.  During
      the deprecation period, our feature gating logic will look at both the ``WaffleSwitch`` model state
      and the Django settings ``FEATURES`` state of a feature's name.  Upon removal of all ORA ``WaffleSwitches``,
      our feature gating logic will only consider state as defined in ``FEATURES``.

   c. We will store "sane defaults" for feature state in the Django settings files of both the edx-ora2 repository
      and the edx-platform repository.  The definitions that live in edx-platform will contain toggle annotations
      that provide definitions, use cases, historical context, and so forth.

#. **Course-specific feature gating**

   a. We will continue to use the ``CourseWaffleFlag`` model to allow for course-specific feature gating.  We may
      re-assess this in the future if outside guidance is given on better ways to toggle features at the course-level
      via Django Settings.

Consequences
============

The primary consequence of these decisions have to do with the benefits mentioned above under "Context" - we
will be able to more easily reason about the state of different application environments (with respect to ORA),
and we will be able to capture feature toggle state change via code pull requests.
