.. _Peer Assessments:

#########################
Open Response Assessments
#########################

*****************************************
Introduction to Open Response Assessments
*****************************************

Open response assessments allow instructors to assign questions that may not have definite answers. Students submit a response to the question, and then that student and the student's peers compare the response to a rubric that you create. Usually students will submit text responses. You can also allow your students to upload an image to accompany the text.

Open response assessments include peer assessments and self assessments. In peer assessments, students compare their peers' responses to a rubric that you create. In self assessments, students compare their own responses to the rubric.

For more information, see the following sections:

* :ref:`PA Elements`
* :ref:`PA Scoring`
* :ref:`PA Create a PA Assignment`
* :ref:`PA Accessing Assignment Information`

.. _PA Elements:

*****************************************
Elements of an Open Response Assessment
*****************************************

When you create an open response assessment assignment, you include several elements:

* The number of responses and assessments.
* One or more assessment types. Assessment types include **student training**, **peer**, and **self**.
* (Optional) The due dates for each step.
* The question.
* The rubric.

For step-by-step instructions, see :ref:`PA Create a PA Assignment`.

=======================================
Number of Responses and Assessments
=======================================

In the assignment code, you'll indicate the **number of responses** each student has to assess and the **number of peer assessments** each response has to receive.

.. note:: Because some students may submit a response but not complete peer assessments, some responses may not receive the required number of assessments. To increase the chance that all responses will receive enough assessments, you must set the number of responses that students have to assess to be higher than the number of assessments that each response must undergo. For example, if you require each response to receive three assessments, you could require each student to assess five responses.

If all responses have received assessments, but some students haven't completed the required number of peer assessments, those students can assess responses that other students have already assessed. The student who submitted the response sees the additional peer assessments when he sees his score. However, the additional peer assessments do not count toward the score that the response receives.

For more information, see :ref:`PA Specify Name and Assessment Types`.

=====================
Assessment Type
=====================

In your assignment, you'll also specify the **assessment type or types**. You can see the type and order of the assessments when you look at the assignment. In the following example, after students submit a response, they complete peer assessments on other students' responses ("Assess Peers") and then complete self assessments ("Assess Your Response").

.. image:: /Images/PA_AsmtWithResponse.png
  :alt: Image of peer assessment with assessment steps and status labeled
  :width: 600

You can set the assignment to include a peer assessment only, a self assessment only, or both a peer assessment and a self assessment. You can also include a student training assessment that students will complete before they perform peer and self assessments. Student training assessments contain sample responses and scores that you create. They help students learn to grade their peers' responses.

For more information, see :ref:`PA Specify Name and Assessment Types` and :ref:`PA Student Training Assessments`.

===================================
Start and Due Dates (optional)
===================================

You can specify **start dates** and **due dates** for students to submit responses, perform peer assessments, and perform self assessments.

You can set different dates for each step, and these dates can overlap. For example, you can allow students to submit responses and complete peer and self assessments starting on March 1. You can require all responses to be submitted by March 7, but allow students to continue peer and self assessments until March 14, a week after all responses are due.

If you don't specify dates, the deadline for all elements--responses, peer assessments, and self assessments--is the due date that you set for the subsection that contains the peer assessment. If you do specify dates, those dates take precedence over the subsection due date.

.. note:: We don't recommend that you use the same due date and time for response submissions and assessments. If a student submits a response immediately before the due date, other students will have very little time to assess the response before peer assessment closes. In this case, a student's response may not receive a score.

For more information, see :ref:`PA Add Due Dates`.

==============
Question
==============

You'll also specify the **question** that you want your students to answer. This appears near the top of the component, followed by a field where the student enters a response. You can require your students to enter text as a response, or you can require your students to both enter text and upload an image. (All student responses must include text. You cannot require students to only upload an image.)

When you write your question, you can include helpful information for your students, such as what students can expect after they submit responses and the approximate number of words or sentences that a student's response should have. (A response cannot have more than 10,000 words.) 

For more information, see :ref:`PA Add Question`.

.. _PA Rubric:

=======
Rubric
=======

