**Add support to show input file read code in the editor by default**
=======================================

Status
------

 *Approved*

Context
-------

 - Need to add an option to select if we want to add input file read code in the editor by default or not
 - Current behavior of editor:

   - There is no option to see from where candidates have to read the input file in the editor

   - There is no code available for reading input files

   - Users need support on how to read files very frequently

 - We need a solution where we can add an option in ORA settings that asks the author if the system should display input file-read code by default in the editor or not

Decisions
---------

- An option to show read input file or not

  - There should be a setting in ora that can be modified from the studio for each question where the author can select if the system should display input file read code or not

- Display the default read input file code in the editor

  - Default read input file code will be loaded on language changed from the drop-down in the selected language
   - Refer to *Appendix A* for the example of a sample input file read code concerning language

  - Default read input file code will only be displayed in the editor is empty or contains the default code of any language
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
