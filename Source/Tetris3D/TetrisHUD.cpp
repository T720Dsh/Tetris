// TETRIS 3D RUSH - HUD implementation (canvas UI, pure C++)
#include "TetrisHUD.h"
#include "TetrisGameMode.h"
#include "TetrisCore.h"
#include "TetrisBoardActor.h"
#include "Engine/Canvas.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Engine.h"
#include "CanvasItem.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "Engine/Font.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "IImageWrapper.h"
#include "ImageUtils.h"
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"

ATetrisHUD::ATetrisHUD()
{
    PrimaryActorTick.bCanEverTick = true;
}

void ATetrisHUD::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!GM)
    {
        GM = Cast<ATetrisGameMode>(UGameplayStatics::GetGameMode(this));
        if (GM) GM->State = ETetrisState::Menu;
    }
    if (!GM) return;
    if (GM->State == ETetrisState::Menu)
    {
        AutoYaw += DeltaSeconds * 0.25f;
        GM->RotateCamera(DeltaSeconds * 0.25f, 0.f);
    }
    HandleMouseClick();
    HandleRebindKeys();
}

bool ATetrisHUD::ProcessKeybindingsForInput()
{
    return false;
}

void ATetrisHUD::HandleRebindKeys()
{
    if (!GM || !bInSettings || SettingCursor < 0) return;
    APlayerController* PC = GetOwningPlayerController();
    if (!PC) return;
    static const FKey CommonKeys[] = {
        EKeys::A, EKeys::B, EKeys::C, EKeys::D, EKeys::E, EKeys::F, EKeys::G, EKeys::H,
        EKeys::I, EKeys::J, EKeys::K, EKeys::L, EKeys::M, EKeys::N, EKeys::O, EKeys::P,
        EKeys::Q, EKeys::R, EKeys::S, EKeys::T, EKeys::U, EKeys::V, EKeys::W, EKeys::X,
        EKeys::Y, EKeys::Z, EKeys::Zero, EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four,
        EKeys::Five, EKeys::Six, EKeys::Seven, EKeys::Eight, EKeys::Nine,
        EKeys::Left, EKeys::Right, EKeys::Up, EKeys::Down, EKeys::SpaceBar, EKeys::Tab,
        EKeys::Escape, EKeys::Enter, EKeys::F1, EKeys::F2, EKeys::F3, EKeys::F4, EKeys::F5,
        EKeys::F6, EKeys::F7, EKeys::F8, EKeys::F9, EKeys::F10, EKeys::F11, EKeys::F12
    };
    for (const FKey& Key : CommonKeys)
    {
        if (PC->WasInputKeyJustPressed(Key))
        {
            HandleKey(Key);
            return;
        }
    }
}

void ATetrisHUD::DrawText(const FString& S, float X, float Y, float Scale, const FLinearColor& Color, bool bCenter)
{
    if (!Canvas) return;
    FCanvasTextItem Item(FVector2D(X, Y), FText::FromString(S), GEngine->GetSmallFont(), Color);
    Item.Scale = FVector2D(Scale, Scale);
    if (bCenter)
    {
        float W = S.Len() * 9.f * Scale;
        float H = 12.f * Scale;
        Item.Position.X -= W * 0.5f;
        Item.Position.Y -= H * 0.5f;
    }
    Canvas->DrawItem(Item);
}

