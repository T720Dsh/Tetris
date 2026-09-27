// TETRIS 3D RUSH - board actor: procedural 3D grid + orbit camera + input + sfx
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "ProceduralMeshComponent.h"
#include "TetrisTypes.h"
#include "TetrisBoardActor.generated.h"

class ATetrisGameMode;

UCLASS()
class ATetrisBoardActor : public AActor
{
    GENERATED_BODY()

public:
    ATetrisBoardActor();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent);

    // camera
    void AddCameraRotation(float YawDelta, float PitchDelta);
    void ZoomCamera(float Delta);
    void ResetCamera();
    void FrontCamera();

    // render
    void RequestRender();
    void RebuildMesh();

    // sfx
    void PlayBeep(const FString& Name);

    UPROPERTY() USceneComponent* Root;
    UPROPERTY() USpringArmComponent* SpringArm;
    UPROPERTY() UCameraComponent* Camera;
    UPROPERTY() UProceduralMeshComponent* BoardMesh;
    UPROPERTY() UProceduralMeshComponent* DecorMesh;
    UPROPERTY() UProceduralMeshComponent* GroundMesh;
    UPROPERTY() UProceduralMeshComponent* BackgroundMesh;
    UPROPERTY() UMaterialInstanceDynamic* BlockMat;
    UPROPERTY() UMaterialInstanceDynamic* DecorMat;
    UPROPERTY() UMaterialInstanceDynamic* GroundMat;
    UPROPERTY() UMaterialInterface* BackgroundMat;
    UPROPERTY() TArray<UMaterialInterface*> BlockMaterials;
    int32 MatStyle = 0;
    int32 AppliedMatStyle = -1;
    int32 AppliedTheme = -1;
    void CycleMatStyle();
    void ApplyMatStyle();
    void CycleTheme();

    void ApplyCustomBackground(const FString& Path);
    void BuildBackground();

    // input state
    bool bLeftHeld = false;
    bool bRightHeld = false;
    bool bDownHeld = false;
    float DasTimer = 0.f;
    float ArrTimer = 0.f;
    float DownTimer = 0.f;
    int32 DasDir = 0;

    float Yaw = 0.f;
    float Pitch = 0.15f;
    float Dist = 24.f;

    bool bRenderDirty = true;
    bool bLmbDragging = false;

    // theme decoration data
    TArray<FVector> Stars;
    TArray<FVector> Buildings;

protected:
    void MoveLeft();
    void MoveRight();
    void SoftDown();
    void RotateCW();
    void RotateCCW();
    void Rotate180();
    void HardDrop();
    void HoldPiece();
    void PauseGame();
    void RestartGame();
    void ViewLeft();
    void ViewRight();
    void ViewReset();
    void ViewFront();
    void ReleaseLeft() { bLeftHeld = false; DasTimer = 0.f; }
    void ReleaseRight() { bRightHeld = false; DasTimer = 0.f; }
    void ReleaseDown() { bDownHeld = false; DownTimer = 0.f; }

    void OnMouseDrag();
    void OnMouseRelease();
    void OnMouseWheel(float V);
    void UpdateCamera();    void BuildGround();
    void BuildDecor();
    void BuildSky();

    ATetrisGameMode* GM = nullptr;
    UMaterialInterface* LoadBaseMat(const TCHAR* Path);
    UMaterial* MakeVertexMat();
    UPROPERTY() TArray<USoundWave*> Beeps;
    USoundWave* MakeBeep(float Freq, float Dur, float Volume);
    void PlayWave(USoundWave* W);
};
