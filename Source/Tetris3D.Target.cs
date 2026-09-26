// TETRIS 3D RUSH - game target
using UnrealBuildTool;
using System.Collections.Generic;

public class Tetris3DTarget : TargetRules
{
    public Tetris3DTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("Tetris3D");
    }
}