void ATetrisHUD::RebuildButtons()
{
    Buttons.Reset();
    if (!GM) return;
    float VW = Canvas ? Canvas->SizeX : 1920.f;
    float VH = Canvas ? Canvas->SizeY : 1080.f;

    if (bInSettings)
    {
        // settings buttons
        float X = VW * 0.55f;
        float Y = VH * 0.18f;
        auto Add = [&](const FString& Label, const FString& Tag)
        {
            FButton B;
            B.Label = Label;
            B.Tag = Tag;
            B.Rect = FBox2D(FVector2D(X, Y), FVector2D(X + VW * 0.36f, Y + VH * 0.055f));
            B.Color = FLinearColor(0.12f, 0.14f, 0.2f);
            Buttons.Add(B);
            Y += VH * 0.075f;
        };
        Add(TEXT("方块材质: 切换"), TEXT("skin"));
        Add(TEXT("背景主题: 切换"), TEXT("theme"));
        Add(TEXT("幽灵投影: 开/关"), TEXT("ghost"));
        Add(TEXT("音效: 开/关"), TEXT("sound"));
        Add(TEXT("键位: 移动 左/右 软降/旋转/硬降/暂存/暂停/视角"), TEXT("keys"));
        Add(TEXT("自定义背景图: 选择"), TEXT("bg"));
        Add(TEXT("返回主菜单"), TEXT("back"));
        return;
    }

    if (GM->State == ETetrisState::Menu)
    {
        float X = VW * 0.18f;
        float Y = VH * 0.30f;
        for (int32 i = 0; i < (int32)ETetrisMode::Count; ++i)
        {
            FButton B;
            B.Tag = FString::Printf(TEXT("mode_%d"), i);
            B.Rect = FBox2D(FVector2D(X, Y), FVector2D(X + VW * 0.34f, Y + VH * 0.065f));
            B.Color = FLinearColor(0.13f, 0.15f, 0.22f);
            Buttons.Add(B);
            Y += VH * 0.085f;
        }
        FButton S;
        S.Tag = TEXT("settings");
        S.Rect = FBox2D(FVector2D(X, Y + VH * 0.02f), FVector2D(X + VW * 0.14f, Y + VH * 0.02f + VH * 0.06f));
        S.Color = FLinearColor(0.1f, 0.2f, 0.3f);
        Buttons.Add(S);
        FButton Q;
        Q.Tag = TEXT("quit");
        Q.Rect = FBox2D(FVector2D(X + VW * 0.16f, Y + VH * 0.02f), FVector2D(X + VW * 0.30f, Y + VH * 0.02f + VH * 0.06f));
        Q.Color = FLinearColor(0.3f, 0.12f, 0.12f);
        Buttons.Add(Q);
    }
    else if (GM->State == ETetrisState::Result)
    {
        float X = VW * 0.40f;
        float Y = VH * 0.55f;
        FButton R;
        R.Tag = TEXT("retry");
        R.Label = TEXT("再来一局");
        R.Rect = FBox2D(FVector2D(X, Y), FVector2D(X + VW * 0.18f, Y + VH * 0.07f));
        R.Color = FLinearColor(0.15f, 0.3f, 0.2f);
        Buttons.Add(R);
        FButton M;
        M.Tag = TEXT("menu");
        M.Label = TEXT("返回主菜单");
        M.Rect = FBox2D(FVector2D(X + VW * 0.2f, Y), FVector2D(X + VW * 0.38f, Y + VH * 0.07f));
        M.Color = FLinearColor(0.2f, 0.2f, 0.35f);
        Buttons.Add(M);
    }
}

