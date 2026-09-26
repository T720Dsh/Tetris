// TETRIS 3D RUSH - board actor implementation
#include "TetrisBoardActor.h"
#include "TetrisGameMode.h"
#include "TetrisCore.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Components/InputComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionTextureSample.h"
#include "Materials/MaterialExpressionTextureCoordinate.h"
#include "ImageUtils.h"
#include "UObject/ConstructorHelpers.h"
#include "Kismet/GameplayStatics.h"
#include "Math/UnrealMathUtility.h"
#include "Sound/SoundWave.h"
#include "Sound/SoundWaveProcedural.h"
#include "AudioDevice.h"
#include "Engine/Engine.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/UObjectIterator.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/PointLight.h"
#include "Engine/TextureCube.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialExpressionVertexColor.h"
#include "Components/AudioComponent.h"

// ---- geometry helpers ----
static void AddCube(TArray<FVector>& Verts, TArray<int32>& Inds, TArray<FLinearColor>& Colors,
                    const FVector& Center, float S, const FLinearColor& Color)
{
    int32 Base = Verts.Num();
    float H = S / 2.f;
    // 8 corners
    const FVector C[8] = {
        Center + FVector(-H,-H,-H), Center + FVector( H,-H,-H), Center + FVector( H, H,-H), Center + FVector(-H, H,-H),
        Center + FVector(-H,-H, H), Center + FVector( H,-H, H), Center + FVector( H, H, H), Center + FVector(-H, H, H)
    };
    // 6 faces, each 4 verts, 2 tris (CCW outward)
    const int32 F[6][4] = {
        {0,1,2,3},{5,4,7,6},{1,5,6,2},{4,0,3,7},{3,2,6,7},{4,5,1,0}
    };
    for (int32 i = 0; i < 6; ++i)
    {
        for (int32 v = 0; v < 4; ++v)
        {
            Verts.Add(C[F[i][v]]);
            Colors.Add(Color);
        }
        int32 b = Base + i * 4;
        Inds.Add(b); Inds.Add(b+1); Inds.Add(b+2);
        Inds.Add(b); Inds.Add(b+2); Inds.Add(b+3);
    }
}

static TArray<FColor> ToColor8(const TArray<FLinearColor>& C)
{
    TArray<FColor> Out;
    Out.SetNum(C.Num());
    for (int32 i = 0; i < C.Num(); ++i) Out[i] = C[i].ToFColor(true);
    return Out;
}

static void AddQuad(TArray<FVector>& Verts, TArray<int32>& Inds, TArray<FLinearColor>& Colors,
                    const FVector& A, const FVector& B, const FVector& C, const FVector& D, const FLinearColor& Col)
{
    int32 b = Verts.Num();
    Verts.Add(A); Verts.Add(B); Verts.Add(C); Verts.Add(D);
    Colors.Add(Col); Colors.Add(Col); Colors.Add(Col); Colors.Add(Col);
    Inds.Add(b); Inds.Add(b+1); Inds.Add(b+2);
    Inds.Add(b); Inds.Add(b+2); Inds.Add(b+3);
}

ATetrisBoardActor::ATetrisBoardActor()
{
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    BoardMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("BoardMesh"));
    BoardMesh->SetupAttachment(Root);
    BoardMesh->SetCastShadow(true);

    DecorMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("DecorMesh"));
    DecorMesh->SetupAttachment(Root);
    DecorMesh->SetCastShadow(false);

    GroundMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("GroundMesh"));
    GroundMesh->SetupAttachment(Root);
    GroundMesh->SetCastShadow(false);

    BackgroundMesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("BackgroundMesh"));
    BackgroundMesh->SetupAttachment(Root);
    BackgroundMesh->SetCastShadow(false);

    SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
    SpringArm->SetupAttachment(Root);
    SpringArm->bDoCollisionTest = false;
    SpringArm->TargetArmLength = 24.f;

    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(SpringArm);

}

UMaterialInterface* ATetrisBoardActor::LoadBaseMat(const TCHAR* Path)
{
    return LoadObject<UMaterialInterface>(nullptr, Path);
}

UMaterial* ATetrisBoardActor::MakeVertexMat()
{
    // editor-only material graph APIs are not available in packaged game builds;
    // use the engine default material (has compiled shaders in every build config)
    return UMaterial::GetDefaultMaterial(MD_Surface);
}

