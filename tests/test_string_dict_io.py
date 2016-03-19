from __future__ import unicode_literals

from collections import OrderedDict

from zerotk.easyfs import CreateFile, GetFileContents
from zerotk.terraformer.string_dict_io import StringDictIO


def testStringDictIO(embed_data):
    # Create a regular dict
    dictionary = dict(foo='bar', key='value')

    # Save it to a file
    obtained_file = embed_data['obtained_file.txt']
    StringDictIO.Save(dictionary, obtained_file)

    # Create a file by hand
    expected_file = embed_data['expected_file.txt']
    CreateFile(expected_file, 'foo = bar\nkey = value\n')

    # Syntax should match
    embed_data.assert_equal_files(obtained_file, expected_file)

    # Load a dict from our file
    new_dictionary = StringDictIO.Load(obtained_file)

    # That dict should match the original
    assert new_dictionary == dictionary

    filename = embed_data['testStringDictIO.txt']
    CreateFile(filename, 'first=alpha\nsecond = bravo\nthird =   charlie')
    loaded_dictionary = StringDictIO.Load(filename)
    assert loaded_dictionary == dict(first='alpha', second='bravo', third='charlie')

    loaded_dictionary = StringDictIO.Load(filename, inverted=True)
    assert loaded_dictionary == dict(alpha='first', bravo='second', charlie='third')


def testStringDictIOEmptyFile(embed_data):
    # Make sure this works with empty files.
    filename = embed_data['empty_dict']
    CreateFile(filename, contents='')

    dictionary = StringDictIO.Load(filename)

    assert len(dictionary) == 0


def testStringDictIODictWithSpaces(embed_data):
    filename = embed_data['dict_with_spaces.txt']

    dict_with_spaces = {'key with spaces' : 'value with spaces'}

    StringDictIO.Save(dict_with_spaces, filename)

    assert GetFileContents(filename) == 'key with spaces = value with spaces\n'
    assert StringDictIO.Load(filename) == dict_with_spaces


def testStringDictIOOrderAndSorted(embed_data):
    filename = embed_data['dict.txt']

    ordered_dict = OrderedDict()
    ordered_dict['z'] = 'first'
    ordered_dict['a'] = 'last'

    # Test order
    StringDictIO.Save(ordered_dict, filename)
    assert GetFileContents(filename) == 'z = first\na = last\n'

    # Test sorted
    StringDictIO.Save(ordered_dict, filename, sort_items=True)
    assert GetFileContents(filename) == 'a = last\nz = first\n'