void ATetrisHUD::DrawMenu()
{
    if (!GM || !Canvas) return;
    float VW = Canvas->SizeX;
    float VH = Canvas->SizeY;

    DrawText(TEXT("TETRIS 3D RUSH"), VW * 0.18f, VH * 0.12f, 2.2f, FLinearColor(0.2f, 0.9f, 1.0f));
    DrawText(TEXT("伪3D立体场地 · 360°自由视角 · 现代竞速方块"), VW * 0.18f, VH * 0.20f, 0.85f, FLinearColor(0.8f, 0.8f, 0.9f));

    float X = VW * 0.18f;
    float Y = VH * 0.30f;
    for (int32 i = 0; i < (int32)ETetrisMode::Count; ++i)
    {
        ETetrisMode M = (ETetrisMode)i;
        FString Name = FTetrisCore::ModeName(M);
        FString Rec = TEXT("记录 --");
        if (GM->BestScores.Num() > i)
        {
            int32 Sc = GM->BestScores[i];
            if (Sc > 0) Rec = FString::Printf(TEXT("记录 %d 分"), Sc);
        }
        FLinearColor Col = (i == GM->SelectedModeIdx) ? FLinearColor(0.15f, 0.4f, 0.55f) : FLinearColor(0.13f, 0.15f, 0.22f);
        FBox2D R = FBox2D(FVector2D(X, Y), FVector2D(X + VW * 0.34f, Y + VH * 0.065f));
        FCanvasTileItem Tile(R.Min, R.Max - R.Min, Col);
        Canvas->DrawItem(Tile);
        DrawText(Name, X + VW * 0.015f, Y + VH * 0.012f, 1.0f, FLinearColor::White);
        DrawText(Rec, X + VW * 0.22f, Y + VH * 0.012f, 0.75f, FLinearColor(0.75f, 0.8f, 0.9f));
        Y += VH * 0.085f;
    }
    DrawText(TEXT("操作：←→移动 ↑旋转 ↓软降 空格硬降 C暂存"), X, Y + VH * 0.03f, 0.8f, FLinearColor(0.7f, 0.75f, 0.85f));
    DrawText(TEXT("鼠标拖拽旋转视角 滚轮缩放 Q/E视角 V复位 F正面"), X, Y + VH * 0.075f, 0.8f, FLinearColor(0.7f, 0.75f, 0.85f));
    DrawText(TEXT("ESC暂停 R重开 设置中可重绑键位"), X, Y + VH * 0.12f, 0.8f, FLinearColor(0.7f, 0.75f, 0.85f));

    // buttons (settings / quit)
    for (const FButton& B : Buttons)
    {
        FCanvasTileItem Tile(B.Rect.Min, B.Rect.Max - B.Rect.Min, B.Color);
        Canvas->DrawItem(Tile);
        FString L = B.Tag == TEXT("settings") ? TEXT("设置") : (B.Tag == TEXT("quit") ? TEXT("退出") : TEXT(""));
        DrawText(L, B.Rect.Min.X + 10.f, B.Rect.Min.Y + 8.f, 0.9f, FLinearColor::White);
    }
}