void ATetrisBoardActor::BeginPlay()
{
    Super::BeginPlay();
    GM = Cast<ATetrisGameMode>(UGameplayStatics::GetGameMode(this));
    if (!GM) return;

    // enable input on this non-pawn actor
    if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
    {
        EnableInput(PC);
        if (InputComponent)
        {
            SetupPlayerInputComponent(InputComponent);
        }
        // force this actor as the view target so the 3D scene is rendered
        PC->SetViewTargetWithBlend(this, 0.f);
    }

    // materials: engine vertex-color material (compiled shaders shipped with engine)
    UMaterialInterface* VC = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/EngineMaterials/VertexColorMaterial"));
    if (!VC) { UE_LOG(LogTemp, Warning, TEXT("VC_LOAD_FAIL")); VC = UMaterial::GetDefaultMaterial(MD_Surface); }
    else { UE_LOG(LogTemp, Warning, TEXT("VC_LOAD_OK %s"), *VC->GetName()); }
    BoardMesh->SetMaterial(0, VC);
    DecorMesh->SetMaterial(0, VC);
    GroundMesh->SetMaterial(0, VC);
    if (UMaterialInstanceDynamic* VCM = UMaterialInstanceDynamic::Create(VC, this))
    {
        BackgroundMesh->SetMaterial(0, VCM);
    }

    // dynamic lighting so the 3D scene is visible even in an empty level
    FActorSpawnParameters LP;
    if (ADirectionalLight* Sun = GetWorld()->SpawnActor<ADirectionalLight>(FVector(3.f, -8.f, 12.f), FRotator(-45.f, 30.f, 0.f), LP))
    {
        Sun->GetLightComponent()->SetIntensity(100.f);
        Sun->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    }
    if (ASkyLight* Sky = GetWorld()->SpawnActor<ASkyLight>(FVector::ZeroVector, FRotator::ZeroRotator, LP))
    {
        UTextureCube* SkyCube = LoadObject<UTextureCube>(nullptr, TEXT("/Engine/EngineMaterials/DefaultCubemap"));
        if (SkyCube)
        {
            Sky->GetLightComponent()->SetCubemap(SkyCube);
        }
        Sky->GetLightComponent()->SetIntensity(3.f);
        Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    }
    if (APointLight* Fill = GetWorld()->SpawnActor<APointLight>(FVector(0.f, 0.f, 16.f), FRotator::ZeroRotator, LP))
    {
        Fill->GetLightComponent()->SetIntensity(8000.f);
        Fill->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    }

    // sfx
    Beeps.Add(MakeBeep(440.f, 0.05f, 0.3f));   // move
    Beeps.Add(MakeBeep(560.f, 0.06f, 0.3f));   // rotate
    Beeps.Add(MakeBeep(300.f, 0.10f, 0.4f));   // soft drop
    Beeps.Add(MakeBeep(180.f, 0.12f, 0.5f));   // hard drop
    Beeps.Add(MakeBeep(660.f, 0.14f, 0.5f));   // lock
    Beeps.Add(MakeBeep(880.f, 0.20f, 0.5f));   // line clear
    Beeps.Add(MakeBeep(1100.f, 0.10f, 0.4f));  // hold
    Beeps.Add(MakeBeep(130.f, 0.30f, 0.5f));   // end
    Beeps.Add(MakeBeep(1000.f, 0.30f, 0.5f));  // clear

    BuildGround();
    BuildDecor();
    BuildSky();
    BuildBackground();

    if (GM && !GM->CustomBackgroundPath.IsEmpty())
    {
        ApplyCustomBackground(GM->CustomBackgroundPath);
    }
    RequestRender();
}



void ATetrisBoardActor::BuildGround()
{
    TArray<FVector> V;
    TArray<int32> I;
    TArray<FLinearColor> C;
    // large dark plane
    AddQuad(V, I, C, FVector(-40,-40,-1.1f), FVector(40,-40,-1.1f), FVector(40,40,-1.1f), FVector(-40,40,-1.1f),
            FLinearColor(0.09f,0.10f,0.18f));
    // grid lines
    for (int32 i = -40; i <= 40; i += 2)
    {
        float L = 0.015f;
        AddQuad(V, I, C, FVector(i,-40,-1.0f), FVector(i+L,-40,-1.0f), FVector(i+L,40,-1.0f), FVector(i,40,-1.0f),
                FLinearColor(0.24f,0.28f,0.44f));
        AddQuad(V, I, C, FVector(-40,i,-1.0f), FVector(40,i,-1.0f), FVector(40,i+L,-1.0f), FVector(-40,i+L,-1.0f),
                FLinearColor(0.24f,0.28f,0.44f));
    }
    // base platform under board
    AddCube(V, I, C, FVector(0,-0.3f,-1.6f), 12.f, FLinearColor(0.14f,0.18f,0.30f));
    // corner pillars
    for (int32 sx : {-5, 5})
    {
        AddCube(V, I, C, FVector(sx * 0.5f, -0.6f, 2.f), 0.35f, FLinearColor(0.2f,0.5f,1.0f));
        AddCube(V, I, C, FVector(sx * 0.5f, 0.4f, 2.f), 0.35f, FLinearColor(0.2f,0.5f,1.0f));
    }
    // top beam
    AddCube(V, I, C, FVector(0, 0.0f, 11.0f), 11.5f, FLinearColor(0.40f,0.48f,0.70f));
    GroundMesh->CreateMeshSection(0, V, I, TArray<FVector>(), TArray<FVector2D>(), ToColor8(C), TArray<FProcMeshTangent>(), false);
}

