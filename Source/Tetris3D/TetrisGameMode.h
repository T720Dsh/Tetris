// TETRIS 3D RUSH - game mode: state machine, settings, board state holder
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "TetrisTypes.h"
#include "TetrisCore.h"
#include "TetrisGameMode.generated.h"

class ATetrisBoardActor;

UENUM()
enum class ETetrisState : uint8
{
    Menu,
    Playing,
    Paused,
    Result
};

UCLASS()
class ATetrisGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    ATetrisGameMode();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

    FTetrisBoardState Board;

    // state
    ETetrisState State = ETetrisState::Menu;
    ETetrisMode Mode = ETetrisMode::Sprint20;
    int32 SelectedModeIdx = 0;

    // settings
    ETetrisSkin Skin = ETetrisSkin::Classic;
    ETetrisTheme Theme = ETetrisTheme::Space;
    int32 MatStyle = 0;
    float GravityOverride = 0.f;
    bool bShowGhost = true;
    bool bFullscreen = false;
    bool bSoundOn = true;
    bool bDAS = true;
    int32 DasTime = 130;
    int32 ArrTime = 30;
    TMap<FString, FKey> Keybinds;
    FString CustomBackgroundPath;

    // per-mode bests (records)
    TArray<int32> BestScores;
    TArray<int32> BestLines;
    TArray<float> BestTimes;

    void StartGame(ETetrisMode M);
    void TogglePause();
    void BackToMenu();
    void RestartGame();
    void SaveSettings();
    void LoadSettings();
    void LoadRecords();
    void SaveRecords();
    FString SettingsPath() const;
    FString RecordsPath() const;

    bool IsCleared() const;
    bool IsTimedOut() const;

    // input forwarding
    void OnInputAction(const FString& Action);

    // camera control from mouse drag
    void RotateCamera(float YawDelta, float PitchDelta);
    void ZoomCamera(float Delta);
    void ResetCamera();
    void FrontCamera();

    UPROPERTY() ATetrisBoardActor* BoardActor = nullptr;

    // sfx
    void PlaySfx(const FString& Name);
    void UpdateState();

protected:
    float ResultTimer = 0.f;
    float ProbeTimer = 0.f;
    bool bResultPending = false;
};