void ATetrisHUD::DrawSettings()
{
    if (!GM || !Canvas) return;
    float VW = Canvas->SizeX;
    float VH = Canvas->SizeY;

    // dim background
    FCanvasTileItem Dim(FVector2D(0, 0), FVector2D(VW, VH), FLinearColor(0.f, 0.f, 0.f, 0.6f));
    Canvas->DrawItem(Dim);

    DrawText(TEXT("设置"), VW * 0.5f, VH * 0.08f, 2.0f, FLinearColor(1.f, 0.9f, 0.3f), true);

    FString SkinName;
    switch (GM->Skin)
    {
    case ETetrisSkin::Classic: SkinName = TEXT("缁忓吀"); break;
    case ETetrisSkin::Neon: SkinName = TEXT("霓虹"); break;
    case ETetrisSkin::Candy: SkinName = TEXT("绯栨灉"); break;
    case ETetrisSkin::Matrix: SkinName = TEXT("鐭╅樀"); break;
    case ETetrisSkin::Metal: SkinName = TEXT("金属"); break;
    case ETetrisSkin::Ghost: SkinName = TEXT("幽灵"); break;
    default: SkinName = TEXT("缁忓吀"); break;
    }
    FString ThemeName;
    switch (GM->Theme)
    {
    case ETetrisTheme::Space: ThemeName = TEXT("星空"); break;
    case ETetrisTheme::City: ThemeName = TEXT("閮藉競"); break;
    case ETetrisTheme::Aurora: ThemeName = TEXT("鏋佸厜"); break;
    case ETetrisTheme::Grid: ThemeName = TEXT("缃戞牸"); break;
    case ETetrisTheme::Ocean: ThemeName = TEXT("娣辨捣"); break;
    default: ThemeName = TEXT("星空"); break;
    }

    float X = VW * 0.55f;
    float Y = VH * 0.18f;
    DrawText(FString::Printf(TEXT("方块材质：%s"), *SkinName), X, Y, 1.0f, FLinearColor::White);
    Y += VH * 0.075f;
    DrawText(FString::Printf(TEXT("背景主题：%s"), *ThemeName), X, Y, 1.0f, FLinearColor::White);
    Y += VH * 0.075f;
    DrawText(FString::Printf(TEXT("幽灵投影：%s"), GM->bShowGhost ? TEXT("开") : TEXT("关")), X, Y, 1.0f, FLinearColor::White);
    Y += VH * 0.075f;
    DrawText(FString::Printf(TEXT("音效：%s"), GM->bSoundOn ? TEXT("开") : TEXT("关")), X, Y, 1.0f, FLinearColor::White);
    Y += VH * 0.075f;
    DrawText(FString::Printf(TEXT("键位：%s"), *FString::Printf(TEXT("←→ %s %s 空格 C ESC R 视角Q/E/V/F"), *GM->Keybinds.FindRef(TEXT("rotate_cw")).ToString(), *GM->Keybinds.FindRef(TEXT("hard_drop")).ToString())), X, Y, 0.8f, FLinearColor(0.85f, 0.85f, 0.9f));
    Y += VH * 0.075f;
    DrawText(FString::Printf(TEXT("自定义背景图：%s"), GM->CustomBackgroundPath.IsEmpty() ? TEXT("无") : *FPaths::GetCleanFilename(GM->CustomBackgroundPath)), X, Y, 0.8f, FLinearColor(0.85f, 0.85f, 0.9f));
    Y += VH * 0.075f;

    for (const FButton& B : Buttons)
    {
        FCanvasTileItem Tile(B.Rect.Min, B.Rect.Max - B.Rect.Min, B.Color);
        Canvas->DrawItem(Tile);
        DrawText(B.Label, B.Rect.Min.X + 10.f, B.Rect.Min.Y + 8.f, 0.85f, FLinearColor::White);
    }

    if (SettingCursor >= 0)
    {
        DrawText(TEXT("按任意键绑定该操作... (ESC 取消)"), VW * 0.5f, VH * 0.80f, 1.1f, FLinearColor(1.f, 0.4f, 0.4f), true);
    }
}

void ATetrisHUD::DrawHUDGame()
{
    if (!GM || !Canvas) return;
    float VW = Canvas->SizeX;
    float VH = Canvas->SizeY;
    const FTetrisBoardState& S = GM->Board;

    DrawText(FString::Printf(TEXT("分数 %d"), S.Score), VW * 0.02f, VH * 0.05f, 1.4f, FLinearColor(1.f, 0.85f, 0.2f));
    DrawText(FString::Printf(TEXT("行数 %d/%s"), S.Lines, *FTetrisCore::ModeName(GM->Mode)), VW * 0.02f, VH * 0.11f, 1.0f, FLinearColor::White);
    DrawText(FString::Printf(TEXT("时间 %.1fs"), S.Elapsed), VW * 0.02f, VH * 0.16f, 1.0f, FLinearColor::White);
    DrawText(FString::Printf(TEXT("等级 %d"), S.Level), VW * 0.02f, VH * 0.21f, 1.0f, FLinearColor(0.6f, 0.8f, 1.f));
    DrawText(FString::Printf(TEXT("PPS %.2f"), S.Elapsed > 0.f ? S.Pieces / S.Elapsed : 0.f), VW * 0.02f, VH * 0.26f, 1.0f, FLinearColor(0.7f, 0.9f, 0.7f));
    if (S.LastClear > 0)
    {
        FString ComboTxt = S.LastCombo > 0 ? FString::Printf(TEXT("连击x%d"), S.LastCombo + 1) : TEXT("");
        FString L = FString::Printf(TEXT("%d消%s%s"), S.LastClear, S.bLastTSpin ? TEXT(" T旋") : TEXT(""), *ComboTxt);
        DrawText(L, VW * 0.02f, VH * 0.31f, 1.0f, FLinearColor(1.f, 0.6f, 0.8f));
    }
    // next piece
    DrawText(TEXT("下一个"), VW * 0.86f, VH * 0.08f, 1.0f, FLinearColor(0.8f, 0.8f, 0.9f));
    // hold
    DrawText(TEXT("暂存"), VW * 0.86f, VH * 0.28f, 1.0f, FLinearColor(0.8f, 0.8f, 0.9f));

    if (GM->State == ETetrisState::Paused)
    {
        DrawText(TEXT("已暂停"), VW * 0.5f, VH * 0.45f, 2.5f, FLinearColor(1.f, 1.f, 0.4f), true);
        DrawText(TEXT("ESC 继续  R 重开"), VW * 0.5f, VH * 0.52f, 1.0f, FLinearColor::White, true);
    }
}

