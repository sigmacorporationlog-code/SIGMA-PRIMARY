from app.models import MessageTemplate, MessageCampaign, MessageRecipient, MessageDelivery, MessageConversation, WhatsAppConfiguration
from app.services.communication_engine import render_template


def test_connect_models_are_registered():
    assert MessageTemplate.__tablename__ == "message_templates"
    assert MessageCampaign.__tablename__ == "message_campaigns"
    assert MessageRecipient.__tablename__ == "message_recipients"
    assert MessageDelivery.__tablename__ == "message_deliveries"
    assert MessageConversation.__tablename__ == "message_conversations"
    assert WhatsAppConfiguration.__tablename__ == "whatsapp_configurations"


def test_template_rendering():
    assert render_template("Bonjour {{prenom}}, votre classe est {{classe}}.", {"prenom": "Awa", "classe": "CM2 A"}) == "Bonjour Awa, votre classe est CM2 A."
    assert "{{absent}}" in render_template("{{absent}}", {})
