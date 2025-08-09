// frontend/src/components/HUD/HUD.tsx
import type { GameStatePayload, InitialStateData } from '../../api/types';

// --- Prop Types ---
interface HUDProps {
    gameState: GameStatePayload | null;
    initialState: InitialStateData | null;
}

// --- Placeholder Components ---
// In the next steps, we will move these into their own dedicated files
// (`TopBar.tsx`, `BuildBar.tsx`) as per our plan.
const TopBar = ({ gameState }: { gameState: GameStatePayload | null }) => {
    if (!gameState) return null;

    return (
        <div className="absolute top-4 left-4 bg-gray-900 bg-opacity-70 text-white p-3 rounded-lg shadow-lg font-mono text-lg">
            <p>
                HP: <span className="text-red-500 font-bold">{gameState.base_hp}</span>
            </p>
            <p>
                Gold: <span className="text-yellow-400 font-bold">{gameState.gold}</span>
            </p>
            <p>
                Wave: <span className="text-blue-400 font-bold">{gameState.wave}</span>
            </p>
        </div>
    );
};

const BuildBar = ({ initialState }: { initialState: InitialStateData | null }) => {
    if (!initialState) return null;

    return (
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gray-900 bg-opacity-80 p-4 flex items-center justify-center gap-4">
            {initialState.buildable_towers.map((tower) => (
                <button
                    key={tower.id}
                    className="bg-gray-700 hover:bg-blue-600 border-2 border-gray-600 rounded-lg w-20 h-20 flex flex-col items-center justify-center p-2 text-white transition-all"
                >
                    <span className="text-sm font-bold">{tower.name}</span>
                    <span className="text-xs text-yellow-400 mt-1">{tower.cost}G</span>
                </button>
            ))}
        </div>
    );
};

// --- Main HUD Component ---
const HUD = ({ gameState, initialState }: HUDProps) => {
    return (
        // This div is a transparent overlay that holds all UI elements.
        // `pointer-events-none` is key: it allows mouse clicks to "pass through"
        // the container to the canvas below. Individual UI elements like buttons
        // will have `pointer-events-auto` to make them clickable.
        <div className="absolute inset-0 pointer-events-none">
            {/* Top-left stats display */}
            <div className="pointer-events-auto">
                <TopBar gameState={gameState} />
            </div>

            {/* Bottom tower build bar */}
            <div className="pointer-events-auto">
                <BuildBar initialState={initialState} />
            </div>

            {/* TODO: Add containers for side panels (Upgrade/Info) */}
        </div>
    );
};

export default HUD;