void ATetrisHUD::DrawResult()
{
    if (!GM || !Canvas) return;
    float VW = Canvas->SizeX;
    float VH = Canvas->SizeY;
    const FTetrisBoardState& S = GM->Board;

    FCanvasTileItem Dim(FVector2D(0, 0), FVector2D(VW, VH), FLinearColor(0.f, 0.f, 0.f, 0.7f));
    Canvas->DrawItem(Dim);
    FString Title = GM->IsCleared() ? TEXT("通关!") : TEXT("游戏结束");
    DrawText(Title, VW * 0.5f, VH * 0.25f, 2.2f, FLinearColor(1.f, 0.9f, 0.3f), true);
    DrawText(FString::Printf(TEXT("模式：%s"), *FTetrisCore::ModeName(GM->Mode)), VW * 0.5f, VH * 0.32f, 1.0f, FLinearColor(0.6f, 0.8f, 1.f), true);
    DrawText(FString::Printf(TEXT("分数：%d"), S.Score), VW * 0.5f, VH * 0.38f, 1.4f, FLinearColor(1.f, 0.85f, 0.2f), true);
    DrawText(FString::Printf(TEXT("行数：%d   时间：%.1fs   最高连击：%d"), S.Lines, S.Elapsed, S.MaxCombo), VW * 0.5f, VH * 0.44f, 1.0f, FLinearColor::White, true);
    int32 M = (int32)GM->Mode;
    if (GM->BestScores.Num() > M && GM->BestScores[M] > 0)
    {
        DrawText(FString::Printf(TEXT("历史最佳：%d 分"), GM->BestScores[M]), VW * 0.5f, VH * 0.50f, 1.0f, FLinearColor(0.5f, 0.8f, 1.f), true);
    }

    for (const FButton& B : Buttons)
    {
        FCanvasTileItem Tile(B.Rect.Min, B.Rect.Max - B.Rect.Min, B.Color);
        Canvas->DrawItem(Tile);
        DrawText(B.Label, B.Rect.Min.X + 10.f, B.Rect.Min.Y + 8.f, 0.9f, FLinearColor::White);
    }
}

void ATetrisHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!GM)
    {
        GM = Cast<ATetrisGameMode>(UGameplayStatics::GetGameMode(this));
        if (!GM) return;
    }
    RebuildButtons();
    if (bInSettings) DrawSettings();
    else if (GM->State == ETetrisState::Menu) DrawMenu();
    else if (GM->State == ETetrisState::Result) DrawResult();
    else DrawHUDGame();
}

