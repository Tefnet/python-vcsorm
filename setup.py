#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name = 'vcsorm',
    version = '0.1',
    url = 'http://github.com/Tefnet/python-vcsorm',
    license = 'GPL',
    description = 'Version Control System (VCS) ORM',
    author = 'Tomasz Jezierski',
    author_email = 'tomasz.jezierski@tefnet.pl',
    packages = ['vcsorm'],
    test_suite = 'tests',
    package_dir={'vcsorm': 'vcsorm'},
    package_data = {
        'vcsorm': [
            'vcsorm/*.py',
            'static/css/*.css',
            'static/js/*.js',
            'static/templates/*.html',
        ]
    },
    requires = [
        'dulwich',
        'mercurial',
    ],
    dependency_links = ['https://github.com/codeinn/vcs/tarball/master#egg=vcs-0.5.0'],
    entry_points = {
        'console_scripts': [ 'vcs_dailyreport = vcsorm.reports:VCSDailyReport.run' ]
    }
)