void ATetrisBoardActor::BuildDecor()
{
    // theme decoration - per theme
    ETetrisTheme Theme = GM ? GM->Theme : ETetrisTheme::Space;
    TArray<FVector> V;
    TArray<int32> I;
    TArray<FLinearColor> C;
    switch (Theme)
    {
    case ETetrisTheme::Space:
        for (int32 i = 0; i < 60; ++i)
        {
            FVector P(FMath::FRandRange(-70.f,70.f), FMath::FRandRange(-70.f,70.f), FMath::FRandRange(0.f,50.f));
            AddCube(V, I, C, P, 0.12f, FLinearColor(1.f,1.f,0.9f));
        }
        break;
    case ETetrisTheme::City:
        for (int32 i = 0; i < 30; ++i)
        {
            FVector P(FMath::FRandRange(-90.f,-20.f), FMath::FRandRange(-60.f,60.f), 0.f);
            float H = FMath::FRandRange(4.f, 30.f);
            P.Z = H * 0.5f;
            AddCube(V, I, C, P, H, FLinearColor(0.05f,0.07f,0.12f));
        }
        break;
    case ETetrisTheme::Aurora:
        for (int32 i = 0; i < 40; ++i)
        {
            FVector P(FMath::FRandRange(-60.f,60.f), FMath::FRandRange(-60.f,60.f), FMath::FRandRange(8.f,40.f));
            AddCube(V, I, C, P, FMath::FRandRange(0.2f,1.0f), FLinearColor(0.1f,0.9f,0.7f));
        }
        break;
    case ETetrisTheme::Grid:
        for (int32 i = -60; i <= 60; i += 4)
        {
            AddQuad(V, I, C, FVector(i,-60,-0.9f), FVector(i+0.1f,-60,-0.9f), FVector(i+0.1f,60,-0.9f), FVector(i,60,-0.9f),
                    FLinearColor(0.2f,0.4f,0.3f));
            AddQuad(V, I, C, FVector(-60,i,-0.9f), FVector(60,i,-0.9f), FVector(60,i+0.1f,-0.9f), FVector(-60,i+0.1f,-0.9f),
                    FLinearColor(0.2f,0.4f,0.3f));
        }
        break;
    case ETetrisTheme::Ocean:
        for (int32 i = 0; i < 50; ++i)
        {
            FVector P(FMath::FRandRange(-60.f,60.f), FMath::FRandRange(-60.f,60.f), FMath::FRandRange(-3.f,3.f));
            AddCube(V, I, C, P, 0.15f, FLinearColor(0.1f,0.5f,0.8f));
        }
        break;
    }
    DecorMesh->CreateMeshSection(0, V, I, TArray<FVector>(), TArray<FVector2D>(), ToColor8(C), TArray<FProcMeshTangent>(), false);
}

void ATetrisBoardActor::BuildSky()
{
    // fog color per theme - set world fog via exponential height fog would need actor; approximate with clear color
    ETetrisTheme Theme = GM ? GM->Theme : ETetrisTheme::Space;
    FLinearColor Fog;
    switch (Theme)
    {
    case ETetrisTheme::Space: Fog = FLinearColor(0.02f,0.02f,0.08f); break;
    case ETetrisTheme::City: Fog = FLinearColor(0.04f,0.05f,0.10f); break;
    case ETetrisTheme::Aurora: Fog = FLinearColor(0.01f,0.04f,0.07f); break;
    case ETetrisTheme::Grid: Fog = FLinearColor(0.03f,0.06f,0.05f); break;
    case ETetrisTheme::Ocean: Fog = FLinearColor(0.02f,0.05f,0.10f); break;
    }
    // set world clear color via WorldSettings
    if (GetWorld() && GetWorld()->GetWorldSettings())
    {
        GetWorld()->GetWorldSettings()->DefaultGameMode = nullptr; // noop
    }
    UGameplayStatics::GetPlayerCameraManager(this, 0);
}

