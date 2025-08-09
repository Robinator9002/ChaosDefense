// frontend/src/components/HUD/Panels/UpgradePanel.tsx
import { useGameStore } from '../../../state/gameStore';
import { webSocketService } from '../../../api/webSocketService';
import type { Tower, UpgradeDefinition } from '../../../api/types';

// --- Reusable Button Component ---
// This sub-component handles the display logic for a single upgrade button.
const UpgradeButton = ({
    upgrade,
    canAfford,
    onPurchase,
}: {
    upgrade: UpgradeDefinition;
    canAfford: boolean;
    onPurchase: () => void;
}) => (
    <button
        onClick={onPurchase}
        disabled={!canAfford}
        className={`w-full p-3 rounded-lg border-2 text-left transition-colors duration-150
            ${
                canAfford
                    ? 'bg-gray-700 border-gray-600 hover:bg-blue-700 hover:border-blue-500'
                    : 'bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed'
            }`}
    >
        <div className="flex justify-between items-center">
            <span className="font-bold">{upgrade.name}</span>
            <span className={`font-bold ${canAfford ? 'text-yellow-400' : 'text-gray-600'}`}>
                {upgrade.cost}G
            </span>
        </div>
        <p className={`text-xs mt-1 ${canAfford ? 'text-gray-300' : 'text-gray-500'}`}>
            {upgrade.description}
        </p>
    </button>
);

// --- Main UpgradePanel Component ---
const UpgradePanel = () => {
    // --- State Selection ---
    // FIX: Select each piece of state individually to prevent infinite re-renders.
    const gameState = useGameStore((state) => state.gameState);
    const upgradeDefinitions = useGameStore((state) => state.initialState?.upgrade_definitions);

    // This is a more complex selector, but it's efficient. It finds the specific
    // tower object that the player has selected on the map. It will only
    // cause a re-render if the selected ID changes or the tower's data itself changes.
    const selectedTower = useGameStore((state) =>
        state.entities?.towers.find((t) => t.id === state.selectedEntityId),
    );

    // --- Early Exit ---
    // If we don't have the necessary data, render nothing. This prevents crashes.
    if (!selectedTower || !gameState || !upgradeDefinitions) {
        return null;
    }

    // --- Upgrade Logic ---
    // Helper function to find the next available upgrade for a given path ('a' or 'b').
    const findNextUpgrade = (tower: Tower, path: 'a' | 'b'): UpgradeDefinition | null => {
        const currentTier = path === 'a' ? tower.path_a_tier : tower.path_b_tier;
        const towerUpgrades = upgradeDefinitions[tower.type_id];
        if (!towerUpgrades) return null;

        // Upgrade IDs are formatted like "path_a_1", "path_b_2", etc.
        const nextUpgradeId = `path_${path}_${currentTier + 1}`;
        return towerUpgrades[nextUpgradeId] || null;
    };

    const nextUpgradeA = findNextUpgrade(selectedTower, 'a');
    const nextUpgradeB = findNextUpgrade(selectedTower, 'b');

    // --- Action Handler ---
    // Sends the purchase request to the backend via WebSocket.
    const handlePurchase = (upgradeId: string) => {
        webSocketService.send({
            action: 'upgrade_tower',
            payload: { tower_id: selectedTower.id, upgrade_id: upgradeId },
        });
    };

    return (
        <div className="absolute top-4 right-4 w-80 bg-gray-900 bg-opacity-85 border-2 border-gray-700 rounded-lg shadow-2xl p-4 text-white font-mono flex flex-col gap-4">
            {/* Header: Tower Name & Tier */}
            <div className="border-b-2 border-gray-700 pb-2">
                <h2 className="text-xl font-bold text-blue-300">{selectedTower.name}</h2>
                <p className="text-sm text-gray-400">
                    Tier: {selectedTower.path_a_tier} / {selectedTower.path_b_tier}
                </p>
            </div>

            {/* Live Statistics */}
            <div>
                <h3 className="text-md font-semibold text-gray-400 mb-2">Statistics</h3>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                    <span>Damage:</span>
                    <span className="text-right">{selectedTower.stats.damage.toFixed(1)}</span>
                    <span>Range:</span>
                    <span className="text-right">{selectedTower.range.toFixed(0)}</span>
                    <span>Fire Rate:</span>
                    <span className="text-right">{selectedTower.stats.fire_rate.toFixed(2)}/s</span>
                    <span>Pierce:</span>
                    <span className="text-right">{selectedTower.stats.pierce}</span>
                </div>
            </div>

            {/* Upgrade Buttons */}
            <div>
                <h3 className="text-md font-semibold text-gray-400 mb-2">Upgrades</h3>
                <div className="flex flex-col gap-3">
                    {nextUpgradeA && (
                        <UpgradeButton
                            upgrade={nextUpgradeA}
                            canAfford={gameState.gold >= nextUpgradeA.cost}
                            onPurchase={() => handlePurchase(nextUpgradeA.id)}
                        />
                    )}
                    {nextUpgradeB && (
                        <UpgradeButton
                            upgrade={nextUpgradeB}
                            canAfford={gameState.gold >= nextUpgradeB.cost}
                            onPurchase={() => handlePurchase(nextUpgradeB.id)}
                        />
                    )}
                    {!nextUpgradeA && !nextUpgradeB && (
                        <p className="text-sm text-gray-500 text-center">Max upgrades reached.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default UpgradePanel;
