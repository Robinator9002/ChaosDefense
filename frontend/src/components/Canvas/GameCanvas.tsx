// frontend/src/components/Canvas/GameCanvas.tsx
import { Stage, Layer, Rect, Circle } from 'react-konva';
import { useGameStore } from '../../state/gameStore';
import Konva from 'konva';
import { useState, useRef, useEffect, useCallback } from 'react';
import type { GameEntity } from '../../api/types';

// --- Constants ---
const TILE_SIZE = 32;
const MIN_ZOOM = 0.2;
const MAX_ZOOM = 3.0;
const ZOOM_SENSITIVITY = 0.001;

const tileColorMap: { [key: string]: string } = {
    BUILDABLE: '#3a5a40',
    PATH: '#582f0e',
    BORDER: '#212529',
    MOUNTAIN: '#6c757d',
    BASE_ZONE: '#023e8a',
    TOWER_OCCUPIED: '#3a5a40',
    LAKE: '#48cae4',
    TREE: '#9ef01a',
};

// --- Performance Refactor ---
// This component is the core of the performance optimization. Instead of re-rendering
// the component declaratively, we create a Konva shape once and then update its
// properties imperatively. This avoids the massive overhead of React's diffing
// algorithm on every game tick.
const EntityShape = ({
    entity,
    type,
    scale,
    isSelected,
    onClick,
}: {
    entity: GameEntity;
    type: 'tower' | 'enemy';
    scale: number;
    isSelected: boolean;
    onClick: () => void;
}) => {
    const shapeRef = useRef<Konva.Circle | Konva.Rect>(null);

    // Update position imperatively when entity data changes
    useEffect(() => {
        shapeRef.current?.position({ x: entity.pos.x, y: entity.pos.y });
    }, [entity.pos.x, entity.pos.y]);

    if (type === 'tower') {
        return (
            <Circle
                ref={shapeRef as React.Ref<Konva.Circle>}
                key={entity.id}
                x={entity.pos.x}
                y={entity.pos.y}
                radius={TILE_SIZE / 2 - 4}
                fill="#e9ecef"
                stroke={isSelected ? '#facc15' : '#495057'}
                strokeWidth={isSelected ? 4 / scale : 2 / scale}
                shadowColor={isSelected ? '#facc15' : undefined}
                shadowBlur={isSelected ? 10 : 0}
                onClick={onClick}
                onTap={onClick}
            />
        );
    }

    return (
        <Rect
            ref={shapeRef as React.Ref<Konva.Rect>}
            key={entity.id}
            x={entity.pos.x}
            y={entity.pos.y}
            width={TILE_SIZE * 0.8}
            height={TILE_SIZE * 0.8}
            fill="#e5383b"
            cornerRadius={4}
            offsetX={(TILE_SIZE * 0.8) / 2}
            offsetY={(TILE_SIZE * 0.8) / 2}
        />
    );
};

const GameCanvas = () => {
    // --- STATE SELECTION FIX ---
    // This is the definitive fix for the infinite loop. By selecting each
    // piece of state individually, we provide stable values to React,
    // preventing the component from re-rendering unless the data it
    // actually depends on changes.
    const initialState = useGameStore((state) => state.initialState);
    const entities = useGameStore((state) => state.entities);
    const selectedEntityId = useGameStore((state) => state.selectedEntityId);
    const setSelectedEntityId = useGameStore((state) => state.setSelectedEntityId);
    const clearSelections = useGameStore((state) => state.clearSelections);

    const [stagePos, setStagePos] = useState({ x: 0, y: 0 });
    const [stageScale, setStageScale] = useState(1);
    const lastMousePos = useRef({ x: 0, y: 0 });
    const stageRef = useRef<Konva.Stage>(null);

    useEffect(() => {
        if (initialState && stageRef.current) {
            const stage = stageRef.current;
            const { grid } = initialState;
            const mapWidth = grid.width * TILE_SIZE;
            const mapHeight = grid.height * TILE_SIZE;
            const scale = Math.min(stage.width() / mapWidth, stage.height() / mapHeight, MAX_ZOOM);
            setStageScale(scale);
            setStagePos({
                x: (stage.width() - mapWidth * scale) / 2,
                y: (stage.height() - mapHeight * scale) / 2,
            });
        }
    }, [initialState]);

    const handleWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
        e.evt.preventDefault();
        const stage = stageRef.current;
        if (!stage) return;
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();
        if (!pointer) return;
        const mousePointTo = {
            x: (pointer.x - stage.x()) / oldScale,
            y: (pointer.y - stage.y()) / oldScale,
        };
        const newScale = Math.max(
            MIN_ZOOM,
            Math.min(oldScale - e.evt.deltaY * ZOOM_SENSITIVITY, MAX_ZOOM),
        );
        setStageScale(newScale);
        setStagePos({
            x: pointer.x - mousePointTo.x * newScale,
            y: pointer.y - mousePointTo.y * newScale,
        });
    };

    const handlePanMove = useCallback((e: MouseEvent) => {
        const dx = e.clientX - lastMousePos.current.x;
        const dy = e.clientY - lastMousePos.current.y;
        lastMousePos.current = { x: e.clientX, y: e.clientY };
        setStagePos((p) => ({ x: p.x + dx, y: p.y + dy }));
    }, []);

    const handlePanEnd = useCallback(() => {
        window.removeEventListener('mousemove', handlePanMove);
    }, [handlePanMove]);

    const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (e.evt.button === 1) {
            e.evt.preventDefault();
            lastMousePos.current = { x: e.evt.clientX, y: e.evt.clientY };
            window.addEventListener('mousemove', handlePanMove);
            window.addEventListener('mouseup', handlePanEnd, { once: true });
        }
    };

    const handleStageClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (e.target === e.target.getStage()) clearSelections();
    };

    if (!initialState) return null;

    return (
        <Stage
            ref={stageRef}
            width={window.innerWidth}
            height={window.innerHeight}
            x={stagePos.x}
            y={stagePos.y}
            scaleX={stageScale}
            scaleY={stageScale}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onClick={handleStageClick}
        >
            <Layer>
                {initialState.grid.tiles.map((tile) => (
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
                    <EntityShape
                        key={tower.id}
                        entity={tower}
                        type="tower"
                        scale={stageScale}
                        isSelected={tower.id === selectedEntityId}
                        onClick={() => {
                            setSelectedEntityId(tower.id);
                        }}
                    />
                ))}
                {entities?.enemies.map((enemy) => (
                    <EntityShape
                        key={enemy.id}
                        entity={enemy}
                        type="enemy"
                        scale={stageScale}
                        isSelected={false}
                        onClick={() => {}}
                    />
                ))}
            </Layer>
        </Stage>
    );
};

export default GameCanvas;
