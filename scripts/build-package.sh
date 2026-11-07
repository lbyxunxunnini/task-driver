#!/usr/bin/env bash
# 从当前工作区构建完整包；只检查，不提交或发布。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
PACKAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/task-driver-package-XXXXXX")"

python3 - "$PACKAGE_DIR" <<'PY'
from pathlib import Path
import shutil
import subprocess
import sys

destination = Path(sys.argv[1])
entries = ['SKILL.md', 'README.md', 'VERSION.md', '.skillhub.json',
           'CHANGELOG.md', 'references', 'scripts', 'tests']
tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', *entries])
files = {Path(name.decode()) for name in tracked.split(b'\0') if name}
files.add(Path('scripts/build-package.sh'))
for source in sorted(files):
    target = destination / source
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
PY

cd "$PACKAGE_DIR"
bash scripts/check-contracts.sh
python3 -B -m unittest discover -s tests/workflow-control
bash scripts/release_checks/metadata.sh
printf 'package ready: %s\n' "$PACKAGE_DIR"