void ATetrisBoardActor::UpdateCamera()
{
    if (!SpringArm || !Camera) return;
    FVector Center(0.f, 0.f, 4.f);
    SpringArm->TargetArmLength = Dist;
    // orbit around center
    float Cy = Center.Y - Dist * FMath::Cos(Pitch) * FMath::Cos(Yaw);
    float Cx = Center.X - Dist * FMath::Cos(Pitch) * FMath::Sin(Yaw);
    float Cz = Center.Z + Dist * FMath::Sin(Pitch);
    SpringArm->SetWorldLocation(FVector(Cx, Cy, Cz));
    SpringArm->SetWorldRotation(FRotationMatrix::MakeFromX(Center - FVector(Cx, Cy, Cz)).Rotator());
    Camera->SetWorldRotation(FRotationMatrix::MakeFromX(Center - FVector(Cx, Cy, Cz)).Rotator());
}

void ATetrisBoardActor::AddCameraRotation(float YawDelta, float PitchDelta)
{
    Yaw += YawDelta;
    Pitch = FMath::Clamp(Pitch + PitchDelta, -1.2f, 1.2f);
    UpdateCamera();
}

void ATetrisBoardActor::ZoomCamera(float Delta)
{
    Dist = FMath::Clamp(Dist + Delta, 8.f, 60.f);
    UpdateCamera();
}

void ATetrisBoardActor::ResetCamera()
{
    Yaw = 0.f; Pitch = 0.15f; Dist = 24.f;
    UpdateCamera();
}

void ATetrisBoardActor::FrontCamera()
{
    Yaw = 0.f; Pitch = 0.15f;
    UpdateCamera();
}

void ATetrisBoardActor::RequestRender()
{
    bRenderDirty = true;
}

void ATetrisBoardActor::RebuildMesh()
{
    if (!GM) return;
    const FTetrisBoardState& S = GM->Board;
    TArray<FVector> V;
    TArray<int32> I;
    TArray<FLinearColor> C;
    const float SZ = 0.95f;


    // board background panel
    {
        TArray<FVector> V2; TArray<int32> I2; TArray<FLinearColor> C2;
        AddQuad(V2, I2, C2, FVector(-5.6f, -0.25f, -1.2f), FVector(5.6f, -0.25f, -1.2f), FVector(5.6f, -0.25f, 10.6f), FVector(-5.6f, -0.25f, 10.6f),
                FLinearColor(0.12f,0.14f,0.24f));
        AddQuad(V2, I2, C2, FVector(-5.6f, 0.25f, -1.2f), FVector(5.6f, 0.25f, -1.2f), FVector(5.6f, 0.25f, 10.6f), FVector(-5.6f, 0.25f, 10.6f),
                FLinearColor(0.12f,0.14f,0.24f));
        // grid lines
        for (int32 c = 0; c <= TetrisConst::BoardW; ++c)
        {
            float X = (c - 5.f) * 1.f;
            for (int32 r = 0; r <= 22; ++r)
            {
                float Z = 9.5f - r;
                float L = 0.02f;
                AddQuad(V2, I2, C2, FVector(X - L, -0.22f, Z - 0.5f), FVector(X - L, -0.22f, Z + 0.5f), FVector(X + L, -0.22f, Z + 0.5f), FVector(X + L, -0.22f, Z - 0.5f),
                        FLinearColor(0.32f,0.38f,0.58f));
                AddQuad(V2, I2, C2, FVector(-5.f - 0.02f, -0.22f, Z), FVector(-5.f + 0.02f, -0.22f, Z), FVector(5.f - 0.02f, -0.22f, Z), FVector(5.f + 0.02f, -0.22f, Z),
                        FLinearColor(0.32f,0.38f,0.58f));
            }
        }
        for (int32 v = 0; v < V2.Num(); ++v) { V.Add(V2[v]); C.Add(C2[v]); }
        int32 B = V.Num() - V2.Num();
        for (int32 id : I2) I.Add(B + id);
    }

    // locked blocks
    const FLinearColor* Pal = TetrisConst::SKIN_COLORS[(int32)GM->Skin];
    if (S.Grid.Num() >= TetrisConst::BoardW && S.Grid.Num() > 0 && S.Grid[0].Num() >= TetrisConst::BoardH) {
    for (int32 r = 0; r < TetrisConst::BoardH; ++r)
    {
        for (int32 c = 0; c < TetrisConst::BoardW; ++c)
        {
            int32 T = S.Grid[c][r];
            if (T <= 0) continue;
            float X = (c - 4.5f);
            float Z = (9.5f - r);
            FVector P(X, 0.f, Z);
            FLinearColor Col = Pal[T];
            Col.A = 1.f;
            AddCube(V, I, C, P, SZ, Col);
        }
    }
    }

    // active piece + ghost
    if (S.Cur.Type > 0 && !S.bGameOver)
    {
        TArray<TPair<int32,int32>> Cells;
        FTetrisCore::FillCells(S, S.Cur, Cells, false);
        for (const auto& Cell : Cells)
        {
            if (Cell.Value < 0) continue;
            float X = (Cell.Key - 4.5f);
            float Z = (9.5f - Cell.Value);
            FLinearColor Col = Pal[S.Cur.Type];
            Col.A = 1.f;
            AddCube(V, I, C, FVector(X, 0.f, Z), SZ, Col);
        }
        // ghost
        if (GM->bShowGhost)
        {
            FActivePiece G = S.Cur;
            while (FTetrisCore::CanPlace(S, G)) { G.Y++; }
            G.Y--;
            TArray<TPair<int32,int32>> GCells;
            FTetrisCore::FillCells(S, G, GCells, false);
            for (const auto& Cell : GCells)
            {
                if (Cell.Value < 0) continue;
                float X = (Cell.Key - 4.5f);
                float Z = (9.5f - Cell.Value);
                FLinearColor Col = Pal[S.Cur.Type];
                Col.R *= 0.25f; Col.G *= 0.25f; Col.B *= 0.25f;
                Col.A = 0.6f;
                AddCube(V, I, C, FVector(X, 0.f, Z), SZ * 0.92f, Col);
            }
        }
    }

    BoardMesh->CreateMeshSection(0, V, I, TArray<FVector>(), TArray<FVector2D>(), ToColor8(C), TArray<FProcMeshTangent>(), false);
    bRenderDirty = false;
}

void ATetrisBoardActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!GM) return;
    if (GM->State == ETetrisState::Menu)
    {
        if (BoardMesh->IsMeshSectionVisible(0)) BoardMesh->SetMeshSectionVisible(0, false);
        if (GroundMesh->IsMeshSectionVisible(0)) GroundMesh->SetMeshSectionVisible(0, false);
        if (DecorMesh->IsMeshSectionVisible(0)) DecorMesh->SetMeshSectionVisible(0, false);
        if (BackgroundMesh->IsMeshSectionVisible(0)) BackgroundMesh->SetMeshSectionVisible(0, false);
    }
    else
    {
        if (!BoardMesh->IsMeshSectionVisible(0)) BoardMesh->SetMeshSectionVisible(0, true);
        if (!GroundMesh->IsMeshSectionVisible(0)) GroundMesh->SetMeshSectionVisible(0, true);
        if (!DecorMesh->IsMeshSectionVisible(0)) DecorMesh->SetMeshSectionVisible(0, true);
        if (!BackgroundMesh->IsMeshSectionVisible(0)) BackgroundMesh->SetMeshSectionVisible(0, true);
    }

    // reset camera when entering gameplay (fixes drag-rotated view from menu click)
    static ETetrisState PrevState = ETetrisState::Menu;
    if (GM->State == ETetrisState::Playing && PrevState != ETetrisState::Playing)
    {
        ResetCamera();
    }
    PrevState = GM->State;

    // keep our camera as view target during startup
    if (GetWorld()->GetTimeSeconds() < 5.f)
    {
        APlayerController* PCS = UGameplayStatics::GetPlayerController(this, 0);
        if (PCS && PCS->GetViewTarget() != this) PCS->SetViewTargetWithBlend(this, 0.f);
    }
    // DAS/ARR handling
    // mouse orbit drag
    APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
    if (PC)
    {
        if (PC->IsInputKeyDown(EKeys::LeftMouseButton))
        {
            FVector2D MouseDelta;
        float DX = 0.f, DY = 0.f;
        PC->GetInputMouseDelta(DX, DY);
        if (DX != 0.f || DY != 0.f)
        {
            AddCameraRotation(-DY * 0.006f, -DX * 0.006f);
        }
            {
                AddCameraRotation(-MouseDelta.Y * 0.006f, -MouseDelta.X * 0.006f);
            }
        }
        // wheel zoom
        float Wheel = PC->GetInputAnalogKeyState(EKeys::MouseWheelAxis);
        if (Wheel != 0.f)
        {
            ZoomCamera(-Wheel * 30.f * DeltaSeconds);
        }
    }
    if (GM->State == ETetrisState::Playing)
    {
        if (bLeftHeld || bRightHeld)
        {
            int32 Dir = bLeftHeld ? -1 : 1;
            DasTimer += DeltaSeconds * 1000.f;
            if (DasTimer >= GM->DasTime)
            {
                if (ArrTimer <= 0.f)
                {
                    if (FTetrisCore::TryMove(GM->Board, Dir, 0)) { RequestRender(); GM->PlaySfx(TEXT("move")); }
                    ArrTimer = GM->ArrTime;
                }
                ArrTimer -= DeltaSeconds * 1000.f;
            }
        }
        if (bDownHeld)
        {
            DownTimer += DeltaSeconds;
            if (DownTimer >= 0.05f)
            {
                DownTimer = 0.f;
                if (FTetrisCore::TryMove(GM->Board, 0, 1))
                {
                    GM->Board.Score += 1;
                    GM->PlaySfx(TEXT("soft"));
                    RequestRender();
                }
            }
        }
        // gravity
        float Interval = 1.0f / FTetrisCore::GravitySpeed(GM->Board.Level);
        GM->Board.LastFall += DeltaSeconds;
        if (GM->Board.LastFall >= Interval)
        {
            GM->Board.LastFall = FMath::Fmod(GM->Board.LastFall, Interval);
            if (!FTetrisCore::TryMove(GM->Board, 0, 1))
            {
                // piece settled: auto-lock after short grace
                GM->Board.LastFall = 0.f;
            }
        }
    }

    if (bRenderDirty) RebuildMesh();
}