void ATetrisHUD::HandleMouseClick()
{
    if (!GM) return;
    APlayerController* PC = GetOwningPlayerController();
    if (!PC || !PC->WasInputKeyJustPressed(EKeys::LeftMouseButton)) return;

    float MX, MY;
    PC->GetMousePosition(MX, MY);
    for (const FButton& B : Buttons)
    {
        if (B.Rect.IsInside(FVector2D(MX, MY)))
        {
            if (bInSettings)
            {
                if (B.Tag == TEXT("skin")) { int32 S = (int32)GM->Skin; S = (S + 1) % (int32)ETetrisSkin::Count; GM->Skin = (ETetrisSkin)S; GM->SaveSettings(); }
                else if (B.Tag == TEXT("theme")) { int32 T = (int32)GM->Theme; T = (T + 1) % (int32)ETetrisTheme::Count; GM->Theme = (ETetrisTheme)T; GM->SaveSettings(); }
                else if (B.Tag == TEXT("ghost")) { GM->bShowGhost = !GM->bShowGhost; GM->SaveSettings(); }
                else if (B.Tag == TEXT("sound")) { GM->bSoundOn = !GM->bSoundOn; GM->SaveSettings(); }
                else if (B.Tag == TEXT("keys")) { SettingCursor = 0; }
                else if (B.Tag == TEXT("bg"))
                {
                    IDesktopPlatform* DP = FDesktopPlatformModule::Get();
                    if (DP)
                    {
                        TArray<FString> OutFiles;
                        bool bOk = DP->OpenFileDialog(nullptr, TEXT("选择背景图片"), TEXT(""), TEXT(""),
                            TEXT("图片文件 (*.png;*.jpg;*.jpeg;*.bmp)|*.png;*.jpg;*.jpeg;*.bmp"), EFileDialogFlags::None, OutFiles);
                        if (bOk && OutFiles.Num() > 0)
                        {
                            GM->CustomBackgroundPath = OutFiles[0];
                            GM->SaveSettings();
                            if (GM->BoardActor) GM->BoardActor->ApplyCustomBackground(OutFiles[0]);
                        }
                    }
                }
                else if (B.Tag == TEXT("back")) { bInSettings = false; GM->SaveSettings(); }
            }
            else if (GM->State == ETetrisState::Menu)
            {
                if (B.Tag.StartsWith(TEXT("mode_")))
                {
                    int32 M = FCString::Atoi(*B.Tag.RightChop(5));
                    GM->SelectedModeIdx = M;
                    GM->StartGame((ETetrisMode)M);
                }
                else if (B.Tag == TEXT("settings")) { bInSettings = true; SettingCursor = -1; }
                else if (B.Tag == TEXT("quit"))
                {
                    if (APlayerController* P = GetOwningPlayerController()) P->ConsoleCommand(TEXT("quit"));
                }
            }
            else if (GM->State == ETetrisState::Result)
            {
                if (B.Tag == TEXT("retry")) GM->RestartGame();
                else if (B.Tag == TEXT("menu")) GM->BackToMenu();
            }
            return;
        }
    }
}

void ATetrisHUD::HandleKey(FKey Key)
{
    if (!GM) return;
    if (bInSettings && SettingCursor >= 0)
    {
        if (Key == EKeys::Escape) { SettingCursor = -1; return; }
        // cycle through bindable actions
        TArray<FString> Actions = { TEXT("move_left"), TEXT("move_right"), TEXT("soft_drop"), TEXT("rotate_cw"),
            TEXT("rotate_ccw"), TEXT("rotate_180"), TEXT("hard_drop"), TEXT("hold"), TEXT("pause"), TEXT("restart"),
            TEXT("view_left"), TEXT("view_right"), TEXT("view_reset"), TEXT("view_front") };
        if (SettingCursor < Actions.Num())
        {
            GM->Keybinds.Add(Actions[SettingCursor], Key);
        }
        SettingCursor++;
        if (SettingCursor >= Actions.Num())
        {
            SettingCursor = -1;
            GM->SaveSettings();
        }
        return;
    }
}
