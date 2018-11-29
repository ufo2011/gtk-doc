# -*- python -*-
#
# gtk-doc - GTK DocBook documentation generator.
# Copyright (C) 2018  Stefan Sauer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import argparse
import textwrap
import unittest

from gtkdoc import scan


class ScanHeaderContentTestCase(unittest.TestCase):
    """Baseclass for the header scanner tests."""

    def setUp(self):
        self.decls = []
        self.types = []
        self.options = argparse.Namespace(
            deprecated_guards='GTKDOC_TESTER_DISABLE_DEPRECATED',
            ignore_decorators='',
            rebuild_types=False)

    def scanHeaderContent(self, content):
        return scan.ScanHeaderContent(content, self.decls, self.types,
                                      self.options)

    def assertNoDeclFound(self, slist):
        self.assertEqual([], slist)
        self.assertEqual([], self.decls)
        self.assertEqual([], self.types)

    def assertNothingFound(self, slist, doc_comments):
        self.assertEqual({}, doc_comments)
        self.assertNoDeclFound(slist)


class ScanHeaderContent(ScanHeaderContentTestCase):
    """Test generic scanner behaviour."""

    def test_EmptyInput(self):
        slist, doc_comments = self.scanHeaderContent([])
        self.assertNothingFound(slist, doc_comments)

    def test_FindsDocComment(self):
        slist, doc_comments = self.scanHeaderContent("""\
            /**
             * Symbol:
             */""".splitlines(keepends=True))
        self.assertEqual(1, len(doc_comments))
        self.assertIn('symbol', doc_comments)

    def test_DocDoesNotChangeSlistDeclAndTypes(self):
        slist, doc_comments = self.scanHeaderContent("""\
            /**
             * Symbol:
             */""".splitlines(keepends=True))
        self.assertNoDeclFound(slist)

    # TODO: test /* < private_header > */ maker

    def test_SkipSymbolWithPreprocessor(self):
        slist, doc_comments = self.scanHeaderContent("""\
            #ifndef __GTK_DOC_IGNORE__
            extern int bug_512565(void);
            #endif""".splitlines(keepends=True))
        self.assertNoDeclFound(slist)


