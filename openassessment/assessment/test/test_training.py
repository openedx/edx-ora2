# -*- coding: utf-8 -*-
"""
Tests for training models and serializers (common to student and AI training).
"""
import copy
import mock
from django.db import IntegrityError
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import TrainingExample
from openassessment.assessment.serializers import deserialize_training_examples, serialize_training_example


class TrainingExampleSerializerTest(CacheResetTest):
    """
    Tests for serialization and deserialization of TrainingExample.
    These functions are pretty well-covered by API-level tests,
    so we focus on edge cases.
    """

    RUBRIC_OPTIONS = [
        {
            "order_num": 0,
            "name": u"𝒑𝒐𝒐𝒓",
            "explanation": u"𝕻𝖔𝖔𝖗 𝖏𝖔𝖇!",
            "points": 0,
        },
        {
            "order_num": 1,
            "name": u"𝓰𝓸𝓸𝓭",
            "explanation": u"ﻭѻѻɗ ﻝѻ๒!",
            "points": 1,
        },
        {
            "order_num": 2,
            "name": u"єχ¢єℓℓєηт",
            "explanation": u"乇ﾒc乇ﾚﾚ乇刀ｲ ﾌo乃!",
            "points": 2,
        },
    ]

    RUBRIC = {
        'prompt': u"МоъЎ-ↁіск; оѓ, ГЂэ ЩЂаlэ",
        'criteria': [
            {
                "order_num": 0,
                "name": u"vøȼȺƀᵾłȺɍɏ",
                "prompt": u"Ħøw vȺɍɨɇđ ɨs ŧħɇ vøȼȺƀᵾłȺɍɏ?",
                "options": RUBRIC_OPTIONS
            },
            {
                "order_num": 1,
                "name": u"ﻭɼค๓๓คɼ",
                "prompt": u"𝕳𝖔𝖜 𝖈𝖔𝖗𝖗𝖊𝖈𝖙 𝖎𝖘 𝖙𝖍𝖊 𝖌𝖗𝖆𝖒𝖒𝖆𝖗?",
                "options": RUBRIC_OPTIONS
            }
        ]
    }

    EXAMPLES = [
        {
            'answer': (
                u"𝕿𝖍𝖊𝖗𝖊 𝖆𝖗𝖊 𝖈𝖊𝖗𝖙𝖆𝖎𝖓 𝖖𝖚𝖊𝖊𝖗 𝖙𝖎𝖒𝖊𝖘 𝖆𝖓𝖉 𝖔𝖈𝖈𝖆𝖘𝖎𝖔𝖓𝖘 𝖎𝖓 𝖙𝖍𝖎𝖘 𝖘𝖙𝖗𝖆𝖓𝖌𝖊 𝖒𝖎𝖝𝖊𝖉 𝖆𝖋𝖋𝖆𝖎𝖗 𝖜𝖊 𝖈𝖆𝖑𝖑 𝖑𝖎𝖋𝖊"
                u" 𝖜𝖍𝖊𝖓 𝖆 𝖒𝖆𝖓 𝖙𝖆𝖐𝖊𝖘 𝖙𝖍𝖎𝖘 𝖜𝖍𝖔𝖑𝖊 𝖚𝖓𝖎𝖛𝖊𝖗𝖘𝖊 𝖋𝖔𝖗 𝖆 𝖛𝖆𝖘𝖙 𝖕𝖗𝖆𝖈𝖙𝖎𝖈𝖆𝖑 𝖏𝖔𝖐𝖊, 𝖙𝖍𝖔𝖚𝖌𝖍 𝖙𝖍𝖊 𝖜𝖎𝖙 𝖙𝖍𝖊𝖗𝖊𝖔𝖋"
                u" 𝖍𝖊 𝖇𝖚𝖙 𝖉𝖎𝖒𝖑𝖞 𝖉𝖎𝖘𝖈𝖊𝖗𝖓𝖘, 𝖆𝖓𝖉 𝖒𝖔𝖗𝖊 𝖙𝖍𝖆𝖓 𝖘𝖚𝖘𝖕𝖊𝖈𝖙𝖘 𝖙𝖍𝖆𝖙 𝖙𝖍𝖊 𝖏𝖔𝖐𝖊 𝖎𝖘 𝖆𝖙 𝖓𝖔𝖇𝖔𝖉𝖞'𝖘 𝖊𝖝𝖕𝖊𝖓𝖘𝖊 𝖇𝖚𝖙 𝖍𝖎𝖘 𝖔𝖜𝖓."
            ),
            'options_selected': {
                u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
                u"ﻭɼค๓๓คɼ": u"𝒑𝒐𝒐𝒓",
            }
        },
        {
            'answer': u"Tőṕ-héávӳ ẃáś thé śhíṕ áś á díńńéŕĺéśś śtúdéńt ẃíth áĺĺ Áŕíśtőtĺé íń híś héád.",
            'options_selected': {
                u"vøȼȺƀᵾłȺɍɏ": u"𝒑𝒐𝒐𝒓",
                u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
            }
        },
        {
            'answer': (
                u"Consider the subtleness of the sea; how its most dreaded creatures glide under water, "
                u"unapparent for the most part, and treacherously hidden beneath the loveliest tints of "
                u"azure..... Consider all this; and then turn to this green, gentle, and most docile earth; "
                u"consider them both, the sea and the land; and do you not find a strange analogy to something in yourself?"
            ),
            'options_selected': {
                u"vøȼȺƀᵾłȺɍɏ": u"𝒑𝒐𝒐𝒓",
                u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
            }
        },
    ]

    def test_duplicate_training_example(self):
        # Deserialize some examples for a rubric
        deserialize_training_examples(self.EXAMPLES[0:2], self.RUBRIC)

        # Deserialize some more examples, of which two are duplicates
        examples = deserialize_training_examples(self.EXAMPLES, self.RUBRIC)

        # Check that only three examples were created in the database
        db_examples = TrainingExample.objects.all()
        self.assertEqual(len(db_examples), 3)

        # Check that the examples match what we got from the deserializer
        self.assertItemsEqual(examples, db_examples)

    def test_similar_training_examples_different_rubric(self):
        # Deserialize some examples
        first_examples = deserialize_training_examples(self.EXAMPLES, self.RUBRIC)

        # Deserialize one more example with the rubric mutated slightly
        mutated_rubric = copy.deepcopy(self.RUBRIC)
        mutated_rubric['criteria'][0]['options'][0]['points'] = 5
        second_examples = deserialize_training_examples(self.EXAMPLES[0:2], mutated_rubric)

        # There should be a total of 5 examples (3 for the first rubric + 2 for the second)
        db_examples = TrainingExample.objects.all()
        self.assertEqual(len(db_examples), 5)

        # Check that each of the examples from the deserializer are in the database
        for example in (first_examples + second_examples):
            self.assertIn(example, db_examples)

    def test_similar_training_examples_different_options(self):
        # Deserialize some examples
        first_examples = deserialize_training_examples(self.EXAMPLES, self.RUBRIC)

        # Deserialize another example that's identical to the first example,
        # with one option changed
        mutated_examples = copy.deepcopy(self.EXAMPLES)
        mutated_examples[0]['options_selected'][u'vøȼȺƀᵾłȺɍɏ'] = u"єχ¢єℓℓєηт"
        second_examples = deserialize_training_examples(mutated_examples, self.RUBRIC)

        # Expect that a total of 4 examples (3 for the first call, plus one new example in the second call)
        db_examples = TrainingExample.objects.all()
        self.assertEqual(len(db_examples), 4)

        # Check that all the examples are in the database
        for example in (first_examples + second_examples):
            self.assertIn(example, db_examples)

    def test_similar_training_examples_different_answer(self):
        # Deserialize some examples
        first_examples = deserialize_training_examples(self.EXAMPLES, self.RUBRIC)

        # Deserialize another example that's identical to the first example,
        # with a different answer
        mutated_examples = copy.deepcopy(self.EXAMPLES)
        mutated_examples[0]['answer'] = u"MUTATED!"
        second_examples = deserialize_training_examples(mutated_examples, self.RUBRIC)

        # Expect that a total of 4 examples (3 for the first call, plus one new example in the second call)
        db_examples = TrainingExample.objects.all()
        self.assertEqual(len(db_examples), 4)

        # Check that all the examples are in the database
        for example in (first_examples + second_examples):
            self.assertIn(example, db_examples)

    @mock.patch.object(TrainingExample.objects, 'get')
    @mock.patch.object(TrainingExample, 'create_example')
    def test_deserialize_integrity_error(self, mock_create, mock_get):
        # Simulate an integrity error when creating the training example
        # This can occur when using repeatable-read isolation mode.
        mock_example = mock.MagicMock(TrainingExample)
        mock_get.side_effect = [TrainingExample.DoesNotExist, mock_example]
        mock_create.side_effect = IntegrityError

        # Expect that we get the mock example back
        # (proves that the function tried to retrieve the object again after
        # catching the integrity error)
        examples = deserialize_training_examples(self.EXAMPLES[:1], self.RUBRIC)
        self.assertEqual(examples, [mock_example])

    def test_serialize_training_example_with_legacy_answer(self):
        """Test that legacy answer format in training example serialized correctly"""
        training_examples = deserialize_training_examples(self.EXAMPLES, self.RUBRIC)
        for example in training_examples:
            self.assertIsInstance(example.answer, unicode)
            serialized_example = serialize_training_example(example)
            self.assertIsInstance(serialized_example["answer"], dict)
            expected_answer_dict = {'parts': [{'text': example.answer}]}
            self.assertEqual(serialized_example["answer"], expected_answer_dict)
