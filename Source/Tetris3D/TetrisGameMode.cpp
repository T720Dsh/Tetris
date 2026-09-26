// TETRIS 3D RUSH - game mode implementation
#include "TetrisGameMode.h"
#include "TetrisBoardActor.h"
#include "TetrisHUD.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "Engine/Engine.h"

ATetrisGameMode::ATetrisGameMode()
{
    PrimaryActorTick.bCanEverTick = true;
    DefaultPawnClass = nullptr; // we spawn board actor as the world root; input via board actor's own InputComponent
    HUDClass = ATetrisHUD::StaticClass();
    PlayerControllerClass = APlayerController::StaticClass();
}

FString ATetrisGameMode::SettingsPath() const
{
    return FPaths::ProjectSavedDir() + TEXT("settings.ini");
}

FString ATetrisGameMode::RecordsPath() const
{
    return FPaths::ProjectSavedDir() + TEXT("records.ini");
}

void ATetrisGameMode::LoadSettings()
{
    // defaults
    Skin = ETetrisSkin::Classic;
    Theme = ETetrisTheme::Space;
    bShowGhost = true;
    bSoundOn = true;
    DasTime = 130; ArrTime = 30;
    CustomBackgroundPath = TEXT("");
    Keybinds.Reset();
    Keybinds.Add(TEXT("move_left"), EKeys::Left);
    Keybinds.Add(TEXT("move_right"), EKeys::Right);
    Keybinds.Add(TEXT("soft_drop"), EKeys::Down);
    Keybinds.Add(TEXT("rotate_cw"), EKeys::Up);
    Keybinds.Add(TEXT("rotate_ccw"), EKeys::Z);
    Keybinds.Add(TEXT("rotate_180"), EKeys::A);
    Keybinds.Add(TEXT("hard_drop"), EKeys::SpaceBar);
    Keybinds.Add(TEXT("hold"), EKeys::C);
    Keybinds.Add(TEXT("pause"), EKeys::Escape);
    Keybinds.Add(TEXT("restart"), EKeys::R);
    Keybinds.Add(TEXT("view_left"), EKeys::Q);
    Keybinds.Add(TEXT("view_right"), EKeys::E);
    Keybinds.Add(TEXT("view_reset"), EKeys::V);
    Keybinds.Add(TEXT("view_front"), EKeys::F);

    FString Cfg;
    if (FFileHelper::LoadFileToString(Cfg, *SettingsPath()))
    {
        TArray<FString> Lines;
        Cfg.ParseIntoArray(Lines, TEXT("\n"), true);
        for (const FString& L : Lines)
        {
            FString K, V;
            if (!L.Split(TEXT("="), &K, &V)) continue;
            if (K == TEXT("skin")) Skin = (ETetrisSkin)FCString::Atoi(*V);
            else if (K == TEXT("theme")) Theme = (ETetrisTheme)FCString::Atoi(*V);
            else if (K == TEXT("ghost")) bShowGhost = (V == TEXT("1"));
            else if (K == TEXT("sound")) bSoundOn = (V == TEXT("1"));
            else if (K == TEXT("das")) DasTime = FCString::Atoi(*V);
            else if (K == TEXT("arr")) ArrTime = FCString::Atoi(*V);
            else if (K == TEXT("custombg")) CustomBackgroundPath = V;
            else if (K.StartsWith(TEXT("kb_")))
            {
                FString Act = K.RightChop(3);
                FKey Key(*V);
                if (Key.IsValid()) Keybinds.Add(Act, Key);
            }
        }
    }

    // records
    BestScores.SetNum((int32)ETetrisMode::Count);
    BestLines.SetNum((int32)ETetrisMode::Count);
    BestTimes.SetNum((int32)ETetrisMode::Count);
    FString Rc;
    if (FFileHelper::LoadFileToString(Rc, *RecordsPath()))
    {
        TArray<FString> Lines;
        Rc.ParseIntoArray(Lines, TEXT("\n"), true);
        for (const FString& L : Lines)
        {
            FString K, V;
            if (!L.Split(TEXT("="), &K, &V)) continue;
            int32 M = FCString::Atoi(*K);
            if (M < 0 || M >= (int32)ETetrisMode::Count) continue;
            TArray<FString> Parts;
            V.ParseIntoArray(Parts, TEXT(","), true);
            if (Parts.Num() == 3)
            {
                BestScores[M] = FCString::Atoi(*Parts[0]);
                BestLines[M] = FCString::Atoi(*Parts[1]);
                BestTimes[M] = FCString::Atof(*Parts[2]);
            }
        }
    }
}

