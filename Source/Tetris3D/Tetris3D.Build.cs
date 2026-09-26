// TETRIS 3D RUSH - UE5 C++ module build rules
using UnrealBuildTool;

public class Tetris3D : ModuleRules
{
    public Tetris3D(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "UMG",
            "Slate",
            "SlateCore",
            "ProceduralMeshComponent",
            "EnhancedInput",
            "RenderCore",
            "RHI"
        });

        PrivateDependencyModuleNames.AddRange(new string[] {
            "ImageWrapper",
            "DesktopPlatform"
        });
    }
}