Your assignment must include a **rubric** that you design. The same rubric is used for peer and self assessments, and the rubric appears when students begin grading. Students compare their peers' responses to the rubric.

Rubrics are made of *criteria* and *options*.

* Each criterion has a *name*, a *prompt*, and two or more *options*. 

   * The name is a very short summary of the criterion, such as Ideas or Content. Criterion names generally have just one word. Because the system uses criteria names for identification, **the name for each criterion must be unique.** Criterion names do not appear in the rubric that students see when they are completing peer assessments, but they do appear on the page that shows the student's final grade.

     .. image :: /Images/PA_CriterionName.png
        :alt: A final score page with call-outs for the criterion names

    * The prompt is a description of the criterion. 

* Each option has a *name*, an *explanation*, and a *point value*.

  .. image:: /Images/PA_Rubric_LMS.png
     :alt: Image of a rubric in the LMS with call-outs for the criterion prompt and option names, explanations, and points

You can see both criterion and option names when you access assignment information for an individual student. For more information, see :ref:`PA Accessing Assignment Information`.


.. image:: /Images/PA_Crit_Option_Names.png
   :width: 600
   :alt: Student-specific assignment information with call-outs for criterion and option names

When you create your rubric, decide how many points each option will receive, and make sure that the explanation for each option is as specific as possible. For example, one criterion and set of options may resemble the following.

**Criterion**

Name: Origins

Prompt: Does this response explain the origins of the Hundred Years' War? (5 points possible)

**Options**

.. list-table::
   :widths: 8 20 50
   :stub-columns: 1
   :header-rows: 1

   * - Points
     - Name
     - Explanation
   * - 0
     - Not at all
     - This response does not address the origins of the Hundred Years' War.
   * - 1
     - Dynastic disagreement
     - This response alludes to a dynastic disagreement between England and France, but doesn't reference Edward III of England and Philip VI of France.
   * - 3
     - Edward and Philip
     - This response mentions the dynastic disagreement between Edward III and Philip VI, but doesn't address the role of Salic law.
   * - 5
     - Salic law
     - This response explains the way that Salic law contributed to the dynastic disagreement between Edward III and Philip VI, leading to the Hundred Years' War.

For more information about writing effective rubrics, see Heidi Goodrich Andrade's `Understanding Rubrics <http://learnweb.harvard.edu/alps/thinking/docs/rubricar.htm>`_.

Note that different criteria in the same assignment can have different numbers of options. For example, in the image above, the first criterion has three options and the second criterion has four options.

For more information, see :ref:`PA Add Rubric`.

.. _PA Student Training Assessments:

========================================
Student Training Assessments (optional)
========================================

When you create a peer assessment assignment, you can create one or more student training assessments to help students learn to perform their own assessments. A student training assessment contains one or more sample responses that you write, together with the scores that you would give the sample responses. Students review these responses and try to score them the way that you scored them.

In a student training assessment, the **Learn to Assess Responses** step opens immediately after a student submits a response. The student sees one of the sample responses that you created, along with the rubric. The scores that you gave the response do not appear. The student also sees the number of sample responses that he or she will assess.

.. image:: Images/PA_TrainingAssessment.png
   :alt: Sample training response, unscored
   :width: 500

The student selects an option for each of the assignment's criteria, and then clicks **Compare your selections with the instructor's selections**. If all of the student's selections match the instructor's selections, the next sample response opens automatically.

If any of the student's selections differs from the instructor's selections, the student sees the response again, and the following message appears above the response:

.. code-block:: xml

  Learning to Assess Responses
  Your assessment differs from the instructor's assessment of this response. Review the
  response and consider why the instructor may have assessed it differently. Then, try 
  the assessment again.

For each of the criteria, the student sees one of the following two messages, depending on whether the student's selections matched those of the instructor:

.. code-block:: xml

  Selected Options Differ
  The option you selected is not the option that the instructor selected.

.. code-block:: xml

  Selected Options Agree
  The option you selected is the option that the instructor selected.

For example, the following student chose one correct option and one incorrect option.

.. image:: /Images/PA_TrainingAssessment_Scored.png
   :alt: Sample training response, scored
   :width: 500

