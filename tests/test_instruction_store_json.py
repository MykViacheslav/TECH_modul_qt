from __future__ import annotations

from src.domain.instruction_models import InstructionCardDef
from src.storage.instruction_store_json import InstructionStoreJson


def test_instruction_store_has_defaults_and_supports_crud(tmp_path, monkeypatch):
    monkeypatch.setenv("TECH_MODUL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TECH_MODUL_TESTING", "1")

    store = InstructionStoreJson(path=tmp_path / "instruction_cards.json")
    defaults = store.list_cards()
    categories = {card.category for card in defaults}
    assert "okucia" in categories
    assert "montaz" in categories

    result = store.save_new(
        InstructionCardDef(
            category="montaz",
            title="Montaz blatu test",
            when_to_use="Po ustawieniu baz",
            impact="Stabilnosc i estetyka",
            steps="Dociagnij laczniki i skontroluj poziom.",
            visualization_path="C:/wizualizacje/blat_01.png",
        )
    )
    assert result.ok is True

    cards = store.list_cards("montaz")
    match = [card for card in cards if card.title == "Montaz blatu test"]
    assert len(match) == 1

    delete_result = store.delete(match[0].instruction_id)
    assert delete_result.ok is True
    assert all(card.instruction_id != match[0].instruction_id for card in store.list_cards("montaz"))
