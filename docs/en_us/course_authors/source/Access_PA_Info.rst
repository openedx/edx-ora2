.. _Accessing PA Information:

########################################################
Accessing Assignment Step Status and Student Information
########################################################

.. _PA Access Status of Problem Steps:

******************************
Access Status of Problem Steps
******************************

After your problem has opened, you can check the current number of students who are in each step--that is, how many students have submitted responses, have completed peer and self assessments, are waiting to assess responses or receive grades, or have finished the problem entirely. 

To find this information, open the problem in the LMS, scroll to the bottom of the problem, and then click the black **Course Staff Information** banner.

.. image:: /Images/PA_CourseStaffInfo_Collapsed.png
   :alt: The Course Staff Information banner at the bottom of the peer assessment

**Course Staff Information** expands, and you can see the number of students who are actively in each step of the problem.

.. image:: /Images/PA_CourseStaffInfo_Expanded.png
   :alt: The Course Staff Information box expanded, showing problem status

.. _Access Student Information:

******************************
Access Student Information
******************************

You can access information about an individual student's performance on a peer assessment assignment, including:

* The student's response. 
* The peer assessments that other students performed on the student's response, including feedback on individual criteria and on the overall response.
* The peer assessments that the student performed on other students' responses, including feedback on individual criteria and on the overall responses.
* The student's self assessment.

In the following example, you can see the student's response. The response received one peer assessment, and the student completed one peer assessment on another student's response. The student also completed a self assessment.

.. image:: /Images/PA_SpecificStudent.png
   :width: 600
   :alt: Report showing information about a student's response

Accessing information about a specific student has two steps:

#. Determine the student's anonymized ID.
#. Access information for that student.

=======================================
Determine the Student's Anonymized ID
=======================================

To determine a student's anonymized ID for the course, you'll download two .csv spreadsheets from the Instructor Dashboard.

#. In the LMS, click the **Instructor** tab.
#. On the Instructor Dashboard, click **Data Download**.
#. On the **Data Download** page, locate the **Data Download** section, and then click the **Download profile information as a CSV** button. A spreadsheet named **enrolled_profiles.csv** automatically downloads.
#. In the **Data Download** section, click the **Get Student Anonymized IDs CSV** button. A spreadsheet named **<course name>-anon-ids.csv** automatically downloads.
#. Open both spreadsheets.
#. In the **enrolled_profiles.csv** spreadsheet, locate the student that you want by username, name, or e-mail address. Make a note of the line number for that student. In the following example, Amy Dorrit is listed on line 7.

   .. image:: /Images/PA_enrolled_profiles.png
      :width: 800
      :alt: Spreadsheet listing enrolled students

7. In the **<course name>-anon-ids.csv** spreadsheet, locate the line number that you noted in step 6, and then go to column C, "Course Specific Anonymized user ID", for that line. The value in column C is the student's anonymized user ID for the course. In the following example, the anonymized user ID for Amy Dorrit, line 7, is 9gsbl24689gsdhklh1478192741hjklf.

   .. image:: /Images/PA_anon_ids.png
      :width: 500
      :alt: Spreadsheet listing students' anonymous user IDs

=======================================
Access the Student's Information
=======================================

#. In the LMS, go to the peer assessment assignment that you want to see.
#. Scroll to the bottom of the problem, and then click the black **Course Staff Information** banner.
#. Scroll down to the **Get Student Info** box, enter the student's anonymized user ID in the box, and then click **Submit**.

The student's information appears below the **Get Student Info** box.

