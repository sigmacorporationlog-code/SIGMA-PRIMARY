from app.services.sync import decide_apply


def test_two_clients_same_base_one_applies_other_conflicts():
    first = decide_apply(0, 0)
    second = decide_apply(0, first.new_version)
    assert first.status == "applied"
    assert first.new_version == 1
    assert second.status == "conflict"
    assert second.new_version == 1


def test_rebased_client_can_apply_after_conflict_resolution():
    first = decide_apply(0, 0)
    rebased = decide_apply(first.new_version, first.new_version)
    assert rebased.status == "applied"
    assert rebased.new_version == 2
