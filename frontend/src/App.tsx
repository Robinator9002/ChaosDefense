// frontend/src/App.tsx
import { useGameStore } from './state/gameStore';
import { useGameWebSocket } from './hooks/useGameWebSocket';

// --- Local Imports ---
import GameCanvas from './components/Canvas/GameCanvas';
import HUD from './components/HUD/HUD';

function App() {
    // --- State Management ---
    // We no longer manage state here. Instead, we select what we need from the global store.
    // This subscription is efficient; the component only re-renders if these specific values change.
    const { isConnected, initialState, entities } = useGameStore((state) => ({
        isConnected: state.isConnected,
        initialState: state.initialState,
        entities: state.entities,
    }));

    // --- WebSocket Connection ---
    // This single line initializes our custom hook. The hook will handle all
    // WebSocket logic in the background and automatically update the gameStore.
    useGameWebSocket();

    // --- Rendering Logic ---
    // The rendering logic is now much simpler. It just reads from the store
    // and decides what to show. It doesn't need to pass any props down.
    return (
        <main className="w-screen h-screen bg-gray-800 overflow-hidden relative">
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
        </main>
    );
}

export default App;
