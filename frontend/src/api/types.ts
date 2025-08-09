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

// --- MODIFIED: Tower type is now correctly defined with all properties ---
export interface Tower extends GameEntity {
    name: string;
    range: number;
    path_a_tier: number;
    path_b_tier: number;
    stats: {
        damage: number;
        fire_rate: number;
        blast_radius: number;
        pierce: number;
    };
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

// NEW: Type definition for an upgrade from the config
export interface UpgradeDefinition {
    id: string;
    name: string;
    description: string;
    cost: number;
    path: 'a' | 'b';
    effects: any[]; // Can be defined more strictly later if needed
}

// --- MODIFIED: InitialStateData now correctly includes upgrade_definitions ---
export interface InitialStateData {
    grid: {
        width: number;
        height: number;
        tiles: GridTile[];
    };
    paths: Vector2[][];
    buildable_towers: BuildableTower[];
    upgrade_definitions: { [towerTypeId: string]: { [upgradeId: string]: UpgradeDefinition } };
}
