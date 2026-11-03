"""Exercise the real CLI, including UTF-8 JSON on Windows pipes."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("command", "order_id", "expected_exit", "expected_value"),
    [
        ("get-order", "O1001", 0, "pending_payment"),
        ("cancel-order", "O1001", 0, "cancelled"),
        ("cancel-order", "O1002", 1, "ORDER_NOT_CANCELLABLE"),
        ("get-order", "O2001", 1, "NOT_FOUND_OR_FORBIDDEN"),
    ],
)
def test_cli_returns_utf8_json_and_meaningful_exit_codes(
    command, order_id, expected_exit, expected_value
):
    process = subprocess.run(
        [sys.executable, "-m", "agent_bench", command, order_id],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=15,
    )

    assert process.returncode == expected_exit, process.stderr
    assert process.stderr == ""
    result = json.loads(process.stdout)
    if expected_exit == 0:
        assert result["ok"] is True
        assert result["data"]["status"] == expected_value
        if command == "get-order":
            assert result["data"]["product_name"] == "无线鼠标"
    else:
        assert result["ok"] is False
        assert result["error"]["code"] == expected_value


def test_demo_shows_shared_state_and_keeps_original_fixture_unchanged():
    fixture_path = ROOT / "data" / "orders.json"
    before = fixture_path.read_bytes()

    process = subprocess.run(
        [sys.executable, "-m", "agent_bench", "demo"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=15,
    )

    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    steps = result["steps"]
    assert steps[0]["result"]["data"]["status"] == "pending_payment"
    assert steps[1]["result"]["data"]["status"] == "cancelled"
    assert steps[2]["result"]["data"]["status"] == "cancelled"
    assert steps[3]["result"]["error"]["code"] == "ORDER_NOT_CANCELLABLE"
    assert steps[5]["result"] == steps[6]["result"]
    assert len(result["business_actions"]) == 1
    assert result["refund_request_count"] == 0
    assert fixture_path.read_bytes() == before
