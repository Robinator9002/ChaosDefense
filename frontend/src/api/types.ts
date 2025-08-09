// frontend/src/api/types.ts

// --- Generic & Utility Types ---
export interface Vector2 {
    x: number;
    y: number;
}

// --- Entity Types ---
export interface GameEntity {
    id: string;
    type_id: string;
    pos: Vector2;
    is_alive: boolean;
}

export interface Enemy extends GameEntity {
    hp: number;
    max_hp: number;
}

export interface Tower extends GameEntity {
    range: number;
}

export interface Projectile extends GameEntity {}

// --- WebSocket Payload Types ---
export interface GameStatePayload {
    gold: number;
    base_hp: number;
    wave: number;
    game_over: boolean;
    victory: boolean;
}

export interface EntitiesPayload {
    towers: Tower[];
    enemies: Enemy[];
    projectiles: Projectile[];
}

// --- Initial State Payload Types ---
interface GridTile {
    x: number;
    y: number;
    key: string;
}

interface BuildableTower {
    id: string;
    name: string;
    cost: number;
}

export interface InitialStateData {
    grid: {
        width: number;
        height: number;
        tiles: GridTile[];
    };
    paths: Vector2[][];
    buildable_towers: BuildableTower[];
}
