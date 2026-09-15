import pytest

from taskwarrior_mcp_lite.errors import TaskNotFound


def test_add_returns_the_created_task(tw):
    task = tw.add("buy milk")

    assert task["description"] == "buy milk"
    assert task["status"] == "pending"
    assert "uuid" in task


def test_add_accepts_tags(tw):
    task = tw.add("tagged", tags=["home", "errand"])

    assert sorted(task["tags"]) == ["errand", "home"]


def test_add_rejects_a_description_starting_with_rc(tw):
    with pytest.raises(ValueError, match="rc\\."):
        tw.add("rc.data.location=/tmp/elsewhere")


def test_get_resolves_a_short_id(tw):
    created = tw.add("findable")

    assert tw.get(created["id"])["uuid"] == created["uuid"]


def test_get_resolves_a_uuid_prefix(tw):
    created = tw.add("findable")

    assert tw.get(created["uuid"][:8])["uuid"] == created["uuid"]


def test_get_raises_for_an_unknown_reference(tw):
    with pytest.raises(TaskNotFound):
        tw.get("99999")


def test_modify_changes_only_what_it_is_given(tw):
    created = tw.add("original", project="alpha")

    modified = tw.modify(created["uuid"], description="renamed")

    assert modified["description"] == "renamed"
    assert modified["project"] == "alpha"


def test_start_and_stop_toggle_the_timer(tw):
    created = tw.add("timed")

    assert tw.start(created["uuid"]).get("start")
    assert not tw.stop(created["uuid"]).get("start")


def test_done_marks_the_task_completed(tw):
    created = tw.add("finish me")

    assert tw.done(created["uuid"])["status"] == "completed"


def test_delete_marks_the_task_deleted(tw):
    created = tw.add("remove me")

    assert tw.delete(created["uuid"])["status"] == "deleted"


def test_delete_reports_success_despite_the_silent_confirmation_bug(tw):
    # Some Taskwarrior builds exit 0 on `delete` without actually deleting when a
    # confirmation prompt is suppressed. The returned record, re-read afterwards,
    # is what proves the change landed — the exit status alone does not.
    created = tw.add("remove me")

    tw.delete(created["uuid"])

    assert tw.get(created["uuid"])["status"] == "deleted"


def test_done_refuses_a_short_id(tw):
    tw.add("some task")

    with pytest.raises(ValueError, match="not a UUID"):
        tw.done("1")


def test_delete_refuses_a_short_id(tw):
    tw.add("some task")

    with pytest.raises(ValueError, match="not a UUID"):
        tw.delete("1")


@pytest.mark.parametrize("short_id", ["3", "42", "1234567"])
def test_done_refuses_short_ids_of_various_lengths(tw, short_id):
    with pytest.raises(ValueError, match="not a UUID"):
        tw.done(short_id)


@pytest.mark.parametrize("short_id", ["3", "42", "1234567"])
def test_delete_refuses_short_ids_of_various_lengths(tw, short_id):
    with pytest.raises(ValueError, match="not a UUID"):
        tw.delete(short_id)


@pytest.mark.parametrize("wildcard", ["-", "----", "--------", "-" * 33])
def test_require_uuid_rejects_hyphen_heavy_wildcards(tw, wildcard):
    with pytest.raises(ValueError, match="not a UUID"):
        tw.done(wildcard)


def test_require_uuid_accepts_an_all_digit_uuid_prefix(tw):
    # A UUID prefix can be all digits, which must not be mistaken for a short ID.
    created = tw.add("numeric prefix")
    numeric_prefix = "12345678"

    with pytest.raises(TaskNotFound):
        tw.done(numeric_prefix)

    assert tw.get(created["uuid"])["status"] == "pending"


def test_delete_does_not_act_on_an_arbitrary_task_via_a_wildcard(tw):
    tw.add("innocent bystander")

    with pytest.raises(ValueError):
        tw.delete("--------")

    assert tw.export("status:pending")


def _export_matching_everything(tw, monkeypatch):
    every_task = tw.export()
    monkeypatch.setattr(tw, "export", lambda *filters: every_task)


def test_done_raises_rather_than_pick_one_of_several_matches(tw, monkeypatch):
    created = tw.add("first")
    tw.add("second")
    _export_matching_everything(tw, monkeypatch)

    with pytest.raises(ValueError, match="matches"):
        tw.done(created["uuid"])


def test_delete_raises_rather_than_pick_one_of_several_matches(tw, monkeypatch):
    created = tw.add("first")
    tw.add("second")
    _export_matching_everything(tw, monkeypatch)

    with pytest.raises(ValueError, match="matches"):
        tw.delete(created["uuid"])


def test_projects_lists_distinct_projects(tw):
    tw.add("one", project="alpha")
    tw.add("two", project="alpha")
    tw.add("three", project="beta")
    tw.add("loose")

    assert tw.projects() == ["alpha", "beta"]
