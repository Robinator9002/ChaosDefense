// frontend/src/components/Canvas/GameCanvas.tsx
import { Stage, Layer, Rect, Circle } from 'react-konva';
import { useGameStore } from '../../state/gameStore';

// A simple color map for different tile types. We can make this more robust later.
const tileColorMap: { [key: string]: string } = {
    BUILDABLE: '#3a5a40',
    PATH: '#582f0e',
    BORDER: '#212529',
    MOUNTAIN: '#6c757d',
    BASE_ZONE: '#023e8a',
    TOWER_OCCUPIED: '#3a5a40', // Same as buildable for now
    LAKE: '#48cae4',
    TREE: '#9ef01a',
};

const TILE_SIZE = 32; // This should eventually come from config

const GameCanvas = () => {
    // Select the state needed for rendering directly from the store.
    const { initialState, entities } = useGameStore((state) => ({
        initialState: state.initialState,
        entities: state.entities,
    }));

    // The parent App.tsx already ensures this component won't render if initialState is null,
    // but this is a good safeguard.
    if (!initialState) {
        return null;
    }

    const { grid } = initialState;

    return (
        <Stage width={window.innerWidth} height={window.innerHeight}>
            <Layer>
                {grid.tiles.map((tile) => (
                    <Rect
                        key={`${tile.x}-${tile.y}`}
                        x={tile.x * TILE_SIZE}
                        y={tile.y * TILE_SIZE}
                        width={TILE_SIZE}
                        height={TILE_SIZE}
                        fill={tileColorMap[tile.key] || '#ff00ff'}
                    />
                ))}
            </Layer>

            <Layer>
                {entities?.towers.map((tower) => (
                    <Circle
                        key={tower.id}
                        x={tower.pos.x}
                        y={tower.pos.y}
                        radius={TILE_SIZE / 2 - 4}
                        fill="#e9ecef"
                        stroke="#495057"
                        strokeWidth={2}
                    />
                ))}
                {entities?.enemies.map((enemy) => (
                    <Rect
                        key={enemy.id}
                        x={enemy.pos.x - TILE_SIZE / 2.5}
                        y={enemy.pos.y - TILE_SIZE / 2.5}
                        width={TILE_SIZE * 0.8}
                        height={TILE_SIZE * 0.8}
                        fill="#e5383b"
                        cornerRadius={4}
                    />
                ))}
            </Layer>
        </Stage>
    );
};

export default GameCanvas;
