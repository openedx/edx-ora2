import json
import os.path

from ddt import ddt, file_data
from django.test import TestCase

from openassessment.peer.models import Criterion, CriterionOption, Rubric
from openassessment.peer.serializers import rubric_id_for

def json_data(filename):
    curr_dir = os.path.dirname(__file__)
    with open(os.path.join(curr_dir, filename), "rb") as json_file:
        return json.load(json_file)

class TestPeerSerializers(TestCase):

    def test_repeat_data(self):
        rubric_data = json_data('rubric_data/project_plan_rubric.json')

        rubric_id1 = rubric_id_for(rubric_data)
        rubric_id2 = rubric_id_for(rubric_data)

        self.assertEqual(rubric_id1, rubric_id2)

        Rubric.objects.get(id=rubric_id1).delete()

    def test_db_access(self):
        rubric_data = json_data('rubric_data/project_plan_rubric.json')

        with self.assertNumQueries(4):
            rubric_id1 = rubric_id_for(rubric_data)

        with self.assertNumQueries(1):
            rubric_id2 = rubric_id_for(rubric_data)

        Rubric.objects.get(id=rubric_id1).delete()