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
    selectedEntityId: string | null; // The ID of an entity (tower) already placed on the map

    // Actions (functions to modify the state)
    setConnectionStatus: (status: boolean) => void;
    setInitialState: (data: InitialStateData) => void;
    setGameTickState: (gameState: GameStatePayload, entities: EntitiesPayload) => void;
    selectTowerToBuild: (towerId: string | null) => void;
    setSelectedEntityId: (entityId: string | null) => void; // New action
    clearSelections: () => void; // New utility action
}

// --- Store Creation ---
export const useGameStore = create<GameStoreState>((set) => ({
    // --- Initial Values ---
    initialState: null,
    gameState: null,
    entities: null,
    isConnected: false,
    selectedTowerToBuild: null,
    selectedEntityId: null,

    // --- Actions Implementation ---
    setConnectionStatus: (status) => set({ isConnected: status }),

    setInitialState: (data) => set({ initialState: data }),

    setGameTickState: (gameState, entities) => set({ gameState, entities }),

    selectTowerToBuild: (towerId) =>
        set(() => {
            // When selecting a tower to build, we must clear any selected entity.
            return { selectedTowerToBuild: towerId, selectedEntityId: null };
        }),

    setSelectedEntityId: (entityId) =>
        set((state) => {
            // If the same entity is clicked again, deselect it.
            if (state.selectedEntityId === entityId) {
                return { selectedEntityId: null };
            }
            // When selecting an entity, we must clear any tower-to-build selection.
            return { selectedEntityId: entityId, selectedTowerToBuild: null };
        }),

    clearSelections: () => set({ selectedTowerToBuild: null, selectedEntityId: null }),
}));