void ATetrisGameMode::SaveSettings()
{
    FString Cfg;
    Cfg += FString::Printf(TEXT("skin=%d\n"), (int32)Skin);
    Cfg += FString::Printf(TEXT("theme=%d\n"), (int32)Theme);
    Cfg += FString::Printf(TEXT("ghost=%d\n"), bShowGhost ? 1 : 0);
    Cfg += FString::Printf(TEXT("sound=%d\n"), bSoundOn ? 1 : 0);
    Cfg += FString::Printf(TEXT("das=%d\n"), DasTime);
    Cfg += FString::Printf(TEXT("arr=%d\n"), ArrTime);
    Cfg += FString::Printf(TEXT("custombg=%s\n"), *CustomBackgroundPath);
    for (const auto& KV : Keybinds)
    {
        Cfg += FString::Printf(TEXT("kb_%s=%s\n"), *KV.Key, *KV.Value.ToString());
    }
    FFileHelper::SaveStringToFile(Cfg, *SettingsPath());
}

void ATetrisGameMode::SaveRecords()
{
    FString Rc;
    for (int32 M = 0; M < (int32)ETetrisMode::Count; ++M)
    {
        Rc += FString::Printf(TEXT("%d=%d,%d,%.2f\n"), M, BestScores[M], BestLines[M], BestTimes[M]);
    }
    FFileHelper::SaveStringToFile(Rc, *RecordsPath());
}

void ATetrisGameMode::BeginPlay()
{
    Super::BeginPlay();
    LoadSettings();
    State = ETetrisState::Menu;

    // spawn board actor (3D scene root)
    FActorSpawnParameters Params;
    BoardActor = GetWorld()->SpawnActor<ATetrisBoardActor>(ATetrisBoardActor::StaticClass(), FVector::ZeroVector, FRotator::ZeroRotator, Params);
    if (BoardActor)
    {
        BoardActor->ResetCamera();
        // bind player view to board camera so the 3D scene is rendered
        if (APlayerController* PC2 = UGameplayStatics::GetPlayerController(this, 0))
        {
            PC2->SetViewTargetWithBlend(BoardActor, 0.f);
        }
    }

    // mouse cursor visible for canvas UI
    if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
    {
        PC->bShowMouseCursor = true;
        PC->bEnableClickEvents = true;
        PC->bEnableMouseOverEvents = true;
    }
}

void ATetrisGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (State == ETetrisState::Playing)
    {
        FTetrisCore::Tick(Board, DeltaSeconds);
        UpdateState();
        if (BoardActor) BoardActor->RequestRender();
    }
    else if (bResultPending)
    {
        ResultTimer -= DeltaSeconds;
        if (ResultTimer <= 0.f)
        {
            bResultPending = false;
            State = ETetrisState::Result;
        }
    }
}

void ATetrisGameMode::StartGame(ETetrisMode M)
{
    Mode = M;
    FTetrisCore::NewGame(Board, M);
    State = ETetrisState::Playing;
    if (BoardActor) BoardActor->RequestRender();
}

