// frontend/src/components/HUD/Panels/TowerInfoPanel.tsx
import { useGameStore } from '../../../state/gameStore';

// --- Main TowerInfoPanel Component ---
const TowerInfoPanel = () => {
    // Select the necessary state from the global store.
    // The component will automatically re-render when these values change.
    const { selectedTowerId, buildableTowers } = useGameStore((state) => ({
        selectedTowerId: state.selectedTowerToBuild,
        buildableTowers: state.initialState?.buildable_towers,
    }));

    // If no tower is selected to be built, or if we don't have tower data yet,
    // render nothing.
    if (!selectedTowerId || !buildableTowers) {
        return null;
    }

    // Find the full data object for the selected tower.
    const towerData = buildableTowers.find((t) => t.id === selectedTowerId);

    // This is a safety check in case the ID is invalid.
    if (!towerData) {
        return null;
    }

    return (
        // This panel will appear on the right side of the screen.
        <div className="absolute top-4 right-4 w-80 bg-gray-900 bg-opacity-85 border-2 border-gray-700 rounded-lg shadow-2xl p-4 text-white font-mono flex flex-col gap-4">
            {/* Header Section */}
            <div className="flex justify-between items-center border-b-2 border-gray-700 pb-2">
                <h2 className="text-xl font-bold text-blue-300">{towerData.name}</h2>
                <span className="text-xl font-bold text-yellow-400">{towerData.cost}G</span>
            </div>

            {/* Description Section (placeholder) */}
            <div>
                <h3 className="text-md font-semibold text-gray-400 mb-1">Description</h3>
                <p className="text-sm text-gray-300">
                    {/* TODO: The full description should come from the backend config */}A standard
                    defensive emplacement. Reliable and effective against common threats.
                </p>
            </div>

            {/* Stats Section (placeholder) */}
            <div>
                <h3 className="text-md font-semibold text-gray-400 mb-2">Statistics</h3>
                <div className="flex flex-col gap-1 text-sm">
                    {/* TODO: Stats should come from the backend config */}
                    <div className="flex justify-between">
                        <span>Damage:</span> <span>10</span>
                    </div>
                    <div className="flex justify-between">
                        <span>Range:</span> <span>150</span>
                    </div>
                    <div className="flex justify-between">
                        <span>Fire Rate:</span> <span>1.2/s</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TowerInfoPanel;
