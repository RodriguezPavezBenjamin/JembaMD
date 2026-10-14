using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Launcher
{
    [STAThread]
    private static int Main(string[] args)
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        try
        {
            string python = Path.Combine(root, "runtime", "pythonw.exe");
            string app = Path.Combine(root, "src", "escritorio.py");
            if (!File.Exists(python) || !File.Exists(app))
                throw new Exception("Descomprime TODO el ZIP antes de abrir JembaMD.exe. Mantén el ejecutable junto a sus carpetas.");
            var start = new ProcessStartInfo(python, "\"" + app + "\"" +
                (Array.IndexOf(args, "--verificar") >= 0 ? " --verificar" : ""));
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.EnvironmentVariables.Remove("PYTHONHOME");
            start.EnvironmentVariables.Remove("PYTHONPATH");
            start.EnvironmentVariables["PYTHONNOUSERSITE"] = "1";
            start.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
            using (var process = Process.Start(start))
            {
                process.WaitForExit();
                if (process.ExitCode != 0)
                    throw new Exception("No se pudo iniciar JembaMD. Consulta .logs\\escritorio.log dentro de esta carpeta y las instrucciones de LEEME.txt.");
            }
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "JembaMD", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
