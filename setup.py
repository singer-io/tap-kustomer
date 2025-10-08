#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-kustomer',
      version='1.2.0',
      description='Singer.io tap for extracting data from the Kustomer v1.0 API',
      author='scott.coleman@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_kustomer'],
      install_requires=[
          'backoff==2.2.1',
          'requests==2.32.4',
          'singer-python==6.1.1'
      ],
      extras_require={
        'dev': [
            'pylint',
            'ipdb'
        ]
      },
      entry_points='''
          [console_scripts]
          tap-kustomer=tap_kustomer:main
      ''',
      packages=find_packages(),
      package_data={
          'tap_kustomer': [
              'schemas/*.json',
              'tests/*.py'
          ]
      })