// frontend/src/components/HUD/Bars/BuildBar.tsx
import { useGameStore } from '../../../state/gameStore';

// --- Main BuildBar Component ---
const BuildBar = () => {
    // Select both the data we need to display and the action we need to perform from the global store.
    const {
        initialState,
        selectedTowerToBuild,
        selectTowerToBuild: selectTowerAction,
    } = useGameStore((state) => ({
        initialState: state.initialState,
        selectedTowerToBuild: state.selectedTowerToBuild,
        selectTowerToBuild: state.selectTowerToBuild,
    }));

    if (!initialState) {
        // Don't render if we don't have the buildable tower data yet.
        return null;
    }

    return (
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gray-900 bg-opacity-80 p-4 flex items-center justify-center gap-4 border-t-2 border-gray-700 shadow-top">
            {/* TODO: Add tab buttons for tower categories */}

            {/* Map over the buildable towers received from the backend */}
            {initialState.buildable_towers.map((tower) => {
                // Check if the current tower button is the one selected in our global state.
                const isSelected = selectedTowerToBuild === tower.id;
                return (
                    <button
                        key={tower.id}
                        onClick={() => selectTowerAction(tower.id)}
                        // Dynamically apply TailwindCSS classes based on the 'isSelected' state.
                        className={`
              bg-gray-800 border-2 rounded-lg w-24 h-24 flex flex-col items-center justify-center p-2 text-white
              transition-all duration-150 ease-in-out transform hover:-translate-y-1
              focus:outline-none
              ${
                  isSelected
                      ? 'border-yellow-400 ring-2 ring-yellow-400 ring-opacity-75 -translate-y-1'
                      : // A more subtle hover effect for non-selected items.
                        'border-gray-600 hover:border-blue-400'
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
