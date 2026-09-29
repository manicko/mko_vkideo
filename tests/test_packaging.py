"""Release check for the build artefacts: the archives must match the manifest.

A source distribution exists so that someone can build, test and run this
project from the archive alone. That only holds if the archive holds exactly
what the manifest declares, so this module builds both artefacts into a
temporary directory and asserts their entry sets. The check is an exact
entry-set assertion rather than a size ratio: one unexpected file fails it.

Network
-------
Building needs the build backend (hatchling), which ``uv build`` resolves into
an isolated build environment and may fetch from the package index. When the
backend is already cached no request is made; when it is not, a machine without
network access cannot build.

A build error is therefore reported differently depending on where the module
runs, because the two environments need different answers:

* **Off a CI runner** (``CI`` unset) a network build failure **skips with a
  reason**, so a developer working without a network gets a clear account of
  what was not checked instead of a spurious failure.
* **On a CI runner** (``CI`` set, which is what the release gate is) the same
  network build failure **fails**. The skip is raised from a module-scoped
  fixture, so it skips every test in the module and pytest still exits 0; a PyPI
  outage would then report the release gate green without a single assertion
  having run. A skip that nothing distinguishes from a pass is not a report.

A build error that is not a network failure **fails** in both environments, and
so does a run in which the artefacts were built and then did not match the
manifest. A missing ``uv`` skips in both environments; that path is not part of
the network rule and is unchanged.
"""

import os
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_TIMEOUT_SECONDS = 600

# The runtime data file loaded by the Playwright browser layer. It is named in
# both hatch build targets so its presence is stated, not implied.
STEALTH_SCRIPT = "stealth.min.js"
STEALTH_SDIST_ENTRY = f"src/vkdownloader/{STEALTH_SCRIPT}"
STEALTH_WHEEL_ENTRY = f"vkdownloader/{STEALTH_SCRIPT}"

# Entries hatchling adds to every sdist on its own, whatever the include list
# says. Established empirically from a real build, not assumed: `.gitignore` is
# always shipped so the archive keeps building the same way, and `PKG-INFO` is
# the PEP 517 metadata the builder generates.
BUILDER_ADDED_SDIST_ENTRIES = frozenset({".gitignore", "PKG-INFO"})

# What `[tool.hatch.build.targets.sdist] include` is meant to ship, with the
# builder-added entries removed. Adding a source file, a test or a document
# means adding it here in the same change.
EXPECTED_SDIST_ENTRIES = frozenset(
    {
        ".env.example",
        ".python-version",
        "README.md",
        "docs/STRUCT.md",
        "docs/error-handling-logging-research-2025-2026.md",
        "docs/00-overview/doc-maintenance-rules.md",
        "docs/01-tools/api-reference.md",
        "docs/01-tools/installation.md",
        "docs/01-tools/quality-selection.md",
        "docs/01-tools/vkdownloader-overview.md",
        "docs/11-guides/configuration.md",
        "docs/11-guides/vkdownloader-limitations.md",
        "docs/99-reference/ast-editor.md",
        "docs/99-reference/cli-reference-clean.md",
        "docs/99-reference/cli-reference.md",
        "docs/99-reference/morfx-tools.md",
        "pyproject.toml",
        "src/vkdownloader/__init__.py",
        "src/vkdownloader/__main__.py",
        "src/vkdownloader/cli.py",
        "src/vkdownloader/config.py",
        "src/vkdownloader/exceptions.py",
        "src/vkdownloader/infrastructure/__init__.py",
        "src/vkdownloader/infrastructure/browser.py",
        "src/vkdownloader/infrastructure/network_monitor.py",
        "src/vkdownloader/models/__init__.py",
        "src/vkdownloader/models/dtos.py",
        "src/vkdownloader/models/enums.py",
        "src/vkdownloader/models/video.py",
        "src/vkdownloader/services/__init__.py",
        "src/vkdownloader/services/batch_downloader.py",
        "src/vkdownloader/services/concurrency.py",
        "src/vkdownloader/services/cookies.py",
        "src/vkdownloader/services/downloader.py",
        "src/vkdownloader/services/downloader_throttle.py",
        "src/vkdownloader/services/extractor.py",
        "src/vkdownloader/services/ffmpeg_utils.py",
        "src/vkdownloader/services/progress_display.py",
        "src/vkdownloader/services/quality.py",
        "src/vkdownloader/services/segment_downloader.py",
        "src/vkdownloader/services/signal_handlers.py",
        "src/vkdownloader/services/ytdlp_downloader.py",
        "src/vkdownloader/stealth.min.js",
        "src/vkdownloader/utils/__init__.py",
        "src/vkdownloader/utils/correlation.py",
        "src/vkdownloader/utils/formatting.py",
        "src/vkdownloader/utils/security.py",
        "src/vkdownloader/utils/url_sanitizer.py",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/integration/__init__.py",
        "tests/test_batch_downloader.py",
        "tests/test_browser_infrastructure.py",
        "tests/test_cli.py",
        "tests/test_config.py",
        "tests/test_cookies.py",
        "tests/test_correlation.py",
        "tests/test_downloader.py",
        "tests/test_downloader_throttle.py",
        "tests/test_exceptions.py",
        "tests/test_extractor.py",
        "tests/test_ffmpeg_utils.py",
        "tests/test_hls_downloader.py",
        "tests/test_models.py",
        "tests/test_packaging.py",
        "tests/test_progress_display.py",
        "tests/test_quality_selector.py",
        "tests/test_security.py",
        "tests/test_segment_downloader.py",
        "tests/test_url_sanitizer.py",
        "uv.lock",
    }
)

