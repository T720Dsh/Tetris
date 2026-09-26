// TETRIS 3D RUSH - core logic implementation (ported from Godot 1.3 remake)
#include "TetrisCore.h"

static const int32* ShapePtr(int32 Type)
{
    switch (Type)
    {
    case 1: return &TetrisConst::PIECE_I[0][0];
    case 2: return &TetrisConst::PIECE_O[0][0];
    case 3: return &TetrisConst::PIECE_T[0][0];
    case 4: return &TetrisConst::PIECE_S[0][0];
    case 5: return &TetrisConst::PIECE_Z[0][0];
    case 6: return &TetrisConst::PIECE_J[0][0];
    case 7: return &TetrisConst::PIECE_L[0][0];
    }
    return &TetrisConst::PIECE_O[0][0];
}

int32 FTetrisCore::GetShapeVal(int32 Type, int32 Row, int32 Col)
{
    const int32* M = ShapePtr(Type);
    // 4x4
    return M[Row * 4 + Col];
}

void FTetrisCore::Init(FTetrisBoardState& S)
{
    S.Grid.SetNum(TetrisConst::BoardW);
    for (int32 c = 0; c < TetrisConst::BoardW; ++c)
    {
        S.Grid[c].SetNum(TetrisConst::BoardH);
        for (int32 r = 0; r < TetrisConst::BoardH; ++r) S.Grid[c][r] = 0;
    }
    S.Bag.Reset();
    S.BagIdx = 0;
    S.Lines = 0; S.Score = 0; S.Level = 1; S.Combo = -1; S.B2B = 0;
    S.Pieces = 0; S.Elapsed = 0.f; S.MaxCombo = 0;
    S.bGameOver = false; S.bCleared = false; S.bHeldUsed = false;
    S.Held.Type = 0; S.HoldCount = 0;
    S.Cur.Type = 0; S.Next.Type = 0;
    S.LastClear = 0; S.bLastTSpin = false; S.LastCombo = -1; S.bLastB2B = false;
    S.LastPPS = 0; S.LastFall = 0.f;
}

