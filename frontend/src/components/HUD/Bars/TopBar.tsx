// frontend/src/components/HUD/Bars/TopBar.tsx
import { useGameStore } from '../../../state/gameStore';

// --- SVG Icon Components (unchanged) ---
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
const TopBar = () => {
    const gameState = useGameStore((state) => state.gameState);

    if (!gameState) {
        return null;
    }

    // STYLING FIX: This component is now styled using the custom theme colors
    // from tailwind.config.js. It's a flex container with a semi-transparent
    // background, rounded corners, and a border, positioned at the top-left.
    return (
        <div className="absolute top-4 left-4 flex items-center gap-6 bg-panel-secondary/80 p-3 rounded-xl shadow-lg border-2 border-border-primary text-xl">
            {/* HP Stat */}
            <div className="flex items-center gap-2 text-accent-red">
                <HeartIcon className="w-6 h-6" />
                <span className="font-bold">{gameState.base_hp}</span>
            </div>

            {/* Gold Stat */}
            <div className="flex items-center gap-2 text-accent-yellow">
                <CoinIcon className="w-6 h-6" />
                <span className="font-bold">{gameState.gold}</span>
            </div>

            {/* Wave Stat */}
            <div className="flex items-center gap-2 text-accent-blue">
                <WaveIcon className="w-7 h-7" />
                <span className="font-bold">{gameState.wave}</span>
            </div>
        </div>
    );
};

export default TopBar;
