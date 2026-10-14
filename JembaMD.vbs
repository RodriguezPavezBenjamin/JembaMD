Option Explicit
Dim shell, files, folder, python, script
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
python = files.BuildPath(folder, ".venv\Scripts\pythonw.exe")
script = files.BuildPath(folder, "src\escritorio.py")
shell.CurrentDirectory = folder
If files.FileExists(python) Then
    shell.Run Chr(34) & python & Chr(34) & " " & Chr(34) & script & Chr(34), 0, False
Else
    MsgBox "Abre iniciar.bat una vez para preparar JembaMD.", 64, "JembaMD"
End If
