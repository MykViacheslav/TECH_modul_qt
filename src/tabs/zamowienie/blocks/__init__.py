# src/tabs/zamowienie/blocks/__init__.py
# Bloki wydzielone z tab_nowe_zamowienie.py

from src.tabs.zamowienie.blocks.base_block import OrderFormBlock
from src.tabs.zamowienie.blocks.client_block import ClientBlock, ClientFieldCell
from src.tabs.zamowienie.blocks.order_block import OrderBlock
from src.tabs.zamowienie.blocks.quote_block import QuoteBlock
from src.tabs.zamowienie.blocks.finance_block import FinanceBlock
from src.tabs.zamowienie.blocks.walls_block import WallsBlock
from src.tabs.zamowienie.blocks.architect_block import ArchitectBlock
from src.tabs.zamowienie.blocks.actions_block import ActionsBlock

__all__ = [
    "OrderFormBlock",
    "ClientBlock",
    "ClientFieldCell",
    "OrderBlock",
    "QuoteBlock",
    "FinanceBlock",
    "WallsBlock",
    "ArchitectBlock",
    "ActionsBlock",
]