// ---- input ----
void ATetrisBoardActor::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    if (!GM) GM = Cast<ATetrisGameMode>(UGameplayStatics::GetGameMode(this));
    TMap<FString, FKey> K = GM ? GM->Keybinds : TMap<FString, FKey>();

    auto BindKeyFn = [&](const FString& Act, const FKey& Key)
    {
        if (!Key.IsValid()) return;
        if (Act == TEXT("move_left")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::MoveLeft);
        else if (Act == TEXT("move_right")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::MoveRight);
        else if (Act == TEXT("soft_drop")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::SoftDown);
        else if (Act == TEXT("rotate_cw")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::RotateCW);
        else if (Act == TEXT("rotate_ccw")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::RotateCCW);
        else if (Act == TEXT("rotate_180")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::Rotate180);
        else if (Act == TEXT("hard_drop")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::HardDrop);
        else if (Act == TEXT("hold")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::HoldPiece);
        else if (Act == TEXT("pause")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::PauseGame);
        else if (Act == TEXT("restart")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::RestartGame);
        else if (Act == TEXT("view_left")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::ViewLeft);
        else if (Act == TEXT("view_right")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::ViewRight);
        else if (Act == TEXT("view_reset")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::ViewReset);
        else if (Act == TEXT("view_front")) PlayerInputComponent->BindKey(Key, IE_Pressed, this, &ATetrisBoardActor::ViewFront);
    };
    // default keybinds fallback if settings missing
    TMap<FString, FKey> Def;
    Def.Add(TEXT("move_left"), EKeys::Left);
    Def.Add(TEXT("move_right"), EKeys::Right);
    Def.Add(TEXT("soft_drop"), EKeys::Down);
    Def.Add(TEXT("rotate_cw"), EKeys::Up);
    Def.Add(TEXT("rotate_ccw"), EKeys::Z);
    Def.Add(TEXT("rotate_180"), EKeys::A);
    Def.Add(TEXT("hard_drop"), EKeys::SpaceBar);
    Def.Add(TEXT("hold"), EKeys::C);
    Def.Add(TEXT("pause"), EKeys::Escape);
    Def.Add(TEXT("restart"), EKeys::R);
    Def.Add(TEXT("view_left"), EKeys::Q);
    Def.Add(TEXT("view_right"), EKeys::E);
    Def.Add(TEXT("view_reset"), EKeys::V);
    Def.Add(TEXT("view_front"), EKeys::F);

    TArray<FString> Actions = { TEXT("move_left"), TEXT("move_right"), TEXT("soft_drop"), TEXT("rotate_cw"),
        TEXT("rotate_ccw"), TEXT("rotate_180"), TEXT("hard_drop"), TEXT("hold"), TEXT("pause"), TEXT("restart"),
        TEXT("view_left"), TEXT("view_right"), TEXT("view_reset"), TEXT("view_front") };
    for (const FString& A : Actions)
    {
        FKey* FK = K.Find(A);
        BindKeyFn(A, FK && FK->IsValid() ? *FK : Def[A]);
    }

    // release handlers for held keys (rebindable)
    auto BindRelease = [&](const FString& Act, void (ATetrisBoardActor::*Fn)())
    {
        FKey* FK = K.Find(Act);
        FKey Key = FK && FK->IsValid() ? *FK : Def[Act];
        if (Key.IsValid())
        {
            PlayerInputComponent->BindKey(Key, IE_Released, this, Fn);
        }
    };
    BindRelease(TEXT("move_left"), &ATetrisBoardActor::ReleaseLeft);
    BindRelease(TEXT("move_right"), &ATetrisBoardActor::ReleaseRight);
    BindRelease(TEXT("soft_drop"), &ATetrisBoardActor::ReleaseDown);

    // mouse orbit: pressed via direct key, handled in Tick via mouse delta
    PlayerInputComponent->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &ATetrisBoardActor::OnMouseDrag);
    PlayerInputComponent->BindKey(EKeys::LeftMouseButton, IE_Released, this, &ATetrisBoardActor::OnMouseRelease);
}

