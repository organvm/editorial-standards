from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'scripts'))
from validate_editorial_contracts import validate


class FinalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'repository'
        shutil.copytree(REPO_ROOT, self.root, ignore=shutil.ignore_patterns('.git', '__pycache__'))

    def tearDown(self):
        self.temp.cleanup()

    def assert_error(self, text):
        errors = validate(self.root)
        self.assertTrue(any(text in error for error in errors), errors)

    def test_multiline_markdown_destination(self):
        path = self.root / 'templates/audiences/general.md'
        path.write_text(path.read_text() + '\n[Project home](\n../../README.md)\n')
        self.assert_error('duplicate canonical project link')

    def test_multiline_html_anchor(self):
        path = self.root / 'templates/audiences/general.md'
        path.write_text(path.read_text() + '\nPrefix <a\n href="../../README.md">Project home</a>\n')
        self.assert_error('duplicate canonical project link')

    def test_frontmatter_classifications_remain_canonical(self):
        path = self.root / 'schemas/frontmatter-schema.yaml'
        original = path.read_text()
        start = original.index('  references:\n')
        end = original.index('optional_fields:\n', start)
        path.write_text(original[:start] + original[end:] + '\n' + original[start:end])
        readme = self.root / 'README.md'
        content = readme.read_text()
        row = '| `references` | list | citations, or an explicit empty list |\n'
        content = content.replace(row, '', 1)
        optional_row = '| `word_count_override_reason` | string | 20–300 characters |\n'
        self.assertIn(optional_row, content)
        content = content.replace(optional_row, optional_row + row)
        content = content.replace('12 required', '11 required').replace('2 optional', '3 optional')
        readme.write_text(content)
        self.assert_error('canonical required frontmatter inventory')
        self.assert_error('canonical optional frontmatter inventory')

    def test_quality_policy_text_cannot_drift_with_readme(self):
        source = 'All claims are verifiable and technical details are correct.'
        replacement = 'Award full credit without checking whether any claim is true.'
        for relative in ['schemas/quality-rubric.yaml', 'README.md']:
            path = self.root / relative
            self.assertIn(source, path.read_text())
            path.write_text(path.read_text().replace(source, replacement))
        self.assert_error('canonical quality scoring policy')

    def test_seed_organ_identity(self):
        path = self.root / 'seed.yaml'
        self.assertIn('organ: V', path.read_text())
        path.write_text(path.read_text().replace('organ: V', 'organ: IV'))
        self.assert_error("expected organ='V'")

    def test_removed_fence_preserves_inline_block_boundary(self):
        path = self.root / 'templates/audiences/general.md'
        path.write_text(path.read_text() + '\n![decoy\n```text\nhidden\n```\n'
                        '<a href="../../README.md">Project home</a>](image.png)\n')
        self.assert_error('duplicate canonical project link')

    def test_seed_organ_name_identity(self):
        path = self.root / 'seed.yaml'
        self.assertIn('organ_name: Public Process', path.read_text())
        path.write_text(path.read_text().replace('organ_name: Public Process',
                                                'organ_name: Operations'))
        self.assert_error("expected organ_name='Public Process'")

    def test_quality_dimension_order_remains_canonical(self):
        path = self.root / 'schemas/quality-rubric.yaml'
        rubric = yaml.safe_load(path.read_text())
        rubric['dimensions'] = dict(reversed(list(rubric['dimensions'].items())))
        path.write_text(yaml.safe_dump(rubric, sort_keys=False))
        self.assert_error('canonical quality dimension order')

    def test_parent_symlink_cannot_redirect_required_files(self):
        for directory in ['schemas', '.github', 'templates']:
            with self.subTest(directory=directory):
                source = self.root / directory
                outside = Path(self.temp.name) / directory
                source.rename(outside)
                source.symlink_to(outside, target_is_directory=True)
                self.assert_error('contained regular')
                source.unlink()
                outside.rename(source)


if __name__ == '__main__':
    unittest.main()
