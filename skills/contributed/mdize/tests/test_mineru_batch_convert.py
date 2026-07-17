import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "mineru_batch_convert.py"
SPEC = importlib.util.spec_from_file_location("mineru_batch_convert", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MineruBatchConvertTests(unittest.TestCase):
    def test_collect_input_files_keeps_only_supported_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("paper.pdf", "slides.pptx", "photo.png", "notes.txt"):
                (root / name).write_text("test")

            files = MODULE.collect_input_files([root])

            self.assertEqual([file.name for file in files], ["paper.pdf", "photo.png", "slides.pptx"])

    def test_token_must_come_from_environment(self):
        previous = os.environ.pop("MINERU_API_TOKEN", None)
        try:
            with self.assertRaisesRegex(ValueError, "MINERU_API_TOKEN"):
                MODULE.token_from_environment()
        finally:
            if previous is not None:
                os.environ["MINERU_API_TOKEN"] = previous


if __name__ == "__main__":
    unittest.main()