void ATetrisBoardActor::MoveLeft()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    bLeftHeld = true; bRightHeld = false;
    DasTimer = 0.f; ArrTimer = 0.f; DasDir = -1;
    if (FTetrisCore::TryMove(GM->Board, -1, 0)) { RequestRender(); GM->PlaySfx(TEXT("move")); }
}

void ATetrisBoardActor::MoveRight()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    bRightHeld = true; bLeftHeld = false;
    DasTimer = 0.f; ArrTimer = 0.f; DasDir = 1;
    if (FTetrisCore::TryMove(GM->Board, 1, 0)) { RequestRender(); GM->PlaySfx(TEXT("move")); }
}

void ATetrisBoardActor::SoftDown()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    bDownHeld = true;
    if (FTetrisCore::TryMove(GM->Board, 0, 1)) { GM->Board.Score += 1; GM->PlaySfx(TEXT("soft")); RequestRender(); }
}

void ATetrisBoardActor::RotateCW()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    if (FTetrisCore::TryRotate(GM->Board, 1)) { GM->PlaySfx(TEXT("rotate")); RequestRender(); }
}

void ATetrisBoardActor::RotateCCW()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    if (FTetrisCore::TryRotate(GM->Board, -1)) { GM->PlaySfx(TEXT("rotate")); RequestRender(); }
}

void ATetrisBoardActor::Rotate180()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    if (FTetrisCore::TryRotate(GM->Board, 2)) { GM->PlaySfx(TEXT("rotate")); RequestRender(); }
}

void ATetrisBoardActor::HardDrop()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    int32 D = FTetrisCore::HardDrop(GM->Board);
    if (D > 0) { GM->Board.Score += D * 2; GM->PlaySfx(TEXT("drop")); }
    FTetrisCore::Lock(GM->Board);
    GM->PlaySfx(TEXT("lock"));
    if (GM->Board.LastClear > 0) GM->PlaySfx(TEXT("clear"));
    RequestRender();
    GM->UpdateState();
}

void ATetrisBoardActor::HoldPiece()
{
    if (!GM || GM->State != ETetrisState::Playing) return;
    if (FTetrisCore::DoHold(GM->Board)) { GM->PlaySfx(TEXT("hold")); RequestRender(); }
}

void ATetrisBoardActor::PauseGame()
{
    if (!GM) return;
    if (GM->State == ETetrisState::Playing || GM->State == ETetrisState::Paused) GM->TogglePause();
}

void ATetrisBoardActor::RestartGame()
{
    if (!GM) return;
    if (GM->State == ETetrisState::Playing || GM->State == ETetrisState::Paused || GM->State == ETetrisState::Result)
    {
        GM->RestartGame();
        RequestRender();
    }
}

void ATetrisBoardActor::ViewLeft() { if (GM) AddCameraRotation(-0.6f, 0.f); }
void ATetrisBoardActor::ViewRight() { if (GM) AddCameraRotation(0.6f, 0.f); }
void ATetrisBoardActor::ViewReset() { if (GM) ResetCamera(); }
void ATetrisBoardActor::ViewFront() { if (GM) FrontCamera(); }

void ATetrisBoardActor::OnMouseWheel(float V)
{
    // bound to scroll up/down as pressed; V carries +1/-1
    if (GM)
    {
        ZoomCamera(V * -2.f);
    }
}

void ATetrisBoardActor::OnMouseDrag()
{
    bLmbDragging = true;
}

void ATetrisBoardActor::OnMouseRelease()
{
    bLmbDragging = false;
}

// ---- sfx ----
USoundWave* ATetrisBoardActor::MakeBeep(float Freq, float Dur, float Volume)
{
    const int32 SampleRate = 22050;
    const int32 NumChannels = 2;
    int32 NumSamples = FMath::Max(1, (int32)(SampleRate * Dur));
    TArray<int16> Data;
    Data.SetNum(NumSamples * NumChannels);
    for (int32 i = 0; i < NumSamples; ++i)
    {
        float Env = 1.f - (float)i / NumSamples;
        float V = FMath::Sin(2.f * PI * Freq * (float)i / SampleRate) * Env * Volume;
        int16 S = (int16)(FMath::Clamp(V, -1.f, 1.f) * 32767.f);
        Data[i * NumChannels] = S;
        Data[i * NumChannels + 1] = S;
    }
    USoundWaveProcedural* W = NewObject<USoundWaveProcedural>(this);
    W->SetSampleRate(SampleRate);
    W->NumChannels = NumChannels;
    W->Duration = Dur;
    W->bLooping = false;
    W->QueueAudio((const uint8*)Data.GetData(), NumSamples * NumChannels * sizeof(int16));
    return W;
}

