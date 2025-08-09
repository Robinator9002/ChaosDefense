// frontend/src/components/HUD/HUD.tsx
import { useGameStore } from '../../state/gameStore';

// --- Local Imports ---
// We now import all the child components that the HUD will manage.
import TopBar from './Bars/TopBar';
import BuildBar from './Bars/BuildBar';
import TowerInfoPanel from './Panels/TowerInfoPanel';
import UpgradePanel from './Panels/UpgradePanel';

// --- Main HUD Component ---
// This component acts as the master controller for the game's UI overlays.
// It listens to the global state to decide which panels should be visible.
const HUD = () => {
    // --- State Selection ---
    // We select the two state variables that determine which contextual
    // panel should be displayed.
    // - selectedTowerToBuild: The player has clicked a tower in the build bar.
    // - selectedEntityId: The player has clicked a tower on the map.
    const selectedTowerToBuild = useGameStore((state) => state.selectedTowerToBuild);
    const selectedEntityId = useGameStore((state) => state.selectedEntityId);

    return (
        // This div is a transparent overlay that holds all UI elements.
        // `pointer-events-none` is key: it allows mouse clicks to "pass through"
        // the container to the canvas below. Individual UI elements like buttons
        // will have `pointer-events-auto` to make them clickable again.
        <div className="absolute inset-0 pointer-events-none text-white font-mono">
            {/* --- Static UI Elements --- */}
            {/* These bars are always visible during gameplay. */}
            <div className="pointer-events-auto">
                <TopBar />
                <BuildBar />
            </div>

            {/* --- Contextual UI Panels --- */}
            {/* This is the core logic for the HUD. We conditionally render the
                correct panel based on the player's current selection state.
                This ensures that the UI is never cluttered with irrelevant info. */}
            <div className="pointer-events-auto">
                {/* If a tower is selected from the build bar, show its info. */}
                {selectedTowerToBuild && <TowerInfoPanel />}

                {/* If a tower is selected on the map, show its upgrade options. */}
                {selectedEntityId && <UpgradePanel />}
            </div>
        </div>
    );
};

export default HUD;
