# -*- coding: utf-8 -*-
"""
Constants used as test data.
"""

STUDENT_ITEM = {
    'student_id': u'𝓽𝓮𝓼𝓽 𝓼𝓽𝓾𝓭𝓮𝓷𝓽',
    'item_id': u'𝖙𝖊𝖘𝖙 𝖎𝖙𝖊𝖒',
    'course_id': u'ՇєรՇ ς๏ยгรє',
    'item_type': u'openassessment'
}

ANSWER = {'text': u'ẗëṡẗ äṅṡẅëṛ'}

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
    'prompts': [{"description": u"МоъЎ-ↁіск; оѓ, ГЂэ ЩЂаlэ"}],
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

RUBRIC_POSSIBLE_POINTS = sum(max(option["points"] for option in criterion["options"]) for criterion in RUBRIC["criteria"])

# Used to generate OPTIONS_SELECTED_DICT. Indices refer to RUBRIC_OPTIONS.
OPTIONS_SELECTED_CHOICES = {
    "none": [0, 0],
    "few": [0, 1],
    "most": [1, 2],
    "all": [2, 2],
}

OPTIONS_SELECTED_DICT = {
    key: {
        "options": { RUBRIC["criteria"][i]["name"]: RUBRIC_OPTIONS[j]["name"] for i, j in enumerate(value) },
        "expected_points": sum(RUBRIC_OPTIONS[i]["points"] for i in value)
    } for key, value in OPTIONS_SELECTED_CHOICES.iteritems()
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
]
