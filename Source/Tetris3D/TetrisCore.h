// TETRIS 3D RUSH - pure game logic core (7-bag, SRS kicks, scoring, modes)
#pragma once

#include "CoreMinimal.h"
#include "TetrisTypes.h"
#include "TetrisCore.generated.h"

USTRUCT(BlueprintType)
struct FActivePiece
{
    GENERATED_BODY()

    UPROPERTY() int32 Type = 0;       // 1..7
    UPROPERTY() int32 Rot = 0;        // 0..3
    UPROPERTY() int32 X = 3;
    UPROPERTY() int32 Y = 1;
    UPROPERTY() bool IsI = false;
};

USTRUCT()
struct FTetrisBoardState
{
    GENERATED_BODY()

    // grid[col][row], row 0 = top
    TArray<TArray<int32>> Grid;
    FActivePiece Cur;
    FActivePiece Next;
    FActivePiece Held;
    bool bHeldUsed = false;
    TArray<int32> Bag;
    int32 BagIdx = 0;

    int32 Lines = 0;
    int32 Score = 0;
    int32 Level = 1;
    int32 Combo = -1;
    int32 B2B = 0;            // back-to-back counter
    int32 Pieces = 0;
    float Elapsed = 0.f;
    int32 MaxCombo = 0;
    bool bGameOver = false;
    bool bCleared = false;
    ETetrisMode Mode = ETetrisMode::Sprint20;
    int32 HoldCount = 0;

    // events for feedback
    int32 LastClear = 0;
    bool bLastTSpin = false;
    int32 LastCombo = -1;
    bool bLastB2B = false;
    int32 LastPPS = 0;
    float LastFall = 0.f;
};

class FTetrisCore
{
public:
    static void Init(FTetrisBoardState& S);
    static void NewGame(FTetrisBoardState& S, ETetrisMode Mode);
    static bool TrySpawn(FTetrisBoardState& S, const FActivePiece& P);
    static bool TryMove(FTetrisBoardState& S, int32 Dx, int32 Dy);
    static bool TryRotate(FTetrisBoardState& S, int32 Dir);  // Dir: 1=cw, 2=180, -1=ccw
    static int32 HardDrop(FTetrisBoardState& S);
    static void Lock(FTetrisBoardState& S);
    static bool DoHold(FTetrisBoardState& S);
    static void Tick(FTetrisBoardState& S, float Delta);
    static int32 Cell(const FTetrisBoardState& S, int32 Col, int32 Row);
    static bool CanPlace(const FTetrisBoardState& S, const FActivePiece& P);
    static void FillCells(const FTetrisBoardState& S, FActivePiece P, TArray<TPair<int32,int32>>& Out, bool bActive);
    static int32 GetShapeVal(int32 Type, int32 Row, int32 Col);   // 4x4 matrix
    static bool IsTSpin(const FTetrisBoardState& S, const FActivePiece& P);
    static int32 ScoreForClear(FTetrisBoardState& S, int32 Lines, bool bTSpin, int32& OutCombo, bool& OutB2B);
    static float GravitySpeed(int32 Level);
    static void SetupCheese(FTetrisBoardState& S);
    static FString ModeName(ETetrisMode M);
};