The student continues to try scoring the sample response until the student's scoring for all criteria matches the instructor's scoring.

For more information, see :ref:`PA Add a Student Training Assessment`.

.. _PA Scoring:

***********************
Peer Assessment Scoring
***********************

Peer assessments are scored by criteria. An individual criterion's score is the median of the scores that each peer assessor gave that criterion. For example, if the Ideas criterion in a peer assessment receives a 10 from one student, a 7 from a second student, and an 8 from a third student, the Ideas criterion's score is 8.

A student's final score for a peer assessment is the sum of the median scores for each individual criterion. 

For example, a response may receive the following scores from peer assessors:

.. list-table::
   :widths: 25 10 10 10 10
   :stub-columns: 1
   :header-rows: 1

   * - Criterion Name
     - Peer 1
     - Peer 2
     - Peer 3
     - Median
   * - Ideas (out of 10)
     - 10
     - 7
     - 8
     - **8**
   * - Content (out of 10)
     - 7
     - 9
     - 8
     - **8**
   * - Grammar (out of 5)
     - 4
     - 4
     - 5
     - **4**

To calculate the final score, add the median scores for each criterion:

  **Ideas median (8/10) + Content median (8/10) + Grammar median (4/5) = final score (20/25)**

Note, again, that final scores are calculated by criteria, not by individual assessor. Thus the response's score is not the median of the scores that each individual peer assessor gave the response.

.. _PA Create a PA Assignment:

************************************
Create a Peer Assessment Assignment
************************************

To create a peer assessment assignment, you'll edit XML code in a Problem component, similar to the way you create other assignments. The following image shows what a peer assessment component looks like when you edit it in Studio, as well as the way that students see that peer assessment in the courseware.

.. image:: /Images/PA_XML_LMS_All.png
   :alt: Image of a peer assessment in Studio and LMS views
   :width: 800

Creating a peer assessment is a multi-step process:

* :ref:`PA Create Component`
* :ref:`PA Specify Name and Assessment Types`
* :ref:`PA Add a Student Training Assessment`
* :ref:`PA Add Due Dates`
* :ref:`PA Add Question`
* :ref:`PA Add Rubric`
* :ref:`PA Provide Comment Options`
* :ref:`PA Test Assignment`

Each of these steps is covered in detail below.


.. _PA Create Component:

============================
Step 1. Create the Component
============================

#. In Studio, open the unit where you want to create the assessment.
#. Under **Add New Component**, click **Problem**, click the **Advanced** tab, and then click **Peer Assessment**.
#. In the Problem component that appears, click **Edit**.

When the component editor opens, you can see sample code that includes the following. You'll replace this sample content with the content for your assignment:

* The assignment's title.
* The training responses for the assignment.
* The assessment type or types.
* The number of assessments that students must complete.
* A sample question ("prompt").
* A sample rubric.

Note that you won't use the **Settings** tab in the component editor when you create peer assessments.

.. _PA Specify Name and Assessment Types:

========================================================
Step 2. Specify the Assignment Name and Assessment Types
========================================================

To specify the name and assessment types for the assignment, you'll work with the XML near the top of the component editor.

In the component editor, locate the following XML:

.. code-block:: xml

  <title></title>
  <assessments>
    <assessment name="student-training">
      <example>
        <answer>
        (optional) Replace this text with your own sample response for this assignment. Below, list the names of the criteria for this assignment, and then specify the name of the option that you would select for this response. Students will learn to assess responses by assessing this response and comparing the rubric options that they select with the rubric options that you specified.

        If you don't want to provide sample responses and scores, delete the entire 'assessment name="student-training"' element.
        </answer>
        <select criterion="Ideas" option="Fair"/>
        <select criterion="Content" option="Good"/>
      </example>
      <example>
        <answer>
        (optional) Replace this text with another sample response, and then specify the options that you would select for this response below. To provide more sample responses, copy an "example" element and paste as many as you want before the closing "assessment" tag.
        </answer>
        <select criterion="Ideas" option="Poor"/>
        <select criterion="Content" option="Good"/>
      </example>
    </assessment>
    <assessment name="peer-assessment" must_grade="5" must_be_graded_by="3"/>
    <assessment name="self-assessment"/>
  </assessments>