class ScanHeaderContentEnum(ScanHeaderContentTestCase):
    """Test parsing of enum declarations."""

    def assertDecl(self, name, decl, slist):
        self.assertEqual([name], slist)
        d = '<ENUM>\n<NAME>%s</NAME>\n%s</ENUM>\n' % (name, decl)
        self.assertEqual([d], self.decls)
        self.assertEqual([], self.types)

    def test_FindsEnum(self):
        header = textwrap.dedent("""\
            enum data {
              TEST,
            };""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('data', header, slist)

    def test_FindsTypedefEnum(self):
        header = textwrap.dedent("""\
            typedef enum {
              ENUM
            } Data;""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('Data', header, slist)

    def test_HandleEnumWithDeprecatedMember(self):
        header = textwrap.dedent("""\
            enum data {
              TEST_A,
            #ifndef GTKDOC_TESTER_DISABLE_DEPRECATED
              TEST_B,
            #endif
              TEST_C
            };""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('data', header, slist)

    def test_HandleDeprecatedInMemberName(self):
        header = textwrap.dedent("""\
            typedef enum {
              VAL_DEFAULT,
              VAL_DEPRECATED,
            } Data;""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('Data', header, slist)


class ScanHeaderContentFunctions(ScanHeaderContentTestCase):
    """Test parsing of function declarations."""

    def assertDecl(self, name, ret, params, slist):
        self.assertEqual([name], slist)
        d = '<FUNCTION>\n<NAME>%s</NAME>\n<RETURNS>%s</RETURNS>\n%s\n</FUNCTION>\n' % (name, ret, params)
        self.assertEqual([d], self.decls)
        self.assertEqual([], self.types)

    def test_FindsFunctionVoid(self):
        header = 'void func();'
        slist, doc_comments = self.scanHeaderContent([header])
        self.assertDecl('func', 'void', '', slist)

    def test_FindsFunctionVoidVoid(self):
        header = 'void func(void);'
        slist, doc_comments = self.scanHeaderContent([header])
        self.assertDecl('func', 'void', 'void', slist)

    # TODO: get rid of extra spaces
    def test_FindsFunctionStrucVoidMultiline(self):
        header = textwrap.dedent("""\
            struct ret *
            func (void);""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('func', 'struct ret  *', 'void', slist)


class ScanHeaderContentMacros(ScanHeaderContentTestCase):
    """Test parsing of macro declarations."""

    def assertDecl(self, name, decl, slist):
        self.assertEqual([name], slist)
        d = '<MACRO>\n<NAME>%s</NAME>\n%s</MACRO>\n' % (name, decl)
        self.assertEqual([d], self.decls)
        self.assertEqual([], self.types)

    def test_FindsMacroNumber(self):
        slist, doc_comments = self.scanHeaderContent([
            '#define FOO 1'
        ])
        self.assertDecl('FOO', '#define FOO 1', slist)

    def test_FindsMacroExpression(self):
        slist, doc_comments = self.scanHeaderContent([
            '#define FOO (1 << 1)'
        ])
        self.assertDecl('FOO', '#define FOO (1 << 1)', slist)

    def test_FindsMacroFunction(self):
        slist, doc_comments = self.scanHeaderContent([
            '#define FOO(x) (x << 1)'
        ])
        self.assertDecl('FOO', '#define FOO(x) (x << 1)', slist)

    # TODO: test for a few variants
    def test_IgnoresInternalMacro(self):
        slist, doc_comments = self.scanHeaderContent([
            '#define _BUG_000000b (a) (a*a)'
        ])
        self.assertNoDeclFound(slist)

    def test_FindsDocCommentForDeprecationGuard(self):
        header = textwrap.dedent("""\
            /**
             * GTKDOC_TESTER_DISABLE_DEPRECATED:
             *
             * Documentation for a deprecation guard.
             */
            #define GTKDOC_TESTER_DISABLE_DEPRECATED 1""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertEqual(1, len(doc_comments))
        self.assertIn('gtkdoc_tester_disable_deprecated', doc_comments)
        self.assertDecl('GTKDOC_TESTER_DISABLE_DEPRECATED',
                        '#define GTKDOC_TESTER_DISABLE_DEPRECATED 1', slist)


class ScanHeaderContentStructs(ScanHeaderContentTestCase):
    """Test parsing of struct declarations."""

    def assertDecl(self, name, decl, slist):
        self.assertEqual([name], slist)
        d = '<STRUCT>\n<NAME>%s</NAME>\n%s</STRUCT>\n' % (name, decl)
        self.assertEqual([d], self.decls)
        self.assertEqual([], self.types)

    def test_FindsStruct(self):
        header = textwrap.dedent("""\
            struct data {
              int test;
            };""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('data', header, slist)

    def test_FindsTypedefStruct(self):
        header = textwrap.dedent("""\
            typedef struct {
              int test;
            } Data;""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('Data', header, slist)

    def test_HandleStructWithDeprecatedMember(self):
        header = textwrap.dedent("""\
            struct data {
              int test_a;
            #ifndef GTKDOC_TESTER_DISABLE_DEPRECATED
              int deprecated;
            #endif
              int test_b;
            };""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('data', header, slist)


class ScanHeaderContentUnions(ScanHeaderContentTestCase):
    """Test parsing of union declarations."""

    def assertDecl(self, name, decl, slist):
        self.assertEqual([name], slist)
        d = '<UNION>\n<NAME>%s</NAME>\n%s</UNION>\n' % (name, decl)
        self.assertEqual([d], self.decls)
        self.assertEqual([], self.types)

    def test_FindsUnion(self):
        header = textwrap.dedent("""\
            union data {
              int i;
              float f;
            };""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('data', header, slist)

    def test_FindsTypedefUnion(self):
        header = textwrap.dedent("""\
            typedef union {
              int i;
              float f;
            } Data;""")
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('Data', header, slist)


# USER FUNCTION (aka function pointer types)


class ScanHeaderContentVariabless(ScanHeaderContentTestCase):
    """Test parsing of variable declarations."""

    def assertDecl(self, name, decl, slist):
        self.assertEqual([name], slist)
        d = '<VARIABLE>\n<NAME>%s</NAME>\n%s</VARIABLE>\n' % (name, decl)
        self.assertEqual([d], self.decls)
        self.assertEqual([], self.types)

    def test_FindsExternInt(self):
        header = 'extern int var;'
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('var', header, slist)

    def test_FindsConstInt(self):
        header = 'const int var = 42;'
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('var', header, slist)

    def test_FindsExernCharPtr(self):
        header = 'extern char* var;'
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('var', header, slist)

    def test_FindConstCharPtr(self):
        header = 'const char* var = "foo";'
        slist, doc_comments = self.scanHeaderContent(
            header.splitlines(keepends=True))
        self.assertDecl('var', header, slist)


if __name__ == '__main__':
    unittest.main()

    # from gtkdoc import common
    # common.setup_logging()
    #
    # t = ScanHeaderContentUnions()
    # t.setUp()
    # t.test_FindsUnion()
