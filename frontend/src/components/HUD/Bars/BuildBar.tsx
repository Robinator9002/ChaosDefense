// frontend/src/components/HUD/BuildBar.tsx
import type { InitialStateData } from '../../../api/types';

// --- Prop Types ---
interface BuildBarProps {
    initialState: InitialStateData | null;
}

// --- Main BuildBar Component ---
const BuildBar = ({ initialState }: BuildBarProps) => {
    if (!initialState) {
        return null; // Don't render if we don't have the buildable tower data yet
    }

    const handleTowerSelect = (towerId: string) => {
        // TODO: Implement tower selection logic.
        // This function will eventually set the 'selected tower' in a global state
        // and send a command to the backend when the player clicks on the map.
        console.log(`Selected tower: ${towerId}`);
    };

    return (
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gray-900 bg-opacity-80 p-4 flex items-center justify-center gap-4 border-t-2 border-gray-700 shadow-top">
            {/* TODO: Add tab buttons for tower categories */}

            {/* Map over the buildable towers received from the backend */}
            {initialState.buildable_towers.map((tower) => (
                <button
                    key={tower.id}
                    onClick={() => handleTowerSelect(tower.id)}
                    className="bg-gray-800 hover:bg-blue-700 border-2 border-gray-600 hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75 rounded-lg w-24 h-24 flex flex-col items-center justify-center p-2 text-white transition-all duration-150 ease-in-out transform hover:-translate-y-1"
                    title={`${tower.name} - ${tower.cost} Gold`}
                >
                    {/* Placeholder for tower icon */}
                    <div className="w-10 h-10 bg-gray-600 rounded-md mb-2"></div>
                    <span className="text-sm font-bold truncate w-full">{tower.name}</span>
                    <span className="text-xs text-yellow-400 mt-1">{tower.cost}G</span>
                </button>
            ))}
        </div>
    );
};

export default BuildBar;