This code includes several elements:

* **The title of the assignment**. In this example, because there is no text between the ``<title>`` tags, the assignment does not have a specified title.
* **The type and order of the assessments**. This information is in the **name** attribute in the ``<assessment>`` tags. Assessments run in the order in which they're listed. In this example, students complete the student training assessment, the peer assessment, and the self assessment, in that order.
* **Two sample responses for student training**, together with the options that you select for each of the criteria for the assignment. This information is between the two sets of ``<example> </example>`` tags. Step-by-step instructions for creating student training responses appear in :ref:`PA Add a Student Training Assessment`. 
* **The number of responses that each student must assess** (for peer assessments). This information is in the **must_grade** attribute in the ``<assessment>`` tag for the peer assessment. In this example, each student must grade five peer responses before he receives the scores that his peers have given him. 
* **The number of peer assessments each response must receive** (for peer assessments). This information is in the **must_be_graded_by** attribute in the ``<assessment>`` tag for the peer assessment. In this example, each response must receive assessments from three students before it can return to the student who submitted it. 

To specify the name and assessment types, follow these steps.

#. Between the ``<title>`` tags, add a name for the assignment.

#. Specify the type of assessments you want students to complete. Assessments run in the order in which they're listed.

   .. note:: If you include both peer and self assessments, the peer assessment must precede the self assessment. If you include a student training assessment, the student training assessment must precede the peer and self assessments. You can also include a student training assessment paired with either a peer assessment only or a self assessment only.

   - If you want students to complete a peer assessment only, delete the ``<assessment name="self-assessment"/>`` tag.

   - If you want students to complete a self assessment only, delete the ``<assessment name="peer-assessment" must_grade="5" must_be_graded_by="3""/>`` tag.

   - If you want students to complete a peer assessment and then a self assessment, leave the default tags.

   - If you include a student training assessment, make sure you add the ``<assessment name="student-training">`` tag *before* the ``<assessment name="peer-assessment">`` and ``<assessment name="self-assessment">`` tags. 

#. If your students will complete a peer assessment, replace the values for **must_grade** and **must_be_graded_by** in the ``<assessment name="peer-assessment">`` tag with the numbers that you want.

   .. note:: The value for **must_grade** must be greater than or equal to the value for **must_be_graded_by**.

.. _PA Add a Student Training Assessment:

========================================================
Step 3. Include a Student Training Assessment (optional)
========================================================

To include a student training assessment, which contains both sample responses and scores, you'll work with the following XML:

.. code-block:: xml

    <assessment name="student-training">
      <example>
        <answer>Replace this text with a sample response for this assignment. You'll assess this sample response in the courseware, and students will then learn to assess responses by assessing this response and comparing the options that they select in the rubric with the options that you selected.</answer>
        <select criterion="Ideas" option="Fair"/>
        <select criterion="Content" option="Good"/>
      </example>
      <example>
        <answer>Replace this text with a sample response for this assignment. You'll assess this sample response in the courseware, and students will then learn to assess responses by assessing this response and comparing the options that they select in the rubric with the options that you selected.</answer>
        <select criterion="Ideas" option="Poor"/>
        <select criterion="Content" option="Good"/>
      </example>
    </assessment>

.. note:: If you don't want to include a student training assessment, delete all of this XML.

This code includes several elements:

* The ``<assessment name="student-training">`` tag indicates that this assessment is a student training assessment. 
* Each set of ``<example>`` tags contains one set of ``<answer>`` tags and two or more ``<select/>`` tags.

  * The set of ``<answer>`` tags contains the text of a sample response that you've created.
  * Each ``<select/>`` tag contains the name of one of the assignment's criteria, as well as the option that you select for the criterion. (For more information about criteria and options, see :ref:`PA Rubric`.)

To add student training responses and scores:

#. Replace the placeholder text between the ``<answer>`` tags with the text of your response. To include paragraph breaks, include a blank line between paragraphs. You don't have to add any other formatting tags to include paragraph breaks.
#. Replace the criterion name in each ``<select/>`` tag with the name of one of the criteria in your assignment. To add more criteria, copy and paste as many ``<select/>`` tags as you need. You must include one ``<select/>`` tag for each of the assignment's criteria. 
#. In the ``<select/>`` tag for each criterion, replace the placeholder option name with the name of the option that you would select for the sample response.
#. Copy and paste as many sets of ``<example>`` tags as you need to cover all the criteria for your assignment.

For more information, see :ref:`PA Student Training Assessments`.

.. _PA Add Due Dates:

==========================================
Step 4. Add Start and Due Dates (optional)
==========================================

Setting start and due dates is optional. If you don't specify dates, the deadline for all student responses and assessments is the due date that you set for the subsection that contains the peer assessment. If you do specify dates, those dates take precedence over the subsection due date.

To specify due dates and times, you'll add code that includes the date and time inside the XML tags for the assignment and for each specific assessment. The date and time must be formatted as ``YYYY-MM-DDTHH:MM:SS``.

.. note:: You must include the "T" between the date and the time, with no spaces. All times are in universal coordinated time (UTC).

* To specify a due date for response submissions, add the ``submission_due`` attribute with the date and time to the ``<openassessment>`` tag (this is the first tag in your assignment).

  ``<openassessment submission_due="YYYY-MM-DDTHH:MM:SS">``

* To specify start and end times for an assessment, add ``start`` and ``due`` attributes with the date and time to the ``<assessment>`` tags for the assessment.

  ``<assessment name="peer-assessment" must_grade="5" must_be_graded_by="3" start="YYYY-MM-DDTHH:MM:SS" due="YYYY-MM-DDTHH:MM:SS"/>``

  ``<assessment name="self-assessment" start="YYYY-MM-DDTHH:MM:SS" due="YYYY-MM-DDTHH:MM:SS"/>``

For example, the code for your assignment may resemble the following.

.. code-block:: xml

  <openassessment submission_due="2014-03-01T00:00:00">
  <assessments>
    <assessment name="peer-assessment" must_grade="5" must_be_graded_by="3" start="2014-02-24T00:00:00" due="2014-03-08T00:00:00"/>
    <assessment name="self-assessment" start="2014-02-24T00:00:00" due="2014-03-08T00:00:00"/>
  </assessments>

In this example, the assignment is set at the subsection level to open on February 24, 2014 at midnight UTC. (This information does not appear in the code.) Additionally, the code specifies the following:

* Students can begin submitting responses on February 24, 2014 at midnight UTC, and must submit all responses before March 1, 2014 at midnight UTC:

  ``<openassessment submission_due="2014-03-01T00:00:00">``

* Students can begin peer assessments on February 24, 2014 at midnight UTC, and all peer assessments must be complete by March 8, 2014 at midnight UTC:

  ``<assessment name="peer-assessment" must_grade="5" must_be_graded_by="3" start="2014-02-24T00:00:00" due="2014-03-08T00:00:00"/>``

* Students can begin self assessments on February 24, 2014 at midnight UTC, and all self assessments must be complete by March 8, 2014 at midnight UTC:

  ``<assessment name="self-assessment" start="2014-02-24T00:00:00" due="2014-03-08T00:00:00"/>``


.. note:: We don't recommend that you use the same due date and time for response submissions and peer assessments. If a student submits a response immediately before the due date, other students will have very little time to assess the response before peer assessment closes. In this case, a student's response may not receive a score.

.. _PA Add Question:

============================
Step 5. Add the Question
============================

The following image shows a question in the component editor along with the way the question appears to students.

.. image:: /Images/PA_Question_XML-LMS.png
      :alt: Image of question in XML and the LMS
      :width: 800

To add the question:

#. In the component editor, locate the first set of ``<prompt>`` tags. The opening ``<prompt>`` tag appears directly below the opening ``<rubric>`` tag.

#. Replace the sample text between the ``<prompt>`` tags with the text of your question. Note that the component editor respects paragraph breaks and new lines inside the ``<prompt>`` tags. You don't have to add ``<p>`` tags to create individual paragraphs.

