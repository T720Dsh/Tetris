// TETRIS 3D RUSH - editor target
using UnrealBuildTool;
using System.Collections.Generic;

public class Tetris3DEditorTarget : TargetRules
{
    public Tetris3DEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("Tetris3D");
    }
}
