public class OverrideStore : Object {
    private string applications;
    private string backups;
    public OverrideStore (string applications, string backups) {
        this.applications = applications;
        this.backups = backups;
    }
    private string target (string id) throws Error {
        if (id.contains ("/") || !id.has_suffix (".desktop"))
            throw new IOError.INVALID_ARGUMENT ("Invalid application ID");
        return Path.build_filename (applications, id);
    }
    private string read (string path) throws Error {
        string data;
        FileUtils.get_contents (path, out data);
        return data;
    }
    public bool managed (string id) {
        return FileUtils.test (Path.build_filename (backups, id), FileTest.EXISTS);
    }
    private void verify (string path, KeyFile record) throws Error {
        if (FileUtils.test (path, FileTest.IS_SYMLINK))
            throw new IOError.FAILED ("This entry is a managed symlink. Change it in your Nix configuration.");
        if (read (path) != record.get_string ("Backup", "last"))
            throw new IOError.FAILED ("This entry changed outside Pantheon Studio. Resolve the change before continuing.");
    }
    public void save (string id, string source, string name, string icon, bool hidden) throws Error {
        var path = target (id);
        if (FileUtils.test (path, FileTest.IS_SYMLINK))
            throw new IOError.FAILED ("This entry is a managed symlink. Change it in your Nix configuration.");
        if (name.strip () == "") throw new IOError.INVALID_ARGUMENT ("Enter an application name.");
        var record = new KeyFile ();
        var backup = Path.build_filename (backups, id);
        bool exists = FileUtils.test (path, FileTest.EXISTS);
        if (managed (id)) {
            record.load_from_file (backup, KeyFileFlags.NONE);
            verify (path, record);
        } else {
            record.set_boolean ("Backup", "existed", exists);
            record.set_string ("Backup", "original", exists ? read (path) : "");
        }
        var entry = new KeyFile ();
        entry.load_from_file (exists ? path : source, KeyFileFlags.KEEP_COMMENTS | KeyFileFlags.KEEP_TRANSLATIONS);
        foreach (var key in entry.get_keys ("Desktop Entry")) {
            if (key.has_prefix ("Name[")) entry.remove_key ("Desktop Entry", key);
        }
        entry.set_string ("Desktop Entry", "Name", name.strip ());
        entry.set_string ("Desktop Entry", "Icon", icon.strip ());
        entry.set_boolean ("Desktop Entry", "NoDisplay", hidden);
        string data = entry.to_data ();
        record.set_string ("Backup", "last", data);
        if (DirUtils.create_with_parents (applications, 0755) != 0 || DirUtils.create_with_parents (backups, 0700) != 0)
            throw new IOError.FAILED ("Could not create settings directories.");
        // Save the recovery record before changing the desktop entry.
        FileUtils.set_contents (backup, record.to_data ());
        FileUtils.set_contents (path, data);
    }
    public void restore (string id) throws Error {
        var path = target (id);
        var backup = Path.build_filename (backups, id);
        var record = new KeyFile ();
        record.load_from_file (backup, KeyFileFlags.NONE);
        verify (path, record);
        if (record.get_boolean ("Backup", "existed"))
            FileUtils.set_contents (path, record.get_string ("Backup", "original"));
        else File.new_for_path (path).delete ();
        File.new_for_path (backup).delete ();
    }
}
