Allow File Uploads up to 500MB for ORA Submissions
--------------------------------------------------

Status
======

Accepted (November 2019)

Context
=======

We would like to allow learners to upload larger, richer file types
inside ORA XBlocks, specifically to support "case-study" types of assignments
and team submissions.

Decisions
=========

We will increase the maximum allowed file size that can be uploaded via ORA XBlocks to 500MB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note that this constraint is enforced only via client-side code.

How can we detect/stop misuse?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We will add a management command that measure file size usage by course in the edx-submissions library.
We will run this command periodically via Jenkins, and it will alert some subset of the
Master's development team.

How long will files be retained?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. **We will apply a bucket-level retention policy on all ORA uploads in S3, as follows:**

   a. Standard storage for the first 6-months.
   b. Standard_IA class storage for months 7 through 60.
   c. Glacier storage for months 60 and beyond.

See https://openedx.atlassian.net/browse/EDUCATOR-4743 for implementation.

Consequences
============

Similar to the current situation, ORA files will never truly be deleted from a storage backend.
We will have to change the user experience to handle the case where learners try to view files
older than 60 months (for example, they'll need to trigger some sort of job that fetches old
files out of Glacier storage and sends a notification when the file is ready for download).
