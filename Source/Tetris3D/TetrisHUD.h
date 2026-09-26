// TETRIS 3D RUSH - HUD: canvas-based UI (menu / settings / gameplay / result)
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "TetrisTypes.h"
#include "TetrisHUD.generated.h"

class ATetrisGameMode;

UCLASS()
class ATetrisHUD : public AHUD
{
    GENERATED_BODY()

public:
    ATetrisHUD();

    virtual void DrawHUD() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual bool ProcessKeybindingsForInput();
    void HandleMouseClick();
    void HandleKey(FKey Key);
    void HandleRebindKeys();

protected:
    ATetrisGameMode* GM = nullptr;

    struct FButton
    {
        FString Label;
        FString Tag;
        FBox2D Rect;
        FLinearColor Color;
    };
    TArray<FButton> Buttons;

    // menu
    void DrawMenu();
    void DrawSettings();
    void DrawHUDGame();
    void DrawResult();
    void DrawText(const FString& S, float X, float Y, float Scale, const FLinearColor& Color, bool bCenter = false);

    void RebuildButtons();

    // settings state
    bool bInSettings = false;
    int32 SettingCursor = -1;   // active rebind row
    int32 SkinIdx = 0;
    int32 ThemeIdx = 0;

    float AutoYaw = 0.f;
};
