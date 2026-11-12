void main (string[] args) {
    Test.init (ref args);
    Test.add_func ("/studio/folder-membership", () => {
        try {
            var path = Path.build_filename (DirUtils.make_tmp ("studio-preferences-XXXXXX"), "desktop.ini");
            var prefs = new StudioPreferences (path);
            prefs.load ();
            assert (prefs.number ("Launcher", "rows", 3, 2, 6) == 3);
            prefs.key.set_string ("Folder one", "name", "Work");
            prefs.key.set_string ("Folder two", "name", "Games");
            prefs.assign ("app.desktop", "Folder one");
            prefs.assign ("app.desktop", "Folder two");
            assert (prefs.members ("Folder one").length == 0);
            assert (prefs.members ("Folder two").length == 1);
            prefs.assign ("app.desktop", "Folder two");
            assert (prefs.members ("Folder two").length == 1);
            prefs.key.set_integer ("Launcher", "rows", 1000);
            prefs.save ();
            var loaded = new StudioPreferences (path); loaded.load ();
            assert (loaded.folders ().length == 2);
            assert (loaded.number ("Launcher", "rows", 3, 2, 6) == 6);
            assert ("app.desktop" in loaded.members ("Folder two"));
            loaded.assign ("app.desktop", null);
            assert (loaded.members ("Folder two").length == 0);
            loaded.key.remove_group ("Folder one");
            assert (loaded.folders ().length == 1);
        } catch (Error e) { error ("Preferences test: %s", e.message); }
    });
    Test.run ();
}
