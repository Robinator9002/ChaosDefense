// frontend/src/components/HUD/Bars/BuildBar.tsx
import { useGameStore } from '../../../state/gameStore';

const BuildBar = () => {
    const initialState = useGameStore((state) => state.initialState);
    const selectedTowerToBuild = useGameStore((state) => state.selectedTowerToBuild);
    const selectTowerAction = useGameStore((state) => state.selectTowerToBuild);

    if (!initialState) {
        return null;
    }

    const handleTowerSelect = (towerId: string) => {
        if (selectedTowerToBuild === towerId) {
            selectTowerAction(null);
        } else {
            selectTowerAction(towerId);
        }
    };

    // STYLING FIX: The bar is now positioned at the bottom of the screen.
    // It uses a custom background color and a top shadow for depth.
    return (
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 mb-4">
            <div className="flex items-center justify-center gap-4 bg-panel-primary/90 p-4 rounded-xl border-2 border-border-primary shadow-top">
                {initialState.buildable_towers.map((tower) => {
                    const isSelected = selectedTowerToBuild === tower.id;
                    return (
                        <button
                            key={tower.id}
                            onClick={() => handleTowerSelect(tower.id)}
                            // STYLING FIX: Buttons now use theme colors for consistency.
                            // The selected state is much more prominent.
                            className={`
                                bg-panel-secondary border-2 rounded-lg w-24 h-24 flex flex-col items-center justify-center p-2
                                transition-all duration-150 ease-in-out transform hover:-translate-y-1
                                focus:outline-none
                                ${
                                    isSelected
                                        ? 'border-accent-yellow ring-2 ring-accent-yellow'
                                        : 'border-border-primary hover:border-accent-blue'
                                }
                            `}
                            title={`${tower.name} - ${tower.cost} Gold`}
                        >
                            {/* Placeholder for tower icon */}
                            <div className="w-10 h-10 bg-background rounded-md mb-2"></div>
                            <span className="text-sm font-bold truncate w-full text-text-primary">
                                {tower.name}
                            </span>
                            <span className="text-xs text-accent-yellow mt-1">{tower.cost}G</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default BuildBar;
