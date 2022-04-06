**Add support to show input file read code in editor by default**
=======================================

Status
------

 *Pending*

Context
-------

 - Need to add option to select if we want to add input file read code in editor by default or not
 - Current behavior of editor:

   - There is no option to see from where candidate have to read input file in editor

   - There is not code available for reading input files

   - User need support on how to read file very frequently

 - We need a solution where we can add option in ora setting that ask author if the system should display input fileread code by default in the editor orr not

Decisions
---------

- An option to show read input file or not

  - There should a setting in ora which can be modified from studio for each individual question where author can select if system should display input file read code or not

- Display Default read input file code in the editor

  - Default read input file code will be loaded on language changed from drop down in selected language
   - Refer to *Appendix A* for the example of sample input file read code with respect to language

  - Default read input file code will only displayed if the editor is empty or contains default code of any language
  - Default read input file code will only displayed if author select true for value of `show_read_input_file_code`.


Appendix A
----------

  **Sample input file read code example**:

  .. code-block:: JSON

    {
           "Python":"Default code of Python",
           "NodeJS":"Default code of NodeJs",
           "Java":"Default code of Java",
           "C++":"Default code of C++"
    }
