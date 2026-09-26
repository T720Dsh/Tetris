// TETRIS 3D RUSH - shared types & constants (ported from Godot 1.3 remake)
#pragma once

#include "CoreMinimal.h"
#include "TetrisTypes.generated.h"

UENUM()
enum class ETetrisMode : uint8
{
    Sprint20,
    Sprint40,
    Sprint100,
    Marathon1500,
    Blitz120,
    Cheese40,
    Endless,
    Count
};

UENUM()
enum class ETetrisSkin : uint8
{
    Classic,
    Neon,
    Candy,
    Matrix,
    Metal,
    Ghost,
    Count
};

UENUM()
enum class ETetrisTheme : uint8
{
    Space,
    City,
    Aurora,
    Grid,
    Ocean,
    Count
};

USTRUCT(BlueprintType)
struct FTetrisModeCfg
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Name;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Desc;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Lines = 0;      // goal lines (0 = none)
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float TimeLimit = 0.f; // seconds (0 = none)
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 ScoreGoal = 0;   // 0 = none
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool IsEndless = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool IsBlitz = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool IsCheese = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Gravity = 0.8f;
};

namespace TetrisConst
{
    constexpr int32 BoardW = 10;
    constexpr int32 BoardH = 22;   // visible 20, hidden 2
    constexpr int32 VisibleRows = 20;

    // ---- 7-bag piece shapes (4x4 matrices, value = piece type 1..7)
    // I piece row
    static const int32 PIECE_I[4][4] = {
        {0,0,0,0},{1,1,1,1},{0,0,0,0},{0,0,0,0}
    };
    // O piece
    static const int32 PIECE_O[4][4] = {
        {0,0,0,0},{0,2,2,0},{0,2,2,0},{0,0,0,0}
    };
    // T piece
    static const int32 PIECE_T[4][4] = {
        {0,0,0,0},{0,3,0,0},{3,3,3,0},{0,0,0,0}
    };
    // S piece
    static const int32 PIECE_S[4][4] = {
        {0,0,0,0},{0,4,4,0},{4,4,0,0},{0,0,0,0}
    };
    // Z piece
    static const int32 PIECE_Z[4][4] = {
        {0,0,0,0},{5,5,0,0},{0,5,5,0},{0,0,0,0}
    };
    // J piece
    static const int32 PIECE_J[4][4] = {
        {0,0,0,0},{6,0,0,0},{6,6,6,0},{0,0,0,0}
    };
    // L piece
    static const int32 PIECE_L[4][4] = {
        {0,0,0,0},{0,0,7,0},{7,7,7,0},{0,0,0,0}
    };

    // SRS wall kicks: index by rotation state (0..3).  [test rotations: 0->1,1->2,2->3,3->0, and 0->3,3->2,2->1,1->0]
    // kicks[from_rot][attempt] = (dx, dy)  -- standard SRS table
    static const int32 KICKS_JLSTZ[4][5][2] = {
        { {0,0}, {-1,0}, {-1,1}, {0,-2}, {-1,-2} },   // 0->1
        { {0,0}, {1,0}, {1,-1}, {0,2}, {1,2} },       // 1->2
        { {0,0}, {1,0}, {1,1}, {0,-2}, {1,-2} },      // 2->3
        { {0,0}, {-1,0}, {-1,-1}, {0,2}, {-1,2} }     // 3->0
    };
    static const int32 KICKS_I[4][5][2] = {
        { {0,0}, {-2,0}, {1,0}, {-2,-1}, {1,2} },
        { {0,0}, {-1,0}, {2,0}, {-1,2}, {2,-1} },
        { {0,0}, {2,0}, {-1,0}, {2,1}, {-1,-2} },
        { {0,0}, {1,0}, {-2,0}, {1,-2}, {-2,1} }
    };

