void main (string[] args) {
    Test.init (ref args);
    Test.add_func ("/overrides/roundtrip", () => {
        try {
            string root = DirUtils.make_tmp ("studio-test-XXXXXX");
            string apps = Path.build_filename (root, "applications");
            string source = Path.build_filename (root, "source.desktop");
            string original = "[Desktop Entry]\nType=Application\nName=Original\nName[fr]=Original FR\nExec=example %U\nIcon=example\nActions=New;\n\n[Desktop Action New]\nName=New\nExec=example --new\n";
            FileUtils.set_contents (source, original);
            var store = new OverrideStore (apps, Path.build_filename (root, "backups"));
            string target = Path.build_filename (apps, "example.desktop");
            store.save ("example.desktop", source, "Custom", "custom-icon", true);
            var entry = new KeyFile (); entry.load_from_file (target, KeyFileFlags.NONE);
            assert (entry.get_string ("Desktop Entry", "Name") == "Custom");
            assert (!entry.has_key ("Desktop Entry", "Name[fr]"));
            assert (entry.get_boolean ("Desktop Entry", "NoDisplay"));
            assert (entry.get_string ("Desktop Entry", "Exec") == "example %U");
            assert (entry.get_string ("Desktop Action New", "Exec") == "example --new");
            store.save ("example.desktop", source, "Again", "other", false);
            store.restore ("example.desktop");
            assert (!FileUtils.test (target, FileTest.EXISTS));
            FileUtils.set_contents (target, original);
            store.save ("example.desktop", source, "Custom", "custom", false);
            store.restore ("example.desktop");
            string restored; FileUtils.get_contents (target, out restored); assert (restored == original);
            store.save ("example.desktop", source, "Custom", "custom", false);
            FileUtils.set_contents (target, "external change");
            bool rejected = false;
            try { store.restore ("example.desktop"); } catch (Error e) { rejected = true; }
            assert (rejected);
            rejected = false;
            try { store.save ("../bad.desktop", source, "Bad", "bad", false); } catch (Error e) { rejected = true; }
            assert (rejected);
            string link = Path.build_filename (apps, "link.desktop");
            File.new_for_path (link).make_symbolic_link (source);
            rejected = false;
            try { store.save ("link.desktop", source, "Bad", "bad", false); } catch (Error e) { rejected = true; }
            assert (rejected);
        } catch (Error e) { error ("Test failed: %s", e.message); }
    });
    Test.run ();
}