# The wheel payload, excluding the versioned `.dist-info` directory, which the
# builder names from the project version. The wheel was previously correct only
# by accident - the builder's default swept the whole package directory - so
# its entry set is pinned here as well.
EXPECTED_WHEEL_ENTRIES = frozenset(
    {
        "vkdownloader/__init__.py",
        "vkdownloader/__main__.py",
        "vkdownloader/cli.py",
        "vkdownloader/config.py",
        "vkdownloader/exceptions.py",
        "vkdownloader/infrastructure/__init__.py",
        "vkdownloader/infrastructure/browser.py",
        "vkdownloader/infrastructure/network_monitor.py",
        "vkdownloader/models/__init__.py",
        "vkdownloader/models/dtos.py",
        "vkdownloader/models/enums.py",
        "vkdownloader/models/video.py",
        "vkdownloader/services/__init__.py",
        "vkdownloader/services/batch_downloader.py",
        "vkdownloader/services/concurrency.py",
        "vkdownloader/services/cookies.py",
        "vkdownloader/services/downloader.py",
        "vkdownloader/services/downloader_throttle.py",
        "vkdownloader/services/extractor.py",
        "vkdownloader/services/ffmpeg_utils.py",
        "vkdownloader/services/progress_display.py",
        "vkdownloader/services/quality.py",
        "vkdownloader/services/segment_downloader.py",
        "vkdownloader/services/signal_handlers.py",
        "vkdownloader/services/ytdlp_downloader.py",
        "vkdownloader/stealth.min.js",
        "vkdownloader/utils/__init__.py",
        "vkdownloader/utils/correlation.py",
        "vkdownloader/utils/formatting.py",
        "vkdownloader/utils/security.py",
        "vkdownloader/utils/url_sanitizer.py",
    }
)

EXPECTED_DIST_INFO_ENTRIES = frozenset({"METADATA", "RECORD", "WHEEL", "entry_points.txt"})

# Trees and files that must never ship. Each was measured in the source
# distribution before the manifest declared an allow-list.
FORBIDDEN_SDIST_PREFIXES = (
    ".ai/",  # the audit corpus: findings, plans, research, phase catalogue
    ".kilo/",  # agent worktrees holding a second copy of src/, plus node_modules
    ".github/",
)
FORBIDDEN_SDIST_ENTRIES = (
    "urls.txt",  # a user's working file: untracked and not ignored
    "stage_and_commit.bat",
    "cli_ruff_output.txt",
    "temp_tests_output.txt",
    "%PYFILE%",
    "Continue",
    "Continue=SilentlyContinue",
    "ErrorPreference=SilentlyContinue",
)

_NETWORK_MARKERS = (
    "failed to fetch",
    "error sending request",
    "dns error",
    "could not resolve",
    "connection refused",
    "connection reset",
    "connection timed out",
    "timed out",
    "network",
    "offline",
    "no such host",
)


class BuiltArtefacts:
    """Paths to the sdist and the wheel built by a single test run."""

    def __init__(self, sdist: Path, wheel: Path) -> None:
        self.sdist = sdist
        self.wheel = wheel


def _running_on_ci() -> bool:
    """Return True when the suite runs on a CI runner.

    GitHub Actions sets ``CI`` on every runner, so its presence is the signal
    that the result is a release decision about somebody else's checkout rather
    than a developer's local observation of their own machine.
    """
    return os.environ.get("CI", "").strip().lower() not in {"", "0", "false"}


class BuildOutcome(StrEnum):
    """What the module reports when the artefacts could not be built."""

    FAILED = "failed"
    SKIPPED = "skipped"


