#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='tap-kustomer',
      version='0.0.3',
      description='Singer.io tap for extracting data from the Kustomer v1.0 API',
      author='scott.coleman@bytecode.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_kustomer'],
      install_requires=[
          'backoff==1.8.0',
          'requests==2.22.0',
          'singer-python==5.8.1'
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
