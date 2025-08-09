// frontend/src/components/HUD/HUD.tsx

// --- Local Imports ---
// FIX: Updated import paths to reflect the new 'Bars' subdirectory.
import TopBar from './Bars/TopBar';
import BuildBar from './Bars/BuildBar';

// --- Main HUD Component ---
// This component no longer needs to receive any props.
// Its children will get their data directly from the global store.
const HUD = () => {
    return (
        // This div is a transparent overlay that holds all UI elements.
        // `pointer-events-none` is key: it allows mouse clicks to "pass through"
        // the container to the canvas below. Individual UI elements like buttons
        // will have `pointer-events-auto` to make them clickable.
        <div className="absolute inset-0 pointer-events-none">
            <div className="pointer-events-auto">
                <TopBar />
            </div>

            <div className="pointer-events-auto">
                <BuildBar />
            </div>

            {/* TODO: Add containers for side panels (Upgrade/Info) which will live in a 'Panels' subfolder. */}
        </div>
    );
};

export default HUD;
