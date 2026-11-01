"""Build real Hugo output with synthetic articles outside the checkout."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HUGO = os.environ.get('HUGO_BIN', 'hugo')


class BlogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='adapt-blog-test-')
        cls.site = Path(cls.tmp.name) / 'site'
        shutil.copytree(ROOT, cls.site, ignore=shutil.ignore_patterns(
            '.git', 'public', 'resources', '.hugo_build.lock', '__pycache__'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def article(self, slug, date, extra='', author='試験用著者'):
        folder = self.site / 'content/insights/blog'
        (folder / (slug + '.md')).write_text(
            f'---\ntitle: "{slug} 日本語の長いタイトルと判断の記録"\n'
            f'date: {date}\nauthor: "{author}"\ndescription: "試験用概要"\n'
            f'{extra}\n---\n\n## 試験用見出し\n\n試験用本文です。\n', encoding='utf-8')

    def build(self, *flags):
        output = Path(self.tmp.name) / ('build-' + str(len(list(Path(self.tmp.name).glob('build-*')))))
        run = subprocess.run([HUGO, '--source', str(self.site), '--destination', str(output),
                              '--gc', '--minify', *flags], capture_output=True, text=True,
                             encoding='utf-8', env={**os.environ, 'CF_PAGES_BRANCH': 'main'})
        return run, output

    def test_blog_lifecycle(self):
        run, empty = self.build()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('記事はまだ公開されていません', (empty/'insights/blog/index.html').read_text(encoding='utf-8'))
        self.article('older', '2025-01-01', 'lastmod: 2025-01-03')
        self.article('newer', '2025-02-01')
        self.article('draft-secret', '2025-03-01', 'draft: true')
        self.article('future-secret', '2099-01-01')
        run, public = self.build()
        self.assertEqual(run.returncode, 0, run.stderr)
        listing = (public/'insights/blog/index.html').read_text(encoding='utf-8')
        self.assertLess(listing.index('newer'), listing.index('older'))
        for slug in ('older', 'newer'):
            html = (public/f'insights/blog/{slug}/index.html').read_text(encoding='utf-8')
            self.assertIn('試験用著者', html)
            self.assertIn('試験用本文', html)
            self.assertIn('ブログ一覧へ', html)
            self.assertIn('公開日', html)
        older = (public/'insights/blog/older/index.html').read_text(encoding='utf-8')
        newer = (public/'insights/blog/newer/index.html').read_text(encoding='utf-8')
        self.assertIn('2025-01-03', older)
        self.assertIn('更新日', older)
        self.assertNotIn('更新日', newer)
        for path in public.rglob('*'):
            if path.suffix in ('.html', '.xml', '.json'):
                text = path.read_text(encoding='utf-8')
                self.assertNotIn('draft-secret', text, str(path))
                self.assertNotIn('future-secret', text, str(path))
        run, preview = self.build('--buildDrafts')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((preview/'insights/blog/draft-secret/index.html').exists())
        self.assertIn('下書き', (preview/'insights/blog/draft-secret/index.html').read_text(encoding='utf-8'))
        self.article('older', '2025-01-01', 'lastmod: 2025-01-01')
        run, same = self.build()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('更新日', (same/'insights/blog/older/index.html').read_text(encoding='utf-8'))
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag in ('a', 'link', 'img', 'script'):
                    self.hrefs.append(attrs.get('href') or attrs.get('src') or '')
        for page in same.rglob('*.html'):
            links = Links()
            links.feed(page.read_text(encoding='utf-8'))
            for href in links.hrefs:
                url = urlsplit(href)
                if url.scheme or url.netloc or not url.path:
                    continue
                target = (same / unquote(url.path).lstrip('/')) if url.path.startswith('/') else (page.parent / unquote(url.path))
                if target.is_dir():
                    target /= 'index.html'
                self.assertTrue(target.exists(), f'{page}: broken link {href}')
        new = subprocess.run([HUGO, 'new', 'content', 'insights/blog/archetype-secret.md',
                              '--kind', 'blog', '--source', str(self.site)],
                             capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(new.returncode, 0, new.stderr)
        generated = self.site/'content/insights/blog/archetype-secret.md'
        draft = generated.read_text(encoding='utf-8')
        self.assertIn('draft: true', draft)
        generated.write_text(draft.replace('author: ""', 'author: "試験用著者"'), encoding='utf-8')
        run, normal = self.build()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse((normal/'insights/blog/archetype-secret/index.html').exists())
        run, preview = self.build('--buildDrafts')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((preview/'insights/blog/archetype-secret/index.html').exists())
        self.article('missing-author', '2025-01-01', author='')
        run, _ = self.build()
        self.assertNotEqual(run.returncode, 0, 'Publishing without author must fail')


if __name__ == '__main__':
    unittest.main(verbosity=2)