def _report_build_failure(target: str, stdout: str, stderr: str) -> BuildOutcome:
    """Fail or skip on a build error, according to the cause and the environment.

    The two cases are separated from the subprocess call so the decision can be
    exercised directly, on a real build error, without a nested pytest run.

    The outcome is **returned** rather than only raised. A test that asserts
    ``pytest.raises(Failed)`` cannot detect a skip: ``Skipped`` is not a
    ``Failed``, so the ``raises`` block lets it escape and pytest reports the
    test as skipped. That is the same "reports success while asserting nothing"
    defect this function exists to close, reintroduced inside its own test, so
    the outcome is captured as a value and asserted on directly.
    """
    output = f"{stdout}\n{stderr}"
    if not any(marker in output.lower() for marker in _NETWORK_MARKERS):
        pytest.fail(f"`uv build {target}` failed:\n{output}")
    if not _running_on_ci():
        pytest.skip(f"`uv build {target}` needs the network and could not reach it:\n{output}")
    pytest.fail(
        f"`uv build {target}` needs the network and could not reach it. On a CI runner this "
        f"is a failure, not a skip: a skip here would let the release gate report success "
        f"with nothing checked.\n{output}"
    )


def _build_failure_outcome(target: str, stdout: str, stderr: str) -> BuildOutcome:
    """Run `_report_build_failure` and report which outcome it produced.

    Both pytest outcomes are caught, so the caller receives a value to assert on
    rather than an exception that would abort the test before it asserts.
    """
    try:
        _report_build_failure(target, stdout, stderr)
    except pytest.fail.Exception:
        return BuildOutcome.FAILED
    except pytest.skip.Exception:
        return BuildOutcome.SKIPPED
    return pytest.fail(f"`uv build {target}` reported neither a failure nor a skip")


@contextmanager
def _with_ci(value: str | None) -> Iterator[None]:
    """Run the block with `CI` set to `value`, or unset when `value` is None.

    The variable is restored afterwards, so these tests decide the environment
    for themselves instead of inheriting whatever the developer or the runner
    exported - which is the same isolation defect D-10 records for the suite.
    """
    previous = os.environ.get("CI")
    if value is None:
        os.environ.pop("CI", None)
    else:
        os.environ["CI"] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CI", None)
        else:
            os.environ["CI"] = previous


