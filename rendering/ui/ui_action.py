# rendering/ui/ui_action.py
import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

# It's good practice to have a logger even in small utility files.
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """
    Defines the types of actions a UI element can trigger.

    Using an Enum provides a robust, type-safe way to identify actions,
    preventing typos and making the code more readable and maintainable
    compared to using raw strings.
    """

    # Action to select a tower from the build menu.
    SELECT_TOWER = auto()
    # Action to purchase a specific upgrade for a selected tower.
    PURCHASE_UPGRADE = auto()
    # Action to sell a selected tower for a percentage of its cost.
    SALVAGE_TOWER = auto()
    # Action to close the currently open panel (e.g., the upgrade panel).
    CLOSE_PANEL = auto()
    # --- NEW: Action to change a tower's targeting AI persona ---
    CHANGE_TARGETING_PERSONA = auto()


@dataclass(frozen=True)
class UIAction:
    """
    A structured representation of an action triggered by the UI.

    This dataclass encapsulates all information needed to process a UI event.
    Using a dataclass ensures that all actions are consistently structured,
    making the event handling logic in the UIManager cleaner and less
    error-prone. 'frozen=True' makes instances of this class immutable,
    which is a good practice for event data.
    """

    type: ActionType
    # Optional: The unique identifier for the entity (e.g., tower type or upgrade ID).
    entity_id: Optional[str] = None

    def __post_init__(self):
        """
        Validates the dataclass instance after it's been created.
        This ensures that actions that require an ID actually have one.
        """
        if self.type in (
            ActionType.SELECT_TOWER,
            ActionType.PURCHASE_UPGRADE,
            ActionType.CHANGE_TARGETING_PERSONA,  # Also requires an ID
        ):
            if self.entity_id is None:
                logger.error(
                    f"UIAction of type '{self.type.name}' requires an 'entity_id'."
                )
                raise ValueError(
                    f"UIAction of type '{self.type.name}' must have an entity_id."
                )
