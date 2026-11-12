// SPDX-License-Identifier: GPL-3.0-or-later
public class Slingshot.Widgets.StudioFolder : Gtk.Button {
    public signal void app_launched ();
    public StudioFolder (string name, string icon, Gee.ArrayList<Backend.App> apps) {
        get_style_context ().add_class (Gtk.STYLE_CLASS_FLAT);
        var box = new Gtk.Box (Gtk.Orientation.VERTICAL, 6);
        var image = new Gtk.Image.from_icon_name (icon, Gtk.IconSize.DIALOG) {
            pixel_size = StudioPreferences.current ().number ("Launcher", "icon-size", 64, 24, 96), margin_top = 9
        };
        box.add (image);
        box.add (new Gtk.Label (name) { ellipsize = Pango.EllipsizeMode.END, max_width_chars = 16, width_chars = 16 });
        add (box); tooltip_text = name;
        var popover = new Gtk.Popover (this);
        var content = new Gtk.Box (Gtk.Orientation.VERTICAL, 8) { margin = 12 };
        content.add (new Gtk.Label (name));
        var grid = new Gtk.FlowBox () { selection_mode = Gtk.SelectionMode.NONE, max_children_per_line = 3, min_children_per_line = 3 };
        foreach (var app in apps) {
            var button = new AppButton (app);
            button.app_launched.connect (() => { popover.popdown (); app_launched (); });
            grid.add (button);
        }
        var scroll = new Gtk.ScrolledWindow (null, null) { min_content_width = 450, min_content_height = 240, max_content_height = 420, propagate_natural_height = true };
        scroll.add (grid); content.add (scroll); popover.add (content);
        clicked.connect (() => { popover.show_all (); popover.popup (); });
        destroy.connect (() => popover.destroy ());
    }
}
