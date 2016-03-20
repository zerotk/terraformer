

class StringDictIO(object):
    """
    Saves dictionaries into plain text files.

    Assumes all keys and values are strings.

    e.g.:
        my_dict = {'Ak':'Av', 'Bk':'Bv'}

        would save as:

        Ak = Av
        Bk = Bv
    """
    @classmethod
    def Save(cls, dictionary, target_filename, sort_items=False):
        """
        Writes a dictionary into a file.

        :param unicode filename:
            Path and filename for target file.

        :param bool sort_items:
            If True, saved dict will be sorted alphabetically
        """
        items = dictionary.items()
        if sort_items:
            items = sorted(items)

        contents = '\n'.join(['%s = %s' % i for i in items]) + '\n'

        from zerotk.easyfs import CreateFile
        CreateFile(target_filename, contents)

    @classmethod
    def Load(cls, filename, inverted=False):
        """
        Loads a dictionary from a file.

        :param unicode filename:
            Path and filename for source file.

        :param bool inverted:
            If True inverts the key/value order.

        :returns dict:
            Dictionary that was loaded
        """
        from zerotk.easyfs import GetFileContents
        contents = GetFileContents(filename)

        contents_dict = dict()
        import re

        for line in contents.split('\n'):
            search_result = re.search('(.*?)\s*=\s*(.*)', line)
            if search_result is not None:
                key, value = search_result.groups()
                if inverted:
                    contents_dict[value] = key
                else:
                    contents_dict[key] = value

        return contents_dict
