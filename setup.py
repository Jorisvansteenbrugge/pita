from distutils.core import setup
from setuptools.command.test import test as TestCommand
import sys

VERSION = "1.72"
DESCRIPTION = """
pita - pita improves transcript annotation
"""
class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup (name = 'pita',
        version = VERSION,
        description = DESCRIPTION,
        author='Simon van Heeringen',
        author_email='s.vanheeringen@ncmls.ru.nl',
        license='MIT',
        packages=[
            'pita'
        ],
        scripts=[
            "scripts/pita",
            "scripts/pita_utr",
            "scripts/bed12togff3",
            "scripts/gff3tobed12",
            "scripts/flatbread",
            "scripts/breadcrumb",
        ],
        data_files=[],
        tests_require=['pytest'],
        install_requires=[
                        "SQLAlchemy",
                        "gimmemotifs",
                        "pysam < 0.8",
                        "pyyaml",
                        "HTSeq",
                        "bcbio-gff",
                        "biopython",
                        "networkx >= 1.9",
                        "numpy",
                        ],
        cmdclass = {'test': PyTest},
)
