import os
import pytest

import cidc_schemas.util as util

from .constants import TEST_DATA_DIR

def test_split_python_style_path():

    assert ['p', 0, 'a', 0, 'id'] == list(util.split_python_style_path("root['p'][0]['a'][0]['id']"))
    assert ['p', 0, 1, 2, 'id'] == list(util.split_python_style_path("root['p'][0][1][2]['id']"))


def test_get_all_paths():
    hier = {
        "p": [{
            "a": [{
                "id": 1,
                "i want": "this"
            },
            {
                "id": 2,
                "and": "this"
            }],
            "id" : "3",
            "and" : "this"
        }]
    }

    assert ["root['p'][0]['a'][0]['id']"] == list(util.get_all_paths(hier, 1))
    assert ["root['p'][0]['a'][1]['id']"] == list(util.get_all_paths(hier, 2))
    assert ["root['p'][0]['id']"] == list(util.get_all_paths(hier, "3"))
    with pytest.raises(KeyError):
        assert (util.get_all_paths(hier, 3))
    
    assert ["root[0]['id']"] == list(util.get_all_paths(hier['p'], "3"))

    assert [
        "root['p'][0]['a'][0]['i want']",
        "root['p'][0]['a'][1]['and']",
        "root['p'][0]['and']"
        ] == sorted(list(util.get_all_paths(hier, "this")))


def test_get_path_with_strings_with_quotes():
    hier = {
        "p": [{
            "a": [{
                "i want ' ": "this"
            }],
            "and \" " : "that"
        }]
    }

    assert "root['p'][0]['a'][0]['i want ' ']" == util.get_path(hier, "this")
    assert "root['p'][0]['and \" ']" == util.get_path(hier, "that")



def test_get_source():

    hier = {
        "p": [{
            "a": [{
                "id": 1
            },
            {
                "id": 2
            }],
            "id" : "3"
        }]
    }

    assert 1 == util.get_source(hier, "root['p'][0]['a'][0]['id']")
    assert 2 == util.get_source(hier, "root['p'][0]['a'][1]['id']")
    assert '3' == util.get_source(hier, "root['p'][0]['id']")
    
    assert util.get_source(hier, "root['p'][0]['a'][1]['id']", skip_last=3) == util.get_source(hier, "root['p'][0]")



def test_get_source_with_strings_with_quotes():
    hier = {
        "p": [{
            "a": [{
                "i want ' ": "this"
            }],
            "and \" " : "that"
        }]
    }

    assert  "this" == util.get_source(hier, "root['p'][0]['a'][0]['i want ' ']")
    assert  "that" == util.get_source(hier, "root['p'][0]['and \" ']")


