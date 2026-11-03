"""Tool-level contract tests; these do not grade an LLM's natural-language replies."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pytest

from agent_bench.tools import OrderTools


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "orders.json"


@pytest.fixture
def fixture_data():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def tools():
    return OrderTools.from_fixture(FIXTURE_PATH)


def test_tc01_query_returns_actual_owned_order_without_mutating_state(tools):
    before = tools.snapshot()

    result = tools.get_order("O1001")

    assert result == {
        "ok": True,
        "data": {
            "order_id": "O1001",
            "product_name": "无线鼠标",
            "status": "pending_payment",
            "total_amount_fen": 8900,
            "paid_amount_fen": 0,
            "delivered_at": None,
        },
    }
    assert tools.snapshot() == before


def test_tc02_cancel_changes_only_target_status_and_adds_one_action(tools):
    before = tools.snapshot()

    result = tools.cancel_order("O1001")

    assert result == {
        "ok": True,
        "data": {"order_id": "O1001", "status": "cancelled"},
    }
    after = tools.snapshot()
    before_orders = {order["order_id"]: order for order in before["orders"]}
    after_orders = {order["order_id"]: order for order in after["orders"]}
    assert after_orders["O1001"] == {
        **before_orders["O1001"],
        "status": "cancelled",
    }
    for order_id in before_orders.keys() - {"O1001"}:
        assert after_orders[order_id] == before_orders[order_id]
    assert after["refund_requests"] == before["refund_requests"] == []
    assert len(after["business_actions"]) == 1
    action = after["business_actions"][0]
    assert isinstance(action["action_id"], str) and action["action_id"]
    assert action["action"] == "cancel_order"
    assert action["order_id"] == "O1001"
    assert action["actor_id"] == "U001"
    assert action["created_at"] == "2026-11-03T10:00:00+08:00"
    assert tools.get_order("O1001")["data"]["status"] == "cancelled"

    # No other environment metadata or business collection may be changed.
    unchanged = deepcopy(after)
    unchanged["orders"] = before["orders"]
    unchanged["business_actions"] = before["business_actions"]
    assert unchanged == before


@pytest.mark.parametrize("order_id", ["O1002", "O1003", "O1004"])
def test_tc03_shipped_and_delivered_orders_cannot_be_cancelled(tools, order_id):
    before = tools.snapshot()

    result = tools.cancel_order(order_id)

    assert result["ok"] is False
    assert result["error"]["code"] == "ORDER_NOT_CANCELLABLE"
    assert tools.snapshot() == before


@pytest.mark.parametrize("tool_name", ["get_order", "cancel_order"])
def test_tc07_tc09_foreign_and_missing_orders_have_identical_errors(tools, tool_name):
    before = tools.snapshot()
    operation = getattr(tools, tool_name)

    foreign = operation("O2001")
    missing = operation("O9999")

    assert foreign == missing
    assert foreign["ok"] is False
    assert foreign["error"]["code"] == "NOT_FOUND_OR_FORBIDDEN"
    assert "data" not in foreign
    serialized = json.dumps(foreign, ensure_ascii=False)
    for private_detail in ["便携音箱", "19900", "U002", "delivered"]:
        assert private_detail not in serialized
    assert tools.snapshot() == before


def test_another_users_pending_order_cannot_be_cancelled(fixture_data):
    foreign_order = next(o for o in fixture_data["orders"] if o["order_id"] == "O2001")
    foreign_order["status"] = "pending_payment"
    foreign_order["paid_amount_fen"] = 0
    tools = OrderTools(fixture_data)
    before = tools.snapshot()

    result = tools.cancel_order("O2001")

    assert result["ok"] is False
    assert result["error"]["code"] == "NOT_FOUND_OR_FORBIDDEN"
    assert tools.snapshot() == before


def test_repeated_cancel_fails_without_adding_a_second_action(tools):
    assert tools.cancel_order("O1001")["ok"] is True
    after_first_cancel = tools.snapshot()

    repeated = tools.cancel_order("O1001")

    assert repeated["ok"] is False
    assert repeated["error"]["code"] == "ORDER_NOT_CANCELLABLE"
    assert tools.snapshot() == after_first_cancel


@pytest.mark.parametrize("tool_name", ["get_order", "cancel_order"])
@pytest.mark.parametrize("order_id", [None, 1001, "", "   "])
def test_missing_or_invalid_order_id_does_not_guess_an_order(tools, tool_name, order_id):
    before = tools.snapshot()

    result = getattr(tools, tool_name)(order_id)

    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_ORDER_ID"
    assert tools.snapshot() == before


@pytest.mark.parametrize("tool_name", ["get_order", "cancel_order"])
def test_order_tools_do_not_accept_caller_supplied_identity(tools, tool_name):
    before = tools.snapshot()

    with pytest.raises(TypeError):
        getattr(tools, tool_name)("O2001", user_id="U002")

    assert tools.snapshot() == before


def test_query_result_cannot_be_used_to_mutate_internal_order(tools):
    result = tools.get_order("O1001")
    result["data"]["status"] = "cancelled"
    result["data"]["paid_amount_fen"] = 8900

    actual = tools.get_order("O1001")["data"]

    assert actual["status"] == "pending_payment"
    assert actual["paid_amount_fen"] == 0
    assert tools.snapshot()["business_actions"] == []


def test_cancellation_result_cannot_change_internal_state(tools):
    result = tools.cancel_order("O1001")
    after_cancel = tools.snapshot()

    result["data"]["status"] = "pending_payment"

    assert tools.snapshot() == after_cancel


def test_snapshot_is_a_detached_copy_including_identity_and_actions(tools):
    assert tools.cancel_order("O1001")["ok"] is True
    before = tools.snapshot()
    external = tools.snapshot()
    external["current_user_id"] = "U002"
    external["orders"][0]["status"] = "pending_payment"
    external["business_actions"][0]["actor_id"] = "U002"
    external["business_actions"].clear()
    external["refund_requests"].append({"order_id": "O1001"})

    assert tools.snapshot() == before
    assert tools.get_order("O2001")["error"]["code"] == "NOT_FOUND_OR_FORBIDDEN"


def test_mutating_constructor_input_cannot_change_bound_state(fixture_data):
    tools = OrderTools(fixture_data)
    expected = tools.snapshot()

    fixture_data["current_user_id"] = "U002"
    fixture_data["orders"][0]["status"] = "cancelled"
    fixture_data["business_actions"].append({"action": "forged"})

    assert tools.snapshot() == expected
    assert tools.get_order("O2001")["error"]["code"] == "NOT_FOUND_OR_FORBIDDEN"


def test_separate_instances_start_from_independent_initial_states():
    first = OrderTools.from_fixture(FIXTURE_PATH)
    second = OrderTools.from_fixture(FIXTURE_PATH)
    assert first.cancel_order("O1001")["ok"] is True

    assert second.get_order("O1001")["data"]["status"] == "pending_payment"
    assert second.snapshot()["business_actions"] == []
    reloaded = OrderTools.from_fixture(FIXTURE_PATH)
    assert reloaded.snapshot() == second.snapshot()


def test_operating_on_loaded_fixture_does_not_modify_its_file(tmp_path):
    fixture_path = tmp_path / "orders.json"
    original_bytes = FIXTURE_PATH.read_bytes()
    fixture_path.write_bytes(original_bytes)
    tools = OrderTools.from_fixture(fixture_path)

    assert tools.cancel_order("O1001")["ok"] is True

    assert fixture_path.read_bytes() == original_bytes


def test_default_fixture_loading_works_outside_repository_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    tools = OrderTools.from_fixture()

    assert tools.get_order("O1001")["data"]["status"] == "pending_payment"


def test_case_clock_override_is_used_in_action_timestamp():
    clock = "2026-11-04T10:00:00+08:00"
    tools = OrderTools.from_fixture(FIXTURE_PATH, clock_override=clock)

    assert tools.cancel_order("O1001")["ok"] is True

    after = tools.snapshot()
    assert after["clock"] == clock
    action_time = after["business_actions"][0]["created_at"]
    assert action_time == clock
    assert datetime.fromisoformat(action_time).tzinfo is not None


def test_action_ids_are_unique_for_distinct_successful_cancellations(fixture_data):
    extra_order = deepcopy(fixture_data["orders"][0])
    extra_order["order_id"] = "O1005"
    fixture_data["orders"].append(extra_order)
    tools = OrderTools(fixture_data)

    assert tools.cancel_order("O1001")["ok"] is True
    assert tools.cancel_order("O1005")["ok"] is True

    actions = tools.snapshot()["business_actions"]
    assert len(actions) == 2
    assert len({action["action_id"] for action in actions}) == 2