Require Students to Upload an Image
****************************************

If you want your students to upload an image as a part of their response, change the very first tag in the assignment from ``<openassessment allow_file_upload="False">`` to ``<openassessment allow_file_upload="True">``. This action adds the **Choose File** and **Upload Your Image** buttons below the student response field.

.. image:: /Images/PA_Upload_ChooseFile.png 
   :alt: Open response assessment example with Choose File and Upload Your Image buttons circled
   :width: 500


Add Formatting or Images to the Question
****************************************

In this initial release, you cannot add text formatting or images in the Peer Assessment component. If you want to include formatting or images in the text of your prompt, you can add an HTML component that contains your text above the Peer Assessment component, and then remove the prompt from the Peer Assessment component. The instructions for the peer assessment still appear above the **Your Response** field.

.. image:: /Images/PA_HTMLComponent.png
      :alt: A peer assessment that has an image in an HTML component
      :width: 500

To remove the prompt from the Peer Assessment component, open the component editor, and then delete the first set of ``<prompt>`` tags together with all the text between the tags. The first few lines of XML for the assignment will then resemble the following.

.. code-block:: xml

  <openassessment>
    <title></title>
    <assessments>
      <assessment name="peer-assessment" must_grade="5" must_be_graded_by="3"/>
      <assessment name="self-assessment"/>
    </assessments>
    <rubric>
      <criterion feedback="optional">
        <name>Ideas</name>
        <prompt>Determine if there is a unifying theme or main idea.</prompt>
        <option points="0">


.. _PA Add Rubric:

============================
Step 6. Add the Rubric
============================

To add the rubric, you'll create your criteria and options in XML. The following image shows a highlighted criterion and its options in the component editor, followed by the way the criterion and options appear to students.

.. image:: /Images/PA_RubricSample_XML-LMS.png
      :alt: Image of rubric in XML and the LMS, with call-outs for criteria and options

For more information about criteria and options, see :ref:`PA Elements`.

To add the rubric:

#. In the component editor, locate the following XML. This XML contains a single criterion and its options. You'll replace the placeholder text with your own content.  

	.. code-block:: xml

	      <criterion>
	      <name>Ideas</name>
	      <prompt>Determine if there is a unifying theme or main idea.</prompt>
	      <option points="0">
	        <name>Poor</name>
	        <explanation>Difficult for the reader to discern the main idea.
	                Too brief or too repetitive to establish or maintain a focus.</explanation>
	      </option>
	      <option points="3">
	        <name>Fair</name>
	        <explanation>Presents a unifying theme or main idea, but may
	                include minor tangents.  Stays somewhat focused on topic and
	                task.</explanation>
	      </option>
	      <option points="5">
	        <name>Good</name>
	        <explanation>Presents a unifying theme or main idea without going
	                off on tangents.  Stays completely focused on topic and task.</explanation>
	      </option>
	    </criterion>

   .. note:: The placeholder text contains indentations and line breaks. You don't have to preserve these indentations and line breaks when you replace the placeholder text. 

#. Under the opening ``<criterion>`` tag, replace the text between the ``<name>`` tags with the name of your criterion. Then, replace the text between the ``<prompt>`` tags with the description of that criterion.

   Note that **every criterion must have a unique name.** The system uses the criterion name for identification. For more information about criteria, see :ref:`PA Rubric`.

#. Inside the first ``<option>`` tag, replace the value for ``points`` with the number of points that you want this option to receive.

#. Under the ``<option>`` tag, replace the text between the ``<name>`` tags with the name of the first option. Then, replace the text between the ``<explanation>`` tags with the description of that option.

#. Use this format to add as many options as you want.

You can use the following code as a template:

.. code-block:: xml

	 <criterion>
	   <name>NAME</name>
	   <prompt>PROMPT TEXT</prompt>
	   <option points="NUMBER">
	     <name>NAME</name>
	     <explanation>EXPLANATION</explanation>
	   </option>
	   <option points="NUMBER">
	     <name>NAME</name>
	     <explanation>EXPLANATION</explanation>
	   </option>
	   <option points="NUMBER">
	     <name>NAME</name>
	     <explanation>EXPLANATION</explanation>
	   </option>
	 </criterion>