void FTetrisCore::NewGame(FTetrisBoardState& S, ETetrisMode Mode)
{
    Init(S);
    S.Mode = Mode;
    if (Mode == ETetrisMode::Cheese40) { SetupCheese(S); }
    // refill bag, spawn first two pieces
    S.Bag.Reset();
    for (int32 i = 1; i <= 7; ++i) S.Bag.Add(i);
    // shuffle
    for (int32 i = S.Bag.Num() - 1; i > 0; --i)
    {
        int32 j = FMath::RandRange(0, i);
        S.Bag.Swap(i, j);
    }
    S.BagIdx = 0;
    // pre-spawn next
    FActivePiece P;
    if (S.BagIdx < S.Bag.Num()) { P.Type = S.Bag[S.BagIdx++]; P.Rot = 0; P.X = (P.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER; P.Y = TetrisConst::SPAWN_Y; P.IsI = (P.Type == 1); S.Next = P; }
    // spawn current
    if (S.BagIdx < S.Bag.Num()) { P.Type = S.Bag[S.BagIdx++]; P.Rot = 0; P.X = (P.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER; P.Y = TetrisConst::SPAWN_Y; P.IsI = (P.Type == 1); S.Cur = P; }
    S.LastFall = 0.f;
}

bool FTetrisCore::CanPlace(const FTetrisBoardState& S, const FActivePiece& P)
{
    for (int32 r = 0; r < 4; ++r)
    {
        for (int32 c = 0; c < 4; ++c)
        {
            if (GetShapeVal(P.Type, r, c) == 0) continue;
            int32 gx = P.X + c;
            int32 gy = P.Y + r;
            if (gx < 0 || gx >= TetrisConst::BoardW) return false;
            if (gy < 0) return false;
            if (gy < TetrisConst::BoardH && S.Grid[gx][gy] != 0) return false;
        }
    }
    return true;
}

bool FTetrisCore::TrySpawn(FTetrisBoardState& S, const FActivePiece& P)
{
    FActivePiece Q = P;
    Q.X = (Q.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER;
    Q.Y = TetrisConst::SPAWN_Y;
    Q.Rot = 0;
    Q.IsI = (Q.Type == 1);
    if (CanPlace(S, Q))
    {
        S.Cur = Q;
        return true;
    }
    return false;
}

bool FTetrisCore::TryMove(FTetrisBoardState& S, int32 Dx, int32 Dy)
{
    FActivePiece Q = S.Cur;
    Q.X += Dx; Q.Y += Dy;
    if (CanPlace(S, Q)) { S.Cur = Q; return true; }
    return false;
}

// rotate 4x4 matrix
static void RotateMatrixCW(const int32* In, int32* Out)
{
    for (int32 r = 0; r < 4; ++r)
        for (int32 c = 0; c < 4; ++c)
            Out[c * 4 + (3 - r)] = In[r * 4 + c];
}

bool FTetrisCore::TryRotate(FTetrisBoardState& S, int32 Dir)
{
    if (S.Cur.Type == 2) return true; // O piece

    int32 NewRot = (S.Cur.Rot + Dir + 4) % 4;
    int32 KickIdx = S.Cur.Rot; // kicks indexed by from-state

    for (int32 a = 0; a < 5; ++a)
    {
        FActivePiece Q = S.Cur;
        Q.Rot = NewRot;
        int32 KickX = 0, KickY = 0;
        if (S.Cur.Type == 1) { KickX = TetrisConst::KICKS_I[KickIdx][a][0]; KickY = TetrisConst::KICKS_I[KickIdx][a][1]; }
        else { KickX = TetrisConst::KICKS_JLSTZ[KickIdx][a][0]; KickY = TetrisConst::KICKS_JLSTZ[KickIdx][a][1]; }
        Q.X += KickX;
        Q.Y += KickY;
        // SRS: for 180 we use simplified (try offsets 0 and +-1)
        if (Dir == 2)
        {
            if (a == 0) { /* no kick */ }
            else if (a == 1) { Q.X += 1; }
            else if (a == 2) { Q.X -= 1; }
            else if (a == 3) { Q.Y += 1; }
            else { Q.Y -= 1; }
        }
        if (CanPlace(S, Q))
        {
            S.Cur = Q;
            return true;
        }
    }
    return false;
}

int32 FTetrisCore::HardDrop(FTetrisBoardState& S)
{
    int32 D = 0;
    while (TryMove(S, 0, 1)) ++D;
    return D;
}

bool FTetrisCore::IsTSpin(const FTetrisBoardState& S, const FActivePiece& P)
{
    if (P.Type != 3) return false;
    int32 Corners = 0;
    // T corners: (0,0),(0,2),(2,0),(2,2) of 4x4 bounding
    const int32 CX[4] = {0, 0, 2, 2};
    const int32 CY[4] = {0, 2, 0, 2};
    for (int32 i = 0; i < 4; ++i)
    {
        int32 gx = P.X + CX[i];
        int32 gy = P.Y + CY[i];
        bool Occ = (gx < 0 || gx >= TetrisConst::BoardW || gy >= TetrisConst::BoardH);
        if (!Occ && gy >= 0) Occ = (S.Grid[gx][gy] != 0);
        if (Occ) ++Corners;
    }
    return Corners >= 3;
}

void FTetrisCore::Lock(FTetrisBoardState& S)
{
    for (int32 r = 0; r < 4; ++r)
    {
        for (int32 c = 0; c < 4; ++c)
        {
            if (GetShapeVal(S.Cur.Type, r, c) == 0) continue;
            int32 gx = S.Cur.X + c;
            int32 gy = S.Cur.Y + r;
            if (gy >= 0 && gy < TetrisConst::BoardH) S.Grid[gx][gy] = S.Cur.Type;
        }
    }
    S.Pieces++;
    S.bHeldUsed = false;

    // line clear
    TArray<int32> FullRows;
    for (int32 r = TetrisConst::BoardH - 1; r >= 0; --r)
    {
        bool Full = true;
        for (int32 c = 0; c < TetrisConst::BoardW; ++c) if (S.Grid[c][r] == 0) { Full = false; break; }
        if (Full) FullRows.Add(r);
    }
    int32 NClear = FullRows.Num();
    bool bTSpin = (NClear > 0) && IsTSpin(S, S.Cur);
    if (NClear > 0)
    {
        for (int32 r : FullRows)
        {
            for (int32 rr = r; rr > 0; --rr)
                for (int32 c = 0; c < TetrisConst::BoardW; ++c)
                    S.Grid[c][rr] = S.Grid[c][rr - 1];
            for (int32 c = 0; c < TetrisConst::BoardW; ++c) S.Grid[c][0] = 0;
        }
    }
    int32 Combo = -1;
    bool bB2B = false;
    int32 Gain = ScoreForClear(S, NClear, bTSpin, Combo, bB2B);
    S.Score += Gain;
    S.Lines += NClear;
    S.LastClear = NClear;
    S.bLastTSpin = bTSpin;
    S.LastCombo = Combo;
    S.bLastB2B = bB2B;
    if (Combo > 0 && Combo > S.MaxCombo) S.MaxCombo = Combo;

    // level up (every 10 lines)
    int32 NewLevel = S.Lines / 10 + 1;
    if (NewLevel > S.Level)
    {
        S.Level = NewLevel;
        if (S.Level > 20) S.Level = 20;
    }

    // next piece
    if (S.BagIdx >= S.Bag.Num())
    {
        S.Bag.Reset();
        for (int32 i = 1; i <= 7; ++i) S.Bag.Add(i);
        for (int32 i = S.Bag.Num() - 1; i > 0; --i) { int32 j = FMath::RandRange(0, i); S.Bag.Swap(i, j); }
        S.BagIdx = 0;
    }
    FActivePiece P;
    P.Type = S.Bag[S.BagIdx++];
    P.Rot = 0; P.X = (P.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER;
    P.Y = TetrisConst::SPAWN_Y; P.IsI = (P.Type == 1);
    S.Cur = P;
    S.Next = S.Cur; // next display uses bag preview separately handled by actor

    if (!CanPlace(S, S.Cur)) S.bGameOver = true;
}

int32 FTetrisCore::ScoreForClear(FTetrisBoardState& S, int32 Lines, bool bTSpin, int32& OutCombo, bool& OutB2B)
{
    int32 Base = 0;
    if (bTSpin) Base = (Lines == 1) ? 800 : (Lines == 2) ? 1200 : (Lines == 3) ? 1600 : 2000;
    else Base = (Lines == 1) ? 100 : (Lines == 2) ? 300 : (Lines == 3) ? 500 : 800;
    if (Lines >= 4) { OutB2B = (S.B2B >= 1); S.B2B++; }
    else if (Lines > 0) S.B2B = 0;
    OutCombo = (Lines > 0) ? S.Combo + 1 : -1;
    if (Lines > 0) S.Combo = OutCombo; else S.Combo = -1;
    int32 Gain = Base * S.Level;
    if (OutCombo > 0) Gain += 50 * OutCombo * S.Level;
    if (OutB2B && Lines >= 4) Gain += (int32)(Base * 0.5f) * S.Level;
    return Gain;
}

bool FTetrisCore::DoHold(FTetrisBoardState& S)
{
    if (S.bHeldUsed || S.Cur.Type == 0) return false;
    S.bHeldUsed = true;
    S.HoldCount++;
    int32 T = S.Cur.Type;
    if (S.Held.Type == 0)
    {
        S.Held = S.Cur;
        S.Held.Rot = 0;
        S.Held.X = (S.Held.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER;
        S.Held.Y = TetrisConst::SPAWN_Y;
        // spawn next from bag
        if (S.BagIdx >= S.Bag.Num())
        {
            S.Bag.Reset();
            for (int32 i = 1; i <= 7; ++i) S.Bag.Add(i);
            for (int32 i = S.Bag.Num() - 1; i > 0; --i) { int32 j = FMath::RandRange(0, i); S.Bag.Swap(i, j); }
            S.BagIdx = 0;
        }
        FActivePiece P;
        P.Type = S.Bag[S.BagIdx++];
        P.Rot = 0; P.X = (P.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER;
        P.Y = TetrisConst::SPAWN_Y; P.IsI = (P.Type == 1);
        S.Cur = P;
        if (!CanPlace(S, S.Cur)) S.bGameOver = true;
    }
    else
    {
        FActivePiece P = S.Held;
        P.Rot = 0; P.X = (P.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER;
        P.Y = TetrisConst::SPAWN_Y;
        S.Held = S.Cur;
        S.Held.Rot = 0;
        S.Held.X = (S.Held.Type == 1) ? TetrisConst::SPAWN_X_I : TetrisConst::SPAWN_X_OTHER;
        S.Held.Y = TetrisConst::SPAWN_Y;
        if (CanPlace(S, P)) S.Cur = P;
        else S.bGameOver = true;
    }
    return true;
}

void FTetrisCore::Tick(FTetrisBoardState& S, float Delta)
{
    if (S.bGameOver) return;
    S.Elapsed += Delta;
    float Speed = GravitySpeed(S.Level);
    S.LastFall += Delta;
    float Interval = 1.0f / Speed;
    if (S.LastFall >= Interval)
    {
        S.LastFall = FMath::Fmod(S.LastFall, Interval);
        if (!TryMove(S, 0, 1))
        {
            // soft lock
        }
    }
}

float FTetrisCore::GravitySpeed(int32 Level)
{
    if (Level <= 0) return TetrisConst::GRAVITY_SPEEDS[0];
    if (Level > 20) return TetrisConst::GRAVITY_SPEEDS[20];
    return TetrisConst::GRAVITY_SPEEDS[Level];
}

int32 FTetrisCore::Cell(const FTetrisBoardState& S, int32 Col, int32 Row)
{
    if (Col < 0 || Col >= TetrisConst::BoardW || Row < 0 || Row >= TetrisConst::BoardH) return 0;
    return S.Grid[Col][Row];
}

void FTetrisCore::FillCells(const FTetrisBoardState& S, FActivePiece P, TArray<TPair<int32,int32>>& Out, bool bActive)
{
    Out.Reset();
    for (int32 r = 0; r < 4; ++r)
    {
        for (int32 c = 0; c < 4; ++c)
        {
            if (GetShapeVal(P.Type, r, c) == 0) continue;
            int32 gx = P.X + c;
            int32 gy = P.Y + r;
            if (bActive && (gx < 0 || gx >= TetrisConst::BoardW || gy < 0 || gy >= TetrisConst::BoardH)) continue;
            Out.Add(TPair<int32,int32>(gx, gy));
        }
    }
}

void FTetrisCore::SetupCheese(FTetrisBoardState& S)
{
    // cheese race: pre-fill 9 rows with holes at random columns
    for (int32 r = TetrisConst::BoardH - 9; r < TetrisConst::BoardH; ++r)
    {
        int32 Hole = FMath::RandRange(0, TetrisConst::BoardW - 1);
        for (int32 c = 0; c < TetrisConst::BoardW; ++c)
        {
            if (c != Hole) S.Grid[c][r] = FMath::RandRange(1, 7);
        }
    }
}

FString FTetrisCore::ModeName(ETetrisMode M)
{
    int32 Idx = (int32)M;
    if (Idx < 0 || Idx >= 7) return TEXT("未知");
    return FString(TetrisConst::MODE_NAMES[Idx]);
}
