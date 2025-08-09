// frontend/src/components/HUD/Bars/BuildBar.tsx
import { useGameStore } from '../../../state/gameStore';

// --- Main BuildBar Component ---
// This component displays the towers the player can build.
const BuildBar = () => {
    // --- State Selection ---
    // FIX: Select each piece of state individually. This is the crucial change
    // to prevent the component from entering an infinite re-render loop.
    const initialState = useGameStore((state) => state.initialState);
    const selectedTowerToBuild = useGameStore((state) => state.selectedTowerToBuild);
    const selectTowerAction = useGameStore((state) => state.selectTowerToBuild);

    // Don't render if we don't have the initial game configuration yet.
    if (!initialState) {
        return null;
    }

    // --- Action Handler ---
    // This function handles what happens when a tower button is clicked.
    // If the clicked tower is already selected, it deselects it. Otherwise,
    // it selects the new tower. This allows toggling the selection.
    const handleTowerSelect = (towerId: string) => {
        if (selectedTowerToBuild === towerId) {
            selectTowerAction(null); // Deselect if already selected
        } else {
            selectTowerAction(towerId); // Select the new tower
        }
    };

    return (
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gray-900 bg-opacity-80 p-4 flex items-center justify-center gap-4 border-t-2 border-gray-700 shadow-top">
            {/* We map over the buildable towers received from the backend */}
            {initialState.buildable_towers.map((tower) => {
                // Check if the current tower button is the one selected in our global state.
                const isSelected = selectedTowerToBuild === tower.id;
                return (
                    <button
                        key={tower.id}
                        onClick={() => handleTowerSelect(tower.id)}
                        // Dynamically apply TailwindCSS classes based on the 'isSelected' state.
                        className={`
                            bg-gray-800 border-2 rounded-lg w-24 h-24 flex flex-col items-center justify-center p-2 text-white
                            transition-all duration-150 ease-in-out transform hover:-translate-y-1
                            focus:outline-none
                            ${
                                isSelected
                                    ? 'border-yellow-400 ring-2 ring-yellow-400 ring-opacity-75 -translate-y-1'
                                    : 'border-gray-600 hover:border-blue-400'
                            }
                        `}
                        title={`${tower.name} - ${tower.cost} Gold`}
                    >
                        {/* Placeholder for tower icon */}
                        <div className="w-10 h-10 bg-gray-600 rounded-md mb-2"></div>
                        <span className="text-sm font-bold truncate w-full">{tower.name}</span>
                        <span className="text-xs text-yellow-400 mt-1">{tower.cost}G</span>
                    </button>
                );
            })}
        </div>
    );
};

export default BuildBar;
