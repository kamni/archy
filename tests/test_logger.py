import logging
import unittest

from archy.logger import ExtraStreamHandler


class ExtraStreamHandlerTests(unittest.TestCase):
    """
    Tests for archy.logging.ExtraStreamHandler
    """

    def test_format_extra(self):
        handler = ExtraStreamHandler()
        extra = {'foo': 1, 'bar': 2}
        expected = ' | foo: 1 | bar: 2'
        self.assertEqual(expected, handler._format_extra(extra))

    def test_format_extra_no_extra(self):
        handler = ExtraStreamHandler()
        extra = {}
        expected = ''
        self.assertEqual(expected, handler._format_extra(extra))

    def test_get_extra(self):
        handler = ExtraStreamHandler()
        record = logging.LogRecord(
            name='foo',
            level=logging.DEBUG,
            pathname='/tmp/archy-test.py',
            lineno=123,
            msg='This is a test',
            args=(),
            exc_info=(),
        )
        record.__dict__['foo'] = 1
        record.__dict__['bar'] = 2
        expected = {'foo': 1, 'bar': 2}
        self.assertEqual(expected, handler._get_extra(record))

    def test_get_extra_no_extra(self):
        handler = ExtraStreamHandler()
        record = logging.LogRecord(
            name='foo',
            level=logging.DEBUG,
            pathname='/tmp/archy-test.py',
            lineno=123,
            msg='This is a test',
            args=(),
            exc_info=(),
        )
        expected = {}
        self.assertEqual(expected, handler._get_extra(record))

    def test_format(self):
        handler = ExtraStreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        record = logging.LogRecord(
            name='foo',
            level=logging.DEBUG,
            pathname='/tmp/archy-test.py',
            lineno=123,
            msg='This is a test',
            args=(),
            exc_info=(),
        )
        record.__dict__['foo'] = 1
        record.__dict__['bar'] = 2
        expected = 'DEBUG: This is a test | foo: 1 | bar: 2'
        self.assertEqual(expected, handler.format(record))


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
