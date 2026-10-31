using UnityEngine;

// Asks the first connected player in a new world for its co-op mode (ArchipelagoCoop), with the mouse free.
// Until someone picks, the mod holds back what it would keep per slot (ArchipelagoCoop.Ready).
public class ArchipelagoCoopPrompt : MonoBehaviour
{
    public static bool IsOpen { get; private set; }

    private Rect window = new Rect(0, 0, 520, 10);
    private string pick;

    private void Update()
    {
        // Another player may pick first: the world's key arriving closes it here too.
        if (ArchipelagoCoop.Asking) ArchipelagoCoop.ChooseMode();
        bool open = ArchipelagoCoop.Asking && ArchipelagoConnection.IsConnected && Player.m_localPlayer != null;
        if (pick != null) { ArchipelagoCoop.SetMode(pick); pick = null; open = false; }
        if (open == IsOpen) return;
        IsOpen = open;
        if (open) window.center = new Vector2(Screen.width / 2f, Screen.height / 2f);
        else if (!InventoryGui.IsVisible() && !Menu.IsVisible() && !ArchipelagoLogicWindow.IsOpen)
        {
            ZCursor.LockState = CursorLockMode.Locked;
            ZCursor.Hide();
        }
    }

    private void LateUpdate()
    {
        if (!IsOpen) return;
        ZCursor.LockState = CursorLockMode.None;
        ZCursor.Show();
    }

    private void OnGUI()
    {
        if (!IsOpen) return;
        window = GUILayout.Window(GetInstanceID(), window, Draw, "Archipelago: co-op mode for this world");
    }

    private void Draw(int id)
    {
        GUILayout.Label("Nobody has connected in this world before, so pick how it's played. The world keeps this for good.");
        GUILayout.Space(6);
        if (GUILayout.Button("Shared slot", GUILayout.Height(30))) pick = ArchipelagoCoop.Shared;
        GUILayout.Label("One player connects to Archipelago; the others just join the world, and their checks count too.");
        GUILayout.Space(6);
        if (GUILayout.Button("A slot each", GUILayout.Height(30))) pick = ArchipelagoCoop.Separate;
        GUILayout.Label("Every player connects to their own slot, with their own options, researches, checks and goal.");
        GUI.DragWindow(new Rect(0, 0, 10000, 22));
    }
}
