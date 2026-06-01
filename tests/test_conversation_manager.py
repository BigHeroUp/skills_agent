from utils.conversation_manager import ConversationManager


def test_add_message_stores_content_without_attribute_error():
    manager = ConversationManager(session_id="test-session")

    message = manager.add_user_message("Mostrami un grafico per stato ticket")

    assert message.role == "user"
    assert message.content == "Mostrami un grafico per stato ticket"
    assert manager.get_last_user_message() == "Mostrami un grafico per stato ticket"
    assert manager.get_chat_history()[0]["content"] == "Mostrami un grafico per stato ticket"
