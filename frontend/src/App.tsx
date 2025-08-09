// frontend/src/App.tsx
import { useGameStore, AppScreen } from './state/gameStore';
import { useGameWebSocket } from './hooks/useGameWebSocket';

// --- Local Imports ---
import GameCanvas from './components/Canvas/GameCanvas';
import HUD from './components/HUD/HUD';
import MainMenu from './components/Menus/Screens/MainMenu';

function App() {
    // This selector is safe because it only selects a single primitive value.
    const activeScreen = useGameStore((state) => state.activeScreen);

    // --- Rendering Logic ---
    return (
        <main className="w-screen h-screen bg-gray-900 text-white overflow-hidden relative font-mono">
            {activeScreen === AppScreen.MainMenu && <MainMenu />}
            {activeScreen === AppScreen.InGame && <GameUI />}
        </main>
    );
}

// --- GameUI Component ---
const GameUI = () => {
    // FIX: Select each piece of state individually. This prevents the infinite
    // re-render loop because primitives (and stable objects) are compared correctly.
    const isConnected = useGameStore((state) => state.isConnected);
    const initialState = useGameStore((state) => state.initialState);
    const entities = useGameStore((state) => state.entities);

    // The WebSocket hook is only called when we are in-game.
    useGameWebSocket();

    return (
        <>
            {initialState && entities ? (
                <>
                    <GameCanvas />
                    <HUD />
                </>
            ) : (
                <div className="w-full h-full flex items-center justify-center text-white font-mono">
                    <p>
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
