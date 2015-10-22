.. _PA Accessing Assignment Information:

##########################################
Accessing Assignment and Learner Metrics
##########################################

After your open response assessment assignment has been released, you can access information about the number of learners in each step of the assignment or the performance of individual learners. This information is available in the **Course Staff Information** section at the end of each assignment. To access it, open the assignment in the courseware, scroll to the bottom of the assignment, and then click the black **Course Staff Information** banner.

.. image:: /Images/PA_CourseStaffInfo_Collapsed.png
   :alt: The Course Staff Information banner at the bottom of the peer assessment

.. _PA View Metrics for Individual Steps:

************************************************
View Metrics for Individual Steps
************************************************

You can check the number of learners who have completed, or are currently working through, the following steps:

* Submitted responses.
* Completed peer assessments.
* Waiting to assess responses or receive grades.
* Completed self assessments.
* Completed the entire assignment. 

To find this information, open the assignment in the courseware, scroll to the bottom of the assignment, and then click **Course Staff Information**.

The **Course Staff Information** section expands, and you can see the number of learners who are currently working through (but have not completed) each step of the problem.

.. image:: /Images/PA_CourseStaffInfo_Expanded.png
   :alt: The Course Staff Information box expanded, showing problem status

.. _Access Information for a Specific Learner:

***********************************************
Access Information for a Specific Learner
***********************************************

You can access information about an individual learner's performance on a peer assessment assignment, including:

* The learner's response. 
* The peer assessments that other learners performed on the learner's response, including feedback on individual criteria and on the overall response.
* The peer assessments that the learner performed on other learners' responses, including feedback on individual criteria and on the overall responses.
* The learner's self assessment.

In the following example, you can see the learner's response. The response received one peer assessment, and the learner completed a peer assessment on one other learner's response. The learner also completed a self assessment.

.. image:: /Images/PA_SpecificStudent.png
   :width: 500
   :alt: Report showing information about a learner's response

For an example that shows a learner's response with more assessments, see :ref:`Access Learner Information`.

Accessing information about a specific learner has two steps:

#. Determine the learner's course-specific anonymized ID.
#. Access information for that learner.

=====================================================
Determine the Learner's Course-Specific Anonymized ID
=====================================================

To determine a learner's course-specific anonymized ID, you'll need two .csv spreadsheets from the Instructor Dashboard: the grade report (**<course name>_grade_report_<datetime>.csv**) and the list of course-specific anonymized learner IDs (**<course name>-anon-ids.csv**).

#. In the LMS, click the **Instructor** tab.
#. On the Instructor Dashboard, click **Data Download**.
#. On the **Data Download** page, locate the **Data Download** section, and then click **Get Student Anonymized IDs CSV**. A spreadsheet named **<course name>-anon-ids.csv** automatically downloads. Click to open the spreadsheet.
#. Scroll down to the **Reports** section, and then click **Generate Grade Report**. 

   The system automatically begins to generate the grade report. When it's finished, a link to the grade report appears in the list below **Reports Available for Download**.

   .. note:: Generating a grade report for a large class may take several hours.

5. When the link to the grade report appears in the **Reports Available for Download** list, click the link to open the spreadsheet.
#. When you have both spreadsheets open, view the **<course name>_grade_report_<datetime>.csv** spreadsheet. Locate the learner that you want by username or e-mail address. Make a note of the number in the ID column (column A) for that learner. In the following example, the learner ID for e-mail address ``amydorrit@example.com`` (username ``lildorrit``) is ``18557``.

   .. image:: /Images/PA_grade_report.png
      :width: 500
      :alt: Spreadsheet listing enrolled learners and grades

7. Go to the **<course name>-anon-ids.csv** spreadsheet, locate the user ID that you noted in step 6, and then copy the value in the "Course Specific Anonymized user ID" column (**column C**) for the user. The value in column C is the learner's anonymized user ID for the course. In the following example, the anonymized user ID for learner ID ``18557`` is ``ofouw6265242gedud8w82g16qshsid87``.

   .. image:: /Images/PA_anon_ids.png
      :width: 500
      :alt: Spreadsheet listing learners' anonymous user IDs

   .. note:: Make sure that you don't copy the value in column B. You need the *course-specific* anonymized user ID from **column C**.

.. _Access Learner Information:

=======================================
Access the Learner's Information
=======================================

#. In the LMS, go to the peer assessment assignment that you want to see.
#. Scroll to the bottom of the problem, and then click the black **Course Staff Information** banner.
#. Scroll down to the **Get Learner Info** box, paste the learner's course-specific anonymized user ID in the box, and then click **Submit**.

The learner's information appears below the **Get Learner Info** box.

The following example shows:

* The learner's response. 
* The two peer assessments for the response.
* The two peer assessments the learner completed.
* The learner's self assessment.

For a larger view, click the image so that it opens by itself in the browser window, and then click anywhere on the image that opens.

.. image:: /Images/PA_SpecificStudent_long.png
   :width: 250
   :alt: Report showing information about a learner's response
