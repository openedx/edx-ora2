# Architecture

## Submissions

submission_mixin.py:submit()
- collects, validates submission
- gets workflow info, should be null
- Team: create a submission per team-member
    - Creates workflow per submission

verified: {'submitted_at': datetime.datetime(2020, 1, 14, 18, 51, 6, 190610, tzinfo=<UTC>), 'created_at': datetime.datetime(2020, 1, 14, 18, 51, 6, 190662, tzinfo=<UTC>), 'student_item': 67, 'answer': {'parts': [{'text': 'Test'}]}, 'uuid': '8c3a5a53-891c-480d-92d9-683a6cf274b5', 'attempt_number': 1}

honor: {'submitted_at': datetime.datetime(2020, 1, 14, 18, 53, 0, 421391, tzinfo=<UTC>), 'created_at': datetime.datetime(2020, 1, 14, 18, 53, 0, 421421, tzinfo=<UTC>), 'student_item': 72, 'answer': {'parts': [{'text': 'Test'}]}, 'uuid': 'c6740782-80f1-4b6b-8978-0d981b387795', 'attempt_number': 1}]

submission_mixin:submission_path_and_context()
- tries to get workflow info
    - If no UUId is passed in, get from self (OVERRIDE THIS?)

has_saved, saved_response

TODO:
- Make sure we've created a student item for submissions
- Make sure to query these when we load

submitted by teammember:
    workflow = {}
    step = 'submission'

context @submission_mixin 743
{'file_upload_type': 'pdf-and-image', 'submit_enabled': False, 'saved_response': {'answer': {'parts': [{'prompt': {'description': "<p>Censorship in the Libraries<br /><br /> 'All of us can think of a book that we hope none of our children or any other children have taken off the shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have exactly the same right and so does everyone else. And then we have no books left on the shelf for any of us.' --Katherine Paterson, Author<br /><br /> Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive? Support your position with convincing arguments from your own experience, observations, and/or reading.<br /><br /> Read for conciseness, clarity of thought, and form.</p>"}, 'text': ''}]}}, 'submission_due': datetime.datetime(2029, 1, 1, 0, 0, tzinfo=<UTC>), 'save_status': 'This response has not been saved.', 'text_response': 'optional', 'prompts_type': 'html', 'user_timezone': None, 'xblock_id': 'block-v1:Masters+dev101+2019_Oct+type@openassessment+block@0ece2d961f0a49189619fa19f50f8829', 'file_urls': [('/media/submissions_attachments/c4baed194314c6e576fcfc031985345d_course-v1%3AMasters%2Bdev101%2B2019_Oct_block-v1%3AMasters%2Bdev101%2B2019_Oct%2Btype%40openassessment%2Bblock%400ece2d961f0a49189619fa19f50f8829', 'honor 1', 'Screen Shot 2019-10-23 at 15.58.48.png')], 'enable_delete_files': True, 'team_url': '/courses/course-v1:Masters+dev101+2019_Oct/teams/#teams/algorithms/team-a-39126ee342424fc9b82d0f94fcc37982', 'team_id': 'team-a-39126ee342424fc9b82d0f94fcc37982', 'team_name': 'Team A', 'team_usernames': ['verified', 'honor'], 'allow_latex': False, 'user_language': None, 'file_upload_response': 'required'}


Submitted for team
Note: even before context funciton, shows correct step

workflow: {'status_details': {'staff': {'complete': True, 'graded': False}}, 'status': 'waiting', 'score': None, 'submission_uuid': 'd51a8732-d66a-4ddd-a8aa-749a02639d08', 'modified': '2020-01-09T22:23:42.189546Z', 'created': '2020-01-09T22:23:42.166662Z'}

path = oa_response_submitted
context = 
{'file_upload_type': 'pdf-and-image',
'student_submission': {'student_item': 9, 'attempt_number': 1, 'created_at': datetime.datetime(2020, 1, 9, 22, 23, 42, 148263, tzinfo=<UTC>), 'submitted_at': datetime.datetime(2020, 1, 9, 22, 23, 42, 148238, tzinfo=<UTC>), 'answer': {'files_names': ['Brownie recipe001.jpg', 'Brownie recipe002.jpg'], 'parts': [{'prompt': {'description': "<p>Censorship in the Libraries<br /><br /> 'All of us can think of a book that we hope none of our children or any other children have taken off the shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have exactly the same right and so does everyone else. And then we have no books left on the shelf for any of us.' --Katherine Paterson, Author<br /><br /> Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive? Support your position with convincing arguments from your own experience, observations, and/or reading.<br /><br /> Read for conciseness, clarity of thought, and form.</p>"}, 'text': ''}], 'files_sizes': [689334, 262573], 'files_descriptions': ['verified 1', 'verified 2'], 'file_keys': ['3d27ff68f4d37fcee961e020077ab482/course-v1:Masters+dev101+2019_Oct/block-v1:Masters+dev101+2019_Oct+type@openassessment+block@31ce00f104f742289e857f1e387e1651', '3d27ff68f4d37fcee961e020077ab482/course-v1:Masters+dev101+2019_Oct/block-v1:Masters+dev101+2019_Oct+type@openassessment+block@31ce00f104f742289e857f1e387e1651/1']}, 'uuid': 'd51a8732-d66a-4ddd-a8aa-749a02639d08'}, 
'submission_due': datetime.datetime(2029, 1, 1, 0, 0, tzinfo=<UTC>),
'text_response': 'optional',
'prompts_type': 'html',
'user_timezone': None, 'xblock_id':
'block-v1:Masters+dev101+2019_Oct+type@openassessment+block@31ce00f104f742289e857f1e387e1651', 'file_urls': [('/media/submissions_attachments/3d27ff68f4d37fcee961e020077ab482_course-v1%3AMasters%2Bdev101%2B2019_Oct_block-v1%3AMasters%2Bdev101%2B2019_Oct%2Btype%40openassessment%2Bblock%4031ce00f104f742289e857f1e387e1651', 'verified 1', 'Brownie recipe001.jpg'), ('/media/submissions_attachments/3d27ff68f4d37fcee961e020077ab482_course-v1%3AMasters%2Bdev101%2B2019_Oct_block-v1%3AMasters%2Bdev101%2B2019_Oct%2Btype%40openassessment%2Bblock%4031ce00f104f742289e857f1e387e1651_1', 'verified 2', 'Brownie recipe002.jpg')], 'enable_delete_files': False, 'peer_incomplete': False, 'self_incomplete': False, 'allow_latex': False, 'user_language': None, 'file_upload_response': 'required'}

Workflow
{'uuid': UUID('19c5433e-374c-4b09-bcd3-6f0b6abc7595'), 'submission_uuid': '9b717acc-dddf-470a-a707-03308535006d', '_state': <django.db.models.base.ModelState object at 0x7f33e76f1ba8>, 'created': datetime.datetime(2020, 1, 9, 20, 38, 15, 467791, tzinfo=<UTC>), 'modified': datetime.datetime(2020, 1, 9, 20, 38, 15, 536875, tzinfo=<UTC>), 'item_id': 'block-v1:Masters+dev101+2019_Oct+type@openassessment+block@7b7d79c467be47dca53c6fde5883c235', '_monitor_status_changed': 'waiting', 'id': 6, 'status_changed': datetime.datetime(2020, 1, 9, 20, 38, 15, 536897, tzinfo=<UTC>), 'status': 'waiting', 'course_id': 'course-v1:Masters+dev101+2019_Oct'}