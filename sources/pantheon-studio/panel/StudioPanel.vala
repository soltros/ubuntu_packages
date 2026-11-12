// SPDX-License-Identifier: GPL-3.0-or-later
public class StudioPanel : Object {
    private Gtk.CssProvider provider = new Gtk.CssProvider ();
    private FileMonitor? monitor;
    public StudioPanel () {
        Gtk.StyleContext.add_provider_for_screen (Gdk.Screen.get_default (), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1);
        var prefs = new StudioPreferences ();
        try {
            DirUtils.create_with_parents (Path.get_dirname (prefs.path), 0700);
            monitor = File.new_for_path (Path.get_dirname (prefs.path)).monitor_directory (FileMonitorFlags.NONE);
            monitor.changed.connect (() => reload ());
        } catch (Error e) { warning ("Studio panel monitor: %s", e.message); }
        reload ();
    }
    private void reload () {
        var prefs = StudioPreferences.current ();
        string css = "";
        if (prefs.flag ("Panel", "custom")) {
            string bg = prefs.text ("Panel", "background", "#242424");
            string fg = prefs.text ("Panel", "foreground", "#ffffff");
            if (!Regex.match_simple ("^#[0-9a-fA-F]{6}$", bg) || !Regex.match_simple ("^#[0-9a-fA-F]{6}$", fg)) return;
            int opacity = prefs.number ("Panel", "opacity", 90, 0, 100);
            int height = prefs.number ("Panel", "height", 30, 30, 64);
            int spacing = prefs.number ("Panel", "spacing", 6, 0, 24);
            css = "panel { background-image: none; background-color: alpha(%s, %s); min-height: %dpx; } panel > box { background-color: transparent; box-shadow: none; margin-bottom: 0; } panel label, panel image { color: %s; text-shadow: none; -gtk-icon-shadow: none; } panel .composited-indicator { padding-left: %dpx; padding-right: %dpx; }".printf (
                bg, (opacity / 100.0).to_string (), height, fg, spacing, spacing);
        }
        try { provider.load_from_data (css); } catch (Error e) { warning ("Studio panel CSS: %s", e.message); }
    }
}
