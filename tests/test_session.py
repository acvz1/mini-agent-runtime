from mini_agent.session import FileSessionStore, Session


def test_sessions_are_isolated_by_user_and_window(tmp_store: FileSessionStore):
    a1 = tmp_store.get_or_create("A", "window1")
    a2 = tmp_store.get_or_create("A", "window2")
    a1.messages.append({"role": "user", "content": "查天气并记待办"})
    a1.todos.append("带伞")
    tmp_store.save(a1)

    reloaded_a2 = tmp_store.get_or_create("A", "window2")
    reloaded_a1 = tmp_store.get_or_create("A", "window1")
    assert reloaded_a2.messages == a2.messages
    assert reloaded_a2.todos == []
    assert reloaded_a1.todos == ["带伞"]
    assert reloaded_a1.messages[-1]["content"] == "查天气并记待办"


def test_same_window_can_be_resumed(tmp_store: FileSessionStore):
    s = tmp_store.get_or_create("A", "window1")
    s.messages.append({"role": "user", "content": "先记一个待办：写周报"})
    tmp_store.save(s)

    resumed = tmp_store.get_or_create("A", "window1")
    resumed.messages.append({"role": "user", "content": "刚才那个待办完成了吗？"})
    tmp_store.save(resumed)

    again = tmp_store.get_or_create("A", "window1")
    assert [m["content"] for m in again.messages] == [
        "先记一个待办：写周报",
        "刚才那个待办完成了吗？",
    ]


def test_different_users_do_not_share_session(tmp_store: FileSessionStore):
    a = tmp_store.get_or_create("A", "window1")
    a.todos.append("A的待办")
    tmp_store.save(a)
    b = tmp_store.get_or_create("B", "window1")
    assert b.todos == []
    assert isinstance(Session(user_id="x", session_id="y"), Session)
