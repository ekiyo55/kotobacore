"""実文ゴールデンセットを CI で強制する薄いラッパー.

実体は tools/quality_test/golden_set.csv + run_golden_test.py。
デモ・実運用で指摘が出るたび CSV に1行追加する運用 (2026-08-05〜)。
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "tools" / "quality_test"))


def test_golden_set_all_pass():
    from run_golden_test import main
    assert main() == 0
