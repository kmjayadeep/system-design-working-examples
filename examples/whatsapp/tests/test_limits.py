from app.main import CreateChatRequest


def test_chat_participant_limit_allows_99_plus_creator():
    request = CreateChatRequest(participants=[f"user-{index}" for index in range(99)])

    assert len(request.participants) == 99
