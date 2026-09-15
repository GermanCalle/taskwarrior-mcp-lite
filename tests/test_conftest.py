def test_fixture_gives_a_working_isolated_database(tw, task_cli):
    task_cli("add", "only task here")
    tasks = tw.export()

    assert [task["description"] for task in tasks] == ["only task here"]


def test_each_test_gets_a_fresh_database(tw):
    assert tw.export() == []
