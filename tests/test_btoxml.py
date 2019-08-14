#!/usr/bin/env python3
# -*- encoding:utf-8 -*-
#
# @copyright 2011 Canonical Ltd.
# Author 2011 Hsin-Yi Chen
#
# This is a free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This software is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this software; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA 02111-1307 USA
import os
import unittest
import tempfile

from Dell import recovery_xml
ilegal_utf8string = bytes(bytearray(range(129, 255)))

class NewStr(object):

    def __init__(self, _str):
        self._str = _str

    def __repr__(self):
        return self._str

    def __iter__(self):
        return iter(self._str.encode())

class BTOxmlTestCase(unittest.TestCase):

    def setUp(self):
        self.xmlpath = tempfile.mktemp()
        self._load()

    def tearDown(self):
        self.xmlobj = None
        os.remove(self.xmlpath)

    def _write(self, lines):
        lines = [b'<?xml version="1.0" ?><bto>'] + lines + [b'</bto>']
        with open(self.xmlpath, 'wb') as f:
            f.write(b'\n'.join(lines))

    def _load(self):
        self.xmlobj = recovery_xml.BTOxml()
        if os.path.exists(self.xmlpath):
            self.xmlobj.load_bto_xml(self.xmlpath)

    def set_node(self, datas):
        for e in datas:
            (tag, val) = e
            self.xmlobj.replace_node_contents(tag, val)

    def _read_node(self, tag):
        """load a btoxml and read a node"""
        self.newxmlobj = recovery_xml.BTOxml()
        self.newxmlobj.load_bto_xml(self.xmlpath)
        return self.newxmlobj.fetch_node_contents(tag)

    def _save(self):
        self.xmlobj.write_xml(self.xmlpath)

class ReadWriteNewBTOxmlTestCase(BTOxmlTestCase):

    def test_enhance_str(self):
        self.set_node([('syslog', NewStr('ooo'))])
        self._save()
        self.assertEqual('ooo', self._read_node('syslog'))

    def test_set_emptystring(self):
        self.set_node([('syslog', '')])
        self._save()
        self.assertEqual('', self._read_node('syslog'))

    def test_set_node_ascii(self):
        self.set_node([('date', '123')])
        self._save()
        self.assertEqual('123', self._read_node('date'))

    def test_set_node_nonascii(self):
        self.set_node([('syslog', ilegal_utf8string)])
        self._save()
        self.assertEqual('', self._read_node('syslog'))

    def test_set_node_mix(self):
        self.set_node([('date', '2011-11-22'), ('syslog', ilegal_utf8string)])
        self._save()
        self.assertEqual('2011-11-22', self._read_node('date'))

class ReadWriteExistedBTOxmlTestCase(ReadWriteNewBTOxmlTestCase):

    def setUp(self):
        lines = [
            b'<date>2011-11-22</date>',
            b'<syslog>' + '中文測試'.encode('utf-8') + ilegal_utf8string +
                b'</syslog>'
        ]
        self.xmlpath = tempfile.mktemp()
        self._write(lines)
        self._load()

    def test_read_utf8str(self):
        self.assertEqual('中文測試', self._read_node('syslog'))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ReadWriteNewBTOxmlTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ReadWriteExistedBTOxmlTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