.. _PA Provide Comment Options:

=============================================
Step 7. Provide Comment Options (optional)
=============================================

After students fill out the rubric, they can provide additional comments for the responses they've assessed. By default, students see a field for comments below the rubric.

.. image:: /Images/PA_CommentsField.png
   :alt: Contents field 
   :width: 500

You can change the text that appears above this comment field. Additionally, you can provide a comment field for each individual criterion.

.. _PA Change Comments Prompt:

Change the Default Prompt Text
*******************************

By default, the prompt text for the comment field is the following:

``(Optional) What aspects of this response stood out to you? What did it do well? How could it improve?``

You can replace this default text with your own text.

To change this text:

#. Locate the ``<feedbackprompt>`` tags between the last closing ``</criterion>`` tag for the rubric and the closing ``</rubric>`` tag for the assignment:

  .. code-block:: xml

          <option points="3">
            <name>Excellent</name>
            <explanation>Includes in-depth information and exceptional supporting details that are fully developed.  Explores all facets of the topic.</explanation>
          </option>
        </criterion>
        <feedbackprompt>(Optional) What aspects of this response stood out to you? What did it do well? How could it improve?</feedbackprompt>
      </rubric>
     </openassessment>

2. Change the text between the ``<feedbackprompt>`` tags to the text that you want.

.. _PA Add Individual Criterion Comments:

Provide a Comment Field for an Individual Criterion
***************************************************

By default, students see only a single comment field below the entire rubric. However, you can add a comment field to an individual criterion or to several individual criteria. The comment field can contain up to 300 characters.

The comment field appears below the options for the criterion. In the following image, the first criterion has a comment field, but the second does not.

.. image:: /Images/PA_Comments_Criterion.png
   :alt: Comment box under an individual criterion
   :width: 500

To add a comment field:

#. Locate the opening ``<criterion>`` tag for the criterion that you want to change.

#. Add the ``feedback`` attribute to this tag. Make sure to set a value for this attribute: 

   * If you want to make comments optional for students, use ``feedback="optional"``.

   * If you want to require students to provide comments, use ``feedback="required"``.

The XML for a criterion that has a comment field as well as options resembles the following.

.. code-block:: xml

   <criterion feedback="optional">
     <name>NAME</name>
     <prompt>PROMPT TEXT</prompt>
     <option points="NUMBER">
       <name>NAME</name>
       <explanation>EXPLANATION</explanation>
     </option>
     <option points="NUMBER">
       <name>NAME</name>
       <explanation>EXPLANATION</explanation>
     </option>
   </criterion>

If you want to provide a comment field below any additional criteria, add the ``feedback="optional"`` or ``feedback="required"`` attribute to the opening tag for each criterion.

.. _PA Zero Option Criteria:

Provide Only Comment Fields for Individual Criteria
****************************************************

When you add a comment field to a criterion, the comment field appears below the options for the criterion. You can also provide a comment field, but no options. 

In the following image, the first criterion has a comment field but no options. The second includes options, but does not have a comment field.

.. image:: /Images/PA_0_Option_Criteria.png

To provide a comment field without options:

#. Locate the opening ``<criterion>`` tag for the criterion that you want to change.

#. Add the ``feedback="required"`` attribute to this tag.

   .. note:: If you don't include options for the criterion, you must include the ``feedback="required"`` attribute. Don't use the ``feedback="optional"`` attribute.

#. If the criterion has options, delete the options.

The XML for a criterion that has a comment field but no options resembles the following.

.. code-block:: xml

   <criterion feedback="required">
     <name>NAME</name>
     <prompt>PROMPT TEXT</prompt>
   </criterion>




.. _PA Test Assignment:

============================
Step 8. Test the Assignment
============================

To test your assignment, set up the assignment in a test course, and ask a group of beta users to submit responses and grade each other. The beta testers can then let you know if they found the question and the rubric easy to understand or if they had any problems with the assignment.

