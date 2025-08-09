// frontend/src/App.tsx
import { useGameStore, AppScreen } from './state/gameStore';
import { useGameWebSocket } from './hooks/useGameWebSocket';

// --- Local Imports ---
import GameCanvas from './components/Canvas/GameCanvas';
import HUD from './components/HUD/HUD';
import MainMenu from './components/Menus/Screens/MainMenu';

// --- Main Application Component ---
// This is the root component of the entire application.
function App() {
    // This selector is safe because it only selects a single primitive value.
    const activeScreen = useGameStore((state) => state.activeScreen);

    // --- Rendering Logic ---
    // The main container now uses our custom 'background' color from the new theme.
    // It's set to fill the screen and uses a relative positioning context
    // to allow its children to be layered correctly.
    return (
        <main className="w-screen h-screen bg-background text-text-primary overflow-hidden relative font-mono">
            {activeScreen === AppScreen.MainMenu && <MainMenu />}
            {activeScreen === AppScreen.InGame && <GameUI />}
        </main>
    );
}

// --- GameUI Component ---
// This component renders the actual gameplay interface.
const GameUI = () => {
    // Select the necessary state slices. These are stable and won't cause re-renders.
    const isConnected = useGameStore((state) => state.isConnected);
    const initialState = useGameStore((state) => state.initialState);

    // The WebSocket hook is only called when we are in-game.
    useGameWebSocket();

    return (
        <>
            {initialState ? (
                // --- Canvas & HUD Layout ---
                // This is the core of the layout fix. The container is positioned
                // to fill its parent. GameCanvas is the base layer. The HUD,
                // which has `position: absolute` internally, will now correctly
                // float on top of the canvas within this shared container.
                <div className="w-full h-full">
                    <GameCanvas />
                    <HUD />
                </div>
            ) : (
                // --- Loading State Display ---
                // This centered div provides feedback to the user while waiting
                // for the server connection and initial game data.
                <div className="w-full h-full flex items-center justify-center">
                    <p className="text-2xl text-text-secondary animate-pulse">
                        {isConnected
                            ? 'Waiting for initial game state...'
                            : 'Connecting to server...'}
                    </p>
                </div>
            )}
        </>
    );
};

export default App;
