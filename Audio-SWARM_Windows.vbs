Option Explicit

' Audio-SWARM Windows launcher
' Place this file in the same folder as main.py.
' Automatically creates a Desktop shortcut with a custom icon and launches main.py without a console window.

Dim fso, shell, appFolder, mainScript
Dim launchError, launchDescription

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

appFolder = fso.GetParentFolderName(WScript.ScriptFullName)
mainScript = fso.BuildPath(appFolder, "main.py")

If Not fso.FileExists(mainScript) Then
    MsgBox "Audio-SWARM could not find main.py." & vbCrLf & vbCrLf & _
           "Place Audio-SWARM_Windows.vbs in the same folder as main.py.", _
           vbExclamation, "Audio-SWARM Launcher"
    WScript.Quit 1
End If

' Create or update the Desktop shortcut automatically
EnsureDesktopShortcut fso, shell, appFolder

' Ensure relative paths used by Audio-SWARM resolve from the application folder.
shell.CurrentDirectory = appFolder

' Try the Python windowed launcher first. Do not wait for Audio-SWARM to exit.
' Window style 0 hides the launcher's window; waitOnReturn=False returns immediately.
On Error Resume Next
Err.Clear
shell.Run "pyw -3 " & QuoteArg(mainScript), 0, False
If Err.Number = 0 Then WScript.Quit 0

' Fallback for installations that provide pythonw.exe but not pyw.exe.
Err.Clear
shell.Run "pythonw " & QuoteArg(mainScript), 0, False
If Err.Number = 0 Then WScript.Quit 0

launchError = Err.Number
launchDescription = Err.Description
On Error GoTo 0

MsgBox "Audio-SWARM could not be launched without a console window." & vbCrLf & vbCrLf & _
       "Make sure Python 3 is installed with Tkinter and Audio-SWARM's required packages, " & _
       "and that pyw.exe or pythonw.exe is available on PATH." & vbCrLf & vbCrLf & _
       "Windows error " & CStr(launchError) & ": " & launchDescription, _
       vbExclamation, "Audio-SWARM Launcher"
WScript.Quit 1

Sub EnsureDesktopShortcut(fsoObj, shellObj, folderPath)
    On Error Resume Next
    Dim desktopPath, shortcutPath, iconFile, shortcut

    desktopPath = shellObj.SpecialFolders("Desktop")
    shortcutPath = fsoObj.BuildPath(desktopPath, "Audio-SWARM.lnk")
    iconFile = fsoObj.BuildPath(folderPath, "img\audio-swarm-logo-2.ico")

    Set shortcut = shellObj.CreateShortcut(shortcutPath)
    shortcut.TargetPath = WScript.ScriptFullName
    shortcut.WorkingDirectory = folderPath
    shortcut.Description = "Launch Audio-SWARM"

    If fsoObj.FileExists(iconFile) Then
        shortcut.IconLocation = iconFile & ", 0"
    End If

    shortcut.Save
    On Error GoTo 0
End Sub

Function QuoteArg(value)
    QuoteArg = Chr(34) & value & Chr(34)
End Function

