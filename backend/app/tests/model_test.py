from app.models.assistant import AssistantModeType, assistant_mode_str, parse_assistant_mode
from app.models.item import Item, ItemType


def test_to_dict():
    item = Item(name="A", item_type=ItemType.Single, owner="lizec")
    d = item.to_dict()
    assert d["name"] == item.name
    assert d["item_type"] == item.item_type
    assert d["owner"] == item.owner


def test_assistant_mode():
    assert AssistantModeType.Assistant == parse_assistant_mode(assistant_mode_str(AssistantModeType.Assistant))
    assert AssistantModeType.RolePlaying == parse_assistant_mode(assistant_mode_str(AssistantModeType.RolePlaying))

    UnKnownMode = 3
    assert AssistantModeType.RolePlaying == parse_assistant_mode(assistant_mode_str(UnKnownMode))
