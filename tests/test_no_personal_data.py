"""Guard: nothing in this repository may carry personal data.

Text files are covered by a grep in CI, but Office files are zip archives — a name can
sit in docProps/core.xml and never appear to a plain text search. This test opens them.
Run standalone (`python tests/test_no_personal_data.py`) or under pytest.
"""
import glob, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNED = re.compile("|".join(["She" + "shunov", "sqael" + "96", "leopold" + "stern"]), re.I)
TEXT_EXT = (".py", ".md", ".R", ".bas", ".js", ".json", ".csv", ".yml", ".txt", ".cff")


def test_office_files_carry_no_personal_data():
    checked = 0
    for f in glob.glob(os.path.join(ROOT, "**", "*.xlsx"), recursive=True) + \
             glob.glob(os.path.join(ROOT, "**", "*.docx"), recursive=True):
        if os.sep + ".git" + os.sep in f:
            continue
        z = zipfile.ZipFile(f)
        for name in z.namelist():
            assert not BANNED.search(z.read(name).decode("utf-8", "ignore")), (f, name)
        checked += 1
    assert checked > 0, "no Office file found — has the workbook stopped being generated?"


def test_workbook_author_is_the_handle():
    for f in glob.glob(os.path.join(ROOT, "**", "*.xlsx"), recursive=True):
        if os.sep + ".git" + os.sep in f:
            continue
        core = zipfile.ZipFile(f).read("docProps/core.xml").decode("utf-8", "ignore")
        for who in re.findall(r"<(?:dc:creator|cp:lastModifiedBy)>([^<]*)<", core):
            assert who == "Pr0spektor", (f, who)


def test_text_files_carry_no_personal_data():
    this = os.path.abspath(__file__)
    bad = []
    for ext in TEXT_EXT:
        for f in glob.glob(os.path.join(ROOT, "**", "*" + ext), recursive=True):
            if os.sep + ".git" + os.sep in f or os.path.abspath(f) == this:
                continue
            if BANNED.search(open(f, encoding="utf-8", errors="ignore").read()):
                bad.append(os.path.relpath(f, ROOT))
    assert not bad, bad


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in fns:
        try:
            fn(); passed += 1; print("  PASS  " + fn.__name__)
        except AssertionError as e:
            failed += 1; print("  FAIL  %s: %s" % (fn.__name__, e))
    print("%d/%d tests passed." % (passed, passed + failed))
    sys.exit(1 if failed else 0)