void ATetrisBoardActor::PlayWave(USoundWave* W)
{
    if (!W) return;
    UGameplayStatics::PlaySound2D(this, W);
}

void ATetrisBoardActor::PlayBeep(const FString& Name)
{
    int32 Idx = -1;
    if (Name == TEXT("move")) Idx = 0;
    else if (Name == TEXT("rotate")) Idx = 1;
    else if (Name == TEXT("soft")) Idx = 2;
    else if (Name == TEXT("drop")) Idx = 3;
    else if (Name == TEXT("lock")) Idx = 4;
    else if (Name == TEXT("clear")) Idx = 5;
    else if (Name == TEXT("hold")) Idx = 6;
    else if (Name == TEXT("end")) Idx = 7;
    else if (Name == TEXT("clear")) Idx = 5;
    if (Idx >= 0 && Idx < Beeps.Num()) PlayWave(Beeps[Idx]);
}

// ---- custom background ----
void ATetrisBoardActor::BuildBackground()
{
    // theme sky gradient backdrop - bands so the scene is never pure black
    ETetrisTheme Theme = GM ? GM->Theme : ETetrisTheme::Space;
    FLinearColor Top, Bot;
    switch (Theme)
    {
    case ETetrisTheme::Space:  Top = FLinearColor(0.02f,0.03f,0.12f); Bot = FLinearColor(0.08f,0.05f,0.20f); break;
    case ETetrisTheme::City:   Top = FLinearColor(0.02f,0.04f,0.10f); Bot = FLinearColor(0.35f,0.20f,0.10f); break;
    case ETetrisTheme::Aurora: Top = FLinearColor(0.01f,0.06f,0.08f); Bot = FLinearColor(0.10f,0.25f,0.18f); break;
    case ETetrisTheme::Grid:   Top = FLinearColor(0.01f,0.05f,0.03f); Bot = FLinearColor(0.10f,0.35f,0.20f); break;
    case ETetrisTheme::Ocean:  Top = FLinearColor(0.02f,0.06f,0.16f); Bot = FLinearColor(0.10f,0.35f,0.55f); break;
    default: Top = FLinearColor(0.02f,0.03f,0.12f); Bot = FLinearColor(0.08f,0.05f,0.20f); break;
    }
    TArray<FVector> V; TArray<int32> I; TArray<FLinearColor> C;
    const float Y = -90.f;
    const int32 Bands = 10;
    for (int32 b = 0; b < Bands; ++b)
    {
        float t0 = (float)b / (float)Bands;
        float t1 = (float)(b + 1) / (float)Bands;
        float z0 = -80.f + 160.f * t0;
        float z1 = -80.f + 160.f * t1;
        FLinearColor Col((1.f - t0) * Bot.R + t0 * Top.R, (1.f - t0) * Bot.G + t0 * Top.G, (1.f - t0) * Bot.B + t0 * Top.B);
        AddQuad(V, I, C, FVector(-120.f, Y, z0), FVector(120.f, Y, z0), FVector(120.f, Y, z1), FVector(-120.f, Y, z1), Col);
    }
    BackgroundMesh->CreateMeshSection(0, V, I, TArray<FVector>(), TArray<FVector2D>(), ToColor8(C), TArray<FProcMeshTangent>(), false);
    BackgroundMesh->SetVisibility(true);
}

void ATetrisBoardActor::ApplyCustomBackground(const FString& Path)
{
    if (Path.IsEmpty() || !FPaths::FileExists(Path)) return;
    UTexture2D* Tex = FImageUtils::ImportFileAsTexture2D(Path);
    if (!Tex) return;
    Tex->CompressionSettings = TC_Default;
    Tex->SRGB = true;
    Tex->UpdateResource();

    UMaterial* Mat = NewObject<UMaterial>();
    Mat->SetFlags(RF_Transient);
    

    UMaterialExpressionTextureCoordinate* TC = NewObject<UMaterialExpressionTextureCoordinate>(Mat);
    BackgroundMesh->SetMaterial(0, UMaterial::GetDefaultMaterial(MD_Surface));
    BackgroundMat = UMaterial::GetDefaultMaterial(MD_Surface);
}
