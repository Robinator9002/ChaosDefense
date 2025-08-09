// frontend/src/components/HUD/TopBar.tsx
import type { GameStatePayload } from '../../api/types';

// --- Prop Types ---
interface TopBarProps {
    gameState: GameStatePayload | null;
}

// --- SVG Icon Components ---
// Creating simple, reusable SVG components for our icons is cleaner
// than dealing with image files for basic UI elements.

const HeartIcon = ({ className }: { className?: string }) => (
    <svg
        className={className}
        viewBox="0 0 24 24"
        fill="currentColor"
        xmlns="http://www.w3.org/2000/svg"
    >
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
    </svg>
);

const CoinIcon = ({ className }: { className?: string }) => (
    <svg
        className={className}
        viewBox="0 0 24 24"
        fill="currentColor"
        xmlns="http://www.w3.org/2000/svg"
    >
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-8.5h2v-3h-2v3zm0 4h2v-2h-2v2z" />
    </svg>
);

const WaveIcon = ({ className }: { className?: string }) => (
    <svg
        className={className}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        xmlns="http://www.w3.org/2000/svg"
    >
        <path d="M3 12h2l3-9 4 18 4-12 3 9h2" />
    </svg>
);

// --- Main TopBar Component ---
const TopBar = ({ gameState }: TopBarProps) => {
    if (!gameState) {
        // Don't render anything if we don't have state data yet.
        return null;
    }

    return (
        <div className="flex items-center gap-6 bg-gray-900 bg-opacity-75 p-3 rounded-br-2xl shadow-2xl font-mono text-xl border-b-2 border-r-2 border-gray-700">
            {/* HP Stat */}
            <div className="flex items-center gap-2 text-red-400">
                <HeartIcon className="w-6 h-6" />
                <span className="font-bold">{gameState.base_hp}</span>
            </div>

            {/* Gold Stat */}
            <div className="flex items-center gap-2 text-yellow-400">
                <CoinIcon className="w-6 h-6" />
                <span className="font-bold">{gameState.gold}</span>
            </div>

            {/* Wave Stat */}
            <div className="flex items-center gap-2 text-blue-400">
                <WaveIcon className="w-7 h-7" />
                <span className="font-bold">{gameState.wave}</span>
            </div>
        </div>
    );
};

export default TopBar;