    // spawn cells (standard guideline): pieces spawn centered, I piece on row 21 (col 3), others row 21
    // rows: 21 = top hidden row index 0? We use grid row 0 at top. Guideline spawn: I on row 21/22 area.
    // Our grid: row 0 is top (invisible). Visible rows 2..21. Spawn at rows 1..2 (y=0 in matrix = top).
    static const int32 SPAWN_Y = 1;   // matrix row offset for spawn
    static const int32 SPAWN_X_I = 3;
    static const int32 SPAWN_X_OTHER = 3;

    // gravity speeds (cells/sec) per level
    static const float GRAVITY_SPEEDS[21] = {
        0.01667f,0.021017f,0.026977f,0.035256f,0.04693f,
        0.06361f,0.08786f,0.1236f,0.1775f,0.2598f,
        0.388f,0.59f,0.92f,1.46f,2.36f,
        3.86f,6.43f,10.9f,18.7f,32.4f,
        60.0f
    };

    static constexpr const TCHAR* MODE_NAMES[] = {
        TEXT("竞速 20行"), TEXT("竞速 40行"), TEXT("竞速 100行"),
        TEXT("马拉松 1500"), TEXT("限时 120秒"), TEXT("奶糖突击 40"), TEXT("无尽生存")
    };

    static const FLinearColor SKIN_COLORS[(int32)ETetrisSkin::Count][8] = {
        // 1..7 piece colors, index 0 unused
        { FLinearColor::Black, FLinearColor(0.0f,0.85f,0.85f), FLinearColor(1.0f,0.9f,0.1f), FLinearColor(0.75f,0.2f,0.85f),
          FLinearColor(0.15f,0.85f,0.3f), FLinearColor(0.9f,0.2f,0.2f), FLinearColor(0.25f,0.4f,0.95f), FLinearColor(0.95f,0.55f,0.15f) },
        { FLinearColor::Black, FLinearColor(0.2f,1.0f,1.0f), FLinearColor(1.0f,1.0f,0.2f), FLinearColor(1.0f,0.2f,1.0f),
          FLinearColor(0.2f,1.0f,0.4f), FLinearColor(1.0f,0.2f,0.3f), FLinearColor(0.3f,0.5f,1.0f), FLinearColor(1.0f,0.6f,0.2f) },
        { FLinearColor::Black, FLinearColor(1.0f,0.5f,0.8f), FLinearColor(1.0f,0.9f,0.4f), FLinearColor(0.6f,1.0f,0.7f),
          FLinearColor(0.4f,0.9f,1.0f), FLinearColor(1.0f,0.6f,0.6f), FLinearColor(0.7f,0.5f,1.0f), FLinearColor(1.0f,0.8f,0.5f) },
        { FLinearColor::Black, FLinearColor(0.0f,1.0f,0.3f), FLinearColor(0.5f,1.0f,0.0f), FLinearColor(0.0f,0.8f,0.4f),
          FLinearColor(0.0f,1.0f,0.0f), FLinearColor(0.4f,0.9f,0.1f), FLinearColor(0.1f,0.7f,0.3f), FLinearColor(0.8f,1.0f,0.2f) },
        { FLinearColor::Black, FLinearColor(0.6f,0.65f,0.7f), FLinearColor(0.8f,0.8f,0.85f), FLinearColor(0.55f,0.6f,0.65f),
          FLinearColor(0.75f,0.78f,0.82f), FLinearColor(0.5f,0.55f,0.6f), FLinearColor(0.65f,0.7f,0.75f), FLinearColor(0.85f,0.87f,0.9f) },
        { FLinearColor::Black, FLinearColor(0.7f,0.3f,1.0f), FLinearColor(0.9f,0.4f,0.6f), FLinearColor(0.3f,0.8f,1.0f),
          FLinearColor(0.4f,1.0f,0.5f), FLinearColor(1.0f,0.4f,0.3f), FLinearColor(0.4f,0.5f,1.0f), FLinearColor(1.0f,0.7f,0.2f) }
    };
}