def _run_build(target: str, out_dir: Path) -> None:
    """Build one target into `out_dir`, or report the error that stopped it."""
    if shutil.which("uv") is None:
        pytest.skip("uv is not installed, so the packaging artefacts cannot be built")

    completed = subprocess.run(
        ["uv", "build", target, "--out-dir", str(out_dir)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode == 0:
        return

    _report_build_failure(target, completed.stdout, completed.stderr)


def _only_artefact(directory: Path, suffix: str) -> Path:
    """Return the single built artefact with `suffix` inside `directory`."""
    found = sorted(directory.glob(f"*{suffix}"))
    if not found:
        pytest.fail(f"`uv build` produced no {suffix} artefact in {directory}")
    return found[0]


def _project_entries() -> frozenset[str]:
    """Return the top-level entries of the project, to prove nothing is written here."""
    return frozenset(path.name for path in PROJECT_ROOT.iterdir())


def _sdist_entries(archive: Path) -> set[str]:
    """Return the archive member paths, relative to the distribution root."""
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
    roots = {member.name.split("/", 1)[0] for member in members}
    if len(roots) != 1:
        pytest.fail(f"expected a single distribution root in {archive}, found {sorted(roots)}")
    root = f"{roots.pop()}/"
    return {member.name[len(root) :] for member in members if member.isfile()}


def _wheel_entries(archive: Path) -> tuple[set[str], set[str]]:
    """Return the wheel payload paths and the `.dist-info` member names."""
    with zipfile.ZipFile(archive) as wheel:
        names = [name for name in wheel.namelist() if not name.endswith("/")]
    payload = {name for name in names if ".dist-info/" not in name}
    dist_info = {name.split(".dist-info/", 1)[1] for name in names if ".dist-info/" in name}
    return payload, dist_info


def _entry_set_difference(expected: frozenset[str], actual: set[str], what: str) -> str:
    """Describe how `actual` differs from `expected`, or return an empty string."""
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    if not unexpected and not missing:
        return ""
    return (
        f"{what} does not match the manifest.\n"
        f"  unexpected ({len(unexpected)}): {unexpected}\n"
        f"  missing     ({len(missing)}): {missing}\n"
        f"  actual count: {len(actual)}, expected count: {len(expected)}"
    )


def _manifest() -> str:
    """Return the manifest text."""
    return (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _hatch_target(target: str) -> dict[str, object]:
    """Return the parsed `[tool.hatch.build.targets.<target>]` table.

    The table is parsed, not read as text, so a value can only be satisfied by a
    key the builder actually reads. A substring search over the section text is
    satisfied just as well by a comment, which means the assertion reports a
    guarantee the manifest does not make.
    """
    manifest = tomllib.loads(_manifest())
    targets = manifest.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {})
    table = targets.get(target)
    assert isinstance(table, dict), f"the manifest has no [tool.hatch.build.targets.{target}] table"
    return table


def _declared_paths(target: str, key: str) -> list[str]:
    """Return the paths a hatch build target declares under `key`."""
    value = _hatch_target(target).get(key)
    assert isinstance(value, list), f"the {target} target declares no {key} list"
    return [str(entry) for entry in value]


@pytest.fixture(scope="module")
def artefacts() -> Iterator[BuiltArtefacts]:
    """Build both artefacts into a temporary directory outside the repository."""
    before = _project_entries()
    out_dir = Path(tempfile.mkdtemp(prefix="vkdownloader-packaging-"))
    assert not out_dir.is_relative_to(PROJECT_ROOT), "the build must not run inside the repository"
    try:
        _run_build("--sdist", out_dir)
        _run_build("--wheel", out_dir)
        yield BuiltArtefacts(
            sdist=_only_artefact(out_dir, ".tar.gz"),
            wheel=_only_artefact(out_dir, ".whl"),
        )
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)

    assert _project_entries() == before, (
        "building the artefacts must leave the repository untouched"
    )


def test_sdist_entry_set_matches_the_manifest(artefacts: BuiltArtefacts) -> None:
    """The source distribution holds exactly the declared set, nothing more."""
    expected = EXPECTED_SDIST_ENTRIES | BUILDER_ADDED_SDIST_ENTRIES
    actual = _sdist_entries(artefacts.sdist)
    difference = _entry_set_difference(expected, actual, "The sdist")
    assert not difference, difference


def test_sdist_entry_count_matches_the_manifest(artefacts: BuiltArtefacts) -> None:
    """The source distribution entry count is the one measured when the fix landed."""
    expected = len(EXPECTED_SDIST_ENTRIES) + len(BUILDER_ADDED_SDIST_ENTRIES)
    actual = len(_sdist_entries(artefacts.sdist))
    assert actual == expected, f"the sdist holds {actual} entries, the manifest declares {expected}"


def test_sdist_ships_no_unwanted_trees(artefacts: BuiltArtefacts) -> None:
    """No vendored dependency tree, no worktree, no audit corpus, no user data."""
    entries = _sdist_entries(artefacts.sdist)

    for prefix in FORBIDDEN_SDIST_PREFIXES:
        offenders = sorted(entry for entry in entries if entry.startswith(prefix))
        assert not offenders, f"the sdist must not ship {prefix}: {offenders}"

    for entry in FORBIDDEN_SDIST_ENTRIES:
        assert entry not in entries, f"the sdist must not ship {entry}"


def test_sdist_ships_the_runtime_data_file(artefacts: BuiltArtefacts) -> None:
    """The stealth script the browser layer loads at runtime is in the sdist."""
    assert STEALTH_SDIST_ENTRY in _sdist_entries(artefacts.sdist)


def test_wheel_entry_set_matches_the_manifest(artefacts: BuiltArtefacts) -> None:
    """The wheel holds exactly the package, so it stops being correct by accident."""
    payload, dist_info = _wheel_entries(artefacts.wheel)
    difference = _entry_set_difference(EXPECTED_WHEEL_ENTRIES, payload, "The wheel")
    assert not difference, difference
    assert dist_info == EXPECTED_DIST_INFO_ENTRIES, (
        f"unexpected dist-info entries: {sorted(dist_info)}"
    )


def test_wheel_ships_the_runtime_data_file(artefacts: BuiltArtefacts) -> None:
    """The stealth script the browser layer loads at runtime is in the wheel."""
    payload, _ = _wheel_entries(artefacts.wheel)
    assert STEALTH_WHEEL_ENTRY in payload


def test_manifest_declares_an_allow_list_for_the_sdist() -> None:
    """The sdist target declares an include list; an exclude list is not a substitute.

    Only the presence of the allow-list is asserted, against the parsed table. A
    future maintainer adding a legitimate ``exclude`` entry alongside ``include``
    is not a defect, so the test does not forbid one. An exclude-only manifest
    declares no ``include`` key and fails the assertion below on its own.
    """
    assert "include" in _hatch_target("sdist")


def test_manifest_names_the_runtime_data_file_in_both_targets() -> None:
    """The manifest declares the runtime data file in the sdist and in the wheel.

    Asserted against the parsed ``include`` and ``artifacts`` lists, not against
    the section text. A substring search is satisfied by the explanatory comment
    that sits in the same section, so deleting the functional declaration while
    leaving the prose would leave this test green: it would then assert a
    guarantee the manifest no longer makes. Both lists are compared as declared
    paths, so only an entry the builder acts on can satisfy the assertion.
    """
    sdist_paths = _declared_paths("sdist", "include")
    wheel_paths = _declared_paths("wheel", "artifacts")

    assert f"/{STEALTH_SDIST_ENTRY}" in sdist_paths, (
        f"the sdist include list does not declare {STEALTH_SDIST_ENTRY}: {sdist_paths}"
    )
    assert f"src/vkdownloader/{STEALTH_SCRIPT}" in wheel_paths, (
        f"the wheel artifacts list does not declare src/vkdownloader/{STEALTH_SCRIPT}: "
        f"{wheel_paths}"
    )


def test_manifest_declares_the_runtime_data_file_as_a_listed_path_not_only_prose() -> None:
    """Removing the declarations fails this test, which the prose cannot satisfy.

    The mutation is applied to a copy of the manifest, so this asserts the
    property directly rather than inferring it: with the functional declarations
    removed and the comments left in place, the same assertion must fail.
    """
    manifest = _manifest()
    kept = [
        line
        for line in manifest.splitlines()
        if line.strip() != f'"/{STEALTH_SDIST_ENTRY}",'
        and line.strip() != f'artifacts = ["src/vkdownloader/{STEALTH_SCRIPT}"]'
    ]
    stripped = "\n".join(kept) + "\n"
    assert stripped != manifest, "the mutation removed nothing, so this test proves nothing"

    parsed = tomllib.loads(stripped)["tool"]["hatch"]["build"]["targets"]
    sdist_paths = [str(entry) for entry in parsed["sdist"]["include"]]
    wheel_paths = [str(entry) for entry in parsed["wheel"].get("artifacts", [])]

    assert STEALTH_SCRIPT in stripped, "the comment mentioning the file must still be present"
    assert f"/{STEALTH_SDIST_ENTRY}" not in sdist_paths
    assert f"src/vkdownloader/{STEALTH_SCRIPT}" not in wheel_paths


NETWORK_BUILD_ERROR = "error: failed to fetch https://pypi.org/simple/hatchling/"
NON_NETWORK_BUILD_ERROR = "error: Invalid distribution: no README"


def test_a_build_failure_that_is_not_a_network_error_fails_everywhere() -> None:
    """A non-network build error fails on a runner and on a developer machine."""
    for ci_value in ("true", None):
        with _with_ci(ci_value):
            assert _build_failure_outcome("--sdist", "", NON_NETWORK_BUILD_ERROR) is (
                BuildOutcome.FAILED
            )


def test_a_network_build_failure_fails_on_a_ci_runner() -> None:
    """On a runner a network build failure fails, so the gate cannot go green.

    Before this rule existed, the failure skipped the module from a module-scoped
    fixture and pytest exited 0: a PyPI outage reported the release gate green
    with nothing checked. `CI` is what distinguishes a runner from a laptop.
    """
    with _with_ci("true"):
        assert _build_failure_outcome("--sdist", "", NETWORK_BUILD_ERROR) is BuildOutcome.FAILED


def test_a_network_build_failure_skips_on_a_developer_machine() -> None:
    """Off a runner the same failure skips, so an offline laptop can still run this."""
    with _with_ci(None):
        assert _build_failure_outcome("--sdist", "", NETWORK_BUILD_ERROR) is BuildOutcome.SKIPPED


def test_the_ci_variable_is_what_selects_the_outcome() -> None:
    """The two environments differ only by `CI`; nothing else decides the outcome.

    This is the assertion the two tests above cannot make on their own: that the
    discrimination is driven by the environment variable and not by, say, the
    order the tests happen to run in or by a value cached at import time.
    """
    outcomes = set()
    for ci_value in ("true", "false", "", None):
        with _with_ci(ci_value):
            outcomes.add(_build_failure_outcome("--sdist", "", NETWORK_BUILD_ERROR))
    assert outcomes == {BuildOutcome.FAILED, BuildOutcome.SKIPPED}, (
        f"the CI variable did not select the outcome: {sorted(outcomes)}"
    )


def test_configuration_template_ships_no_secret() -> None:
    """The shipped `.env.example` is a template: no uncommented assignment."""
    assignments = [
        line
        for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert not assignments, f".env.example must hold only commented settings, found: {assignments}"
