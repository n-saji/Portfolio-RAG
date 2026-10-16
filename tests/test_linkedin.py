import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.import_linkedin import read_export


class LinkedInImportTests(unittest.TestCase):
    def test_only_public_career_fields_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "export.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Positions.csv", "Title,Company Name,Description,Email Address\nEngineer,Example,Public work,private@example.com\n")
                archive.writestr("Messages.csv", "Message\nDo not index me\n")
            data = read_export(path)
        self.assertEqual({"positions.csv"}, set(data))
        self.assertEqual("Engineer", data["positions.csv"][0]["Title"])
        self.assertNotIn("Email Address", data["positions.csv"][0])


if __name__ == "__main__":
    unittest.main()