void ATetrisGameMode::UpdateState()
{
    if (State != ETetrisState::Playing) return;
    if (Board.bGameOver)
    {
        // record
        int32 M = (int32)Mode;
        if (Board.Score > BestScores[M]) BestScores[M] = Board.Score;
        if (Board.Lines > BestLines[M]) BestLines[M] = Board.Lines;
        float T = Board.Elapsed;
        if (BestTimes[M] <= 0.f || T < BestTimes[M]) BestTimes[M] = T;
        SaveRecords();
        State = ETetrisState::Result;
        PlaySfx(TEXT("end"));
        return;
    }
    switch (Mode)
    {
    case ETetrisMode::Sprint20:
    case ETetrisMode::Sprint40:
    case ETetrisMode::Sprint100:
        if (Board.Lines >= ((int32)Mode + 1) * 20)
        {
            Board.bCleared = true;
            int32 M = (int32)Mode;
            if (Board.Score > BestScores[M]) BestScores[M] = Board.Score;
            float T = Board.Elapsed;
            if (BestTimes[M] <= 0.f || T < BestTimes[M]) BestTimes[M] = T;
            SaveRecords();
            State = ETetrisState::Result;
            PlaySfx(TEXT("clear"));
        }
        break;
    case ETetrisMode::Marathon1500:
        if (Board.Lines >= 1500)
        {
            Board.bCleared = true;
            int32 M = (int32)Mode;
            if (Board.Score > BestScores[M]) BestScores[M] = Board.Score;
            SaveRecords();
            State = ETetrisState::Result;
            PlaySfx(TEXT("clear"));
        }
        break;
    case ETetrisMode::Blitz120:
        if (Board.Elapsed >= 120.f)
        {
            int32 M = (int32)Mode;
            if (Board.Score > BestScores[M]) BestScores[M] = Board.Score;
            SaveRecords();
            State = ETetrisState::Result;
            PlaySfx(TEXT("end"));
        }
        break;
    case ETetrisMode::Cheese40:
        if (Board.Lines >= 40)
        {
            Board.bCleared = true;
            int32 M = (int32)Mode;
            if (Board.Score > BestScores[M]) BestScores[M] = Board.Score;
            float T = Board.Elapsed;
            if (BestTimes[M] <= 0.f || T < BestTimes[M]) BestTimes[M] = T;
            SaveRecords();
            State = ETetrisState::Result;
            PlaySfx(TEXT("clear"));
        }
        break;
    default:
        break;
    }
}

void ATetrisGameMode::TogglePause()
{
    if (State == ETetrisState::Playing) State = ETetrisState::Paused;
    else if (State == ETetrisState::Paused) State = ETetrisState::Playing;
}

void ATetrisGameMode::BackToMenu()
{
    State = ETetrisState::Menu;
    bResultPending = false;
    FTetrisCore::Init(Board);
}

void ATetrisGameMode::RestartGame()
{
    StartGame(Mode);
}

bool ATetrisGameMode::IsCleared() const
{
    return Board.bCleared;
}

bool ATetrisGameMode::IsTimedOut() const
{
    return Board.bGameOver;
}

void ATetrisGameMode::RotateCamera(float YawDelta, float PitchDelta)
{
    if (BoardActor) BoardActor->AddCameraRotation(YawDelta, PitchDelta);
}

void ATetrisGameMode::ZoomCamera(float Delta)
{
    if (BoardActor) BoardActor->ZoomCamera(Delta);
}

void ATetrisGameMode::ResetCamera()
{
    if (BoardActor) BoardActor->ResetCamera();
}

void ATetrisGameMode::FrontCamera()
{
    if (BoardActor) BoardActor->FrontCamera();
}

void ATetrisGameMode::PlaySfx(const FString& Name)
{
    if (!bSoundOn) return;
    // runtime-generated beep via USoundWave - simplified: create tone in BoardActor? skip detailed synth.
    // We synthesize via simple AudioComponent pitch/volume using procedural wave created once.
    if (BoardActor) BoardActor->PlayBeep(Name);
}
