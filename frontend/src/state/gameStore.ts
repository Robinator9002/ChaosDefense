// frontend/src/state/gameStore.ts
import { create } from 'zustand';
import type { InitialStateData, GameStatePayload, EntitiesPayload } from '../api/types';

// --- State Interface ---
// This defines the complete "shape" of our application's state.
interface GameStoreState {
    // Data from the server
    initialState: InitialStateData | null;
    gameState: GameStatePayload | null;
    entities: EntitiesPayload | null;
    isConnected: boolean;

    // Client-side UI state
    selectedTowerToBuild: string | null; // The ID of the tower type the player wants to build

    // Actions (functions to modify the state)
    setConnectionStatus: (status: boolean) => void;
    setInitialState: (data: InitialStateData) => void;
    setGameTickState: (gameState: GameStatePayload, entities: EntitiesPayload) => void;
    selectTowerToBuild: (towerId: string | null) => void;
}

// --- Store Creation ---
export const useGameStore = create<GameStoreState>((set) => ({
    // --- Initial Values ---
    initialState: null,
    gameState: null,
    entities: null,
    isConnected: false,
    selectedTowerToBuild: null,

    // --- Actions Implementation ---
    // These are the only functions that can modify the store's state.
    // They are safe and predictable.

    setConnectionStatus: (status) => set({ isConnected: status }),

    setInitialState: (data) => set({ initialState: data }),

    setGameTickState: (gameState, entities) => set({ gameState, entities }),

    selectTowerToBuild: (towerId) =>
        set((state) => {
            // If the player clicks the same tower again, deselect it.
            if (state.selectedTowerToBuild === towerId) {
                return { selectedTowerToBuild: null };
            }
            return { selectedTowerToBuild: towerId };
        }),
}));
