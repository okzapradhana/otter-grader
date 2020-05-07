##################################
##### Tests for otter build #####
##################################

import unittest
import os
import shutil
import testing.postgresql

from io import StringIO
from contextlib import redirect_stdout
from psycopg2 import connect, extensions
from psycopg2.errors import DuplicateTable

from otter.service.build import write_assignment_info, write_class_info, main
from otter.utils import block_print, enable_print

TEST_FILES_PATH = "test/test_service/test-build/"

parser = None
with open("bin/otter") as f:
    exec(f.read())

class TestBuild(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.postgresql = testing.postgresql.Postgresql()
        cls.conn = connect(**cls.postgresql.dsn())
        cls.conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        block_print()
        args = parser.parse_args(["service", "create"])
        args.func(args, conn=cls.conn, close_conn=False)

        args = parser.parse_args(["service", "build", TEST_FILES_PATH, "-q"])
        args.func(args, conn=cls.conn, close_conn=False) # Function has built-in assert statement for error-checking
        enable_print()

        cls.cursor = cls.conn.cursor()
        cls.cursor.execute("""INSERT INTO classes (class_id, class_name)
                                VALUES ('1234', 'dummy name')""")
        cls.cursor.execute("""INSERT INTO classes (class_id, class_name)
                                VALUES ('2345', 'dummy name')""")
        cls.cursor.execute("""INSERT INTO assignments (assignment_id, class_id, assignment_name)
                                VALUES ('dummyid', '1234', 'dummy name')""")


    def test_write_class_info(self):
        class_id = write_class_info("test_class" ,"test class", self.conn)
        self.cursor.execute("""SELECT * FROM classes
                                WHERE class_id = %s""", (class_id, ))
        assert self.cursor.rowcount == 1, "Couldn't find inserted class"


    def test_write_assignment_info(self):
        write_assignment_info("dummy_aid", 1234, "dummy class name", None, self.conn)
        write_assignment_info("dummy_aid2", 2345, "dummy class name 2", None, self.conn)
        self.cursor.execute("""SELECT * FROM classes WHERE class_id = '2345'""")
        assert self.cursor.rowcount == 1, "Couldn't find inserted assignment information for dummy_aid2"
    

    @classmethod
    def tearDownClass(cls):
        cls.cursor.close()
        cls.conn.close()
        cls.postgresql.stop()
        