# This file is part of beets.
# Copyright 2014, Fabrice Laporte.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Tests for the 'bucket' plugin."""

from _common import unittest
from beetsplug import bucket
from beets import config

from helper import TestHelper


class BucketPluginTest(unittest.TestCase, TestHelper):
    def setUp(self):
        self.setup_beets()
        self.plugin = bucket.BucketPlugin()

    def tearDown(self):
        self.teardown_beets()

    def _setup_config(self, bucket_year=[], bucket_alpha=[],
                      extrapolate=False):
        config['bucket']['bucket_year'] = bucket_year
        config['bucket']['bucket_alpha'] = bucket_alpha
        config['bucket']['extrapolate'] = extrapolate
        self.plugin.setup()

    def test_year_single_year(self):
        """If a single year is given, range starts from this year and stops at
        the year preceding the one of next bucket."""
        self._setup_config(bucket_year=['1950s', '1970s'])
        self.assertEqual(self.plugin._tmpl_bucket('1959'), '1950s')
        self.assertEqual(self.plugin._tmpl_bucket('1969'), '1950s')

    def test_year_single_year_last_folder(self):
        """If a single year is given for the last bucket, extend it to current
        year."""
        self._setup_config(bucket_year=['1950', '1970'])
        self.assertEqual(self.plugin._tmpl_bucket('2014'), '1970')
        self.assertEqual(self.plugin._tmpl_bucket('2015'), '2015')

    def test_year_two_years(self):
        """Buckets can be named with the 'from-to' syntax."""
        self._setup_config(bucket_year=['1950-59', '1960-1969'])
        self.assertEqual(self.plugin._tmpl_bucket('1959'), '1950-59')
        self.assertEqual(self.plugin._tmpl_bucket('1969'), '1960-1969')

    def test_year_multiple_years(self):
        """Buckets can be named by listing all the years"""
        self._setup_config(bucket_year=['1950,51,52,53'])
        self.assertEqual(self.plugin._tmpl_bucket('1953'), '1950,51,52,53')
        self.assertEqual(self.plugin._tmpl_bucket('1974'), '1974')

    def test_year_out_of_range(self):
        """If no range match, return the year"""
        self._setup_config(bucket_year=['1950-59', '1960-69'])
        self.assertEqual(self.plugin._tmpl_bucket('1974'), '1974')
        self._setup_config(bucket_year=[])
        self.assertEqual(self.plugin._tmpl_bucket('1974'), '1974')

    def test_year_out_of_range_extrapolate(self):
        """If no defined range match, extrapolate all ranges using the most
        common syntax amongst existing buckets and return the matching one."""
        self._setup_config(bucket_year=['1950-59', '1960-69'],
                           extrapolate=True)
        self.assertEqual(self.plugin._tmpl_bucket('1914'), '1910-19')
        # pick single year format
        self._setup_config(bucket_year=['1962-81', '2002', '2012'],
                           extrapolate=True)
        self.assertEqual(self.plugin._tmpl_bucket('1983'), '1982')
        # pick from-end format
        self._setup_config(bucket_year=['1962-81', '2002', '2012-14'],
                           extrapolate=True)
        self.assertEqual(self.plugin._tmpl_bucket('1983'), '1982-01')
        # extrapolate add ranges, but never modifies existing ones
        self._setup_config(bucket_year=['1932', '1942', '1952', '1962-81',
                                        '2002'], extrapolate=True)
        self.assertEqual(self.plugin._tmpl_bucket('1975'), '1962-81')

    def test_alpha_all_chars(self):
        """Alphabet buckets can be named by listing all their chars"""
        self._setup_config(bucket_alpha=['ABCD', 'FGH', 'IJKL'])
        self.assertEqual(self.plugin._tmpl_bucket('garry'), 'FGH')

    def test_alpha_first_last_chars(self):
        """Alphabet buckets can be named by listing the 'from-to' syntax"""
        self._setup_config(bucket_alpha=['A-D', 'F-H', 'I-Z'])
        self.assertEqual(self.plugin._tmpl_bucket('garry'), 'F-H')

    def test_alpha_out_of_range(self):
        """If no range match, return the initial"""
        self._setup_config(bucket_alpha=['ABCD', 'FGH', 'IJKL'])
        self.assertEqual(self.plugin._tmpl_bucket('errol'), 'E')
        self._setup_config(bucket_alpha=[])
        self.assertEqual(self.plugin._tmpl_bucket('errol'), 'E')


def suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
