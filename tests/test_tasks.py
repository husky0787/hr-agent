"""Verify task classification at the persistence boundary without a database."""

import unittest
from unittest.mock import patch

from shared.tasks import create_onboarding_task


class TaskCategoryTests(unittest.TestCase):
    def test_hr_and_it_are_preserved_in_the_database_and_tool_result(self):
        for supplied, expected in (
            ("HR", "HR"), ("hr", "HR"), (" IT ", "IT"), ("it", "IT"),
            ("Team", "Team"), ("team", "Team"), ("unknown", "Team"),
        ):
            with self.subTest(category=supplied), patch("shared.tasks.ensure_db"), patch("shared.tasks.get_connection") as connection:
                conn = connection.return_value.__enter__.return_value
                cursor = conn.cursor.return_value.__enter__.return_value
                cursor.fetchone.return_value = {"id": 1}
                result = create_onboarding_task("qa-employee", "Task", 1, supplied)
                self.assertEqual(result["category"], expected)
                self.assertEqual(cursor.execute.call_args.args[1][3], expected)


if __name__ == "__main__":
    unittest.main()
