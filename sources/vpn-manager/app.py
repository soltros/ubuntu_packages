#!/usr/bin/env python3
import sys
from concurrent.futures import ThreadPoolExecutor
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib, Gtk
from backend import VPNError
from session import Session


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='VPN Manager', default_width=620, default_height=700)
        self.backend = Session()
        self.set_icon_name("io.github.soltros.VPNManager")
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.busy = False
        self.state = None
        self.toast = Adw.ToastOverlay()
        self.set_content(self.toast)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast.set_child(layout)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title='VPN Manager', subtitle='Your connections, in one place'))
        self.refresh_button = Gtk.Button(icon_name='view-refresh-symbolic', tooltip_text='Refresh connections')
        self.refresh_button.connect('clicked', lambda _: self.refresh())
        header.pack_start(Gtk.Image(icon_name='io.github.soltros.VPNManager', pixel_size=24))
        header.pack_start(self.refresh_button)
        self.import_button = Gtk.Button(label='Import config', css_classes=['suggested-action'])
        self.import_button.connect('clicked', self.choose_file)
        header.pack_end(self.import_button)
        layout.append(header)
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        layout.append(scroll)
        clamp = Adw.Clamp(maximum_size=560, tightening_threshold=460)
        scroll.set_child(clamp)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22,
                            margin_top=24, margin_bottom=28, margin_start=24, margin_end=24)
        clamp.set_child(self.body)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hero.append(Gtk.Image(icon_name='network-vpn-symbolic', pixel_size=56))
        self.title_label = Gtk.Label(label='Checking connections…', css_classes=['title-1'])
        hero.append(self.title_label)
        self.detail = Gtk.Label(label='Reading Tailscale and WireGuard status', wrap=True, justify=Gtk.Justification.CENTER,
                                css_classes=['dim-label'])
        hero.append(self.detail)
        self.spinner = Gtk.Spinner(halign=Gtk.Align.CENTER)
        hero.append(self.spinner)
        self.body.append(hero)
        note = Gtk.Label(label='One connection at a time. Switching disconnects your current VPN before connecting the next one.',
                         wrap=True, xalign=0, css_classes=['dim-label'])
        self.body.append(note)
        self.warning = Gtk.Label(wrap=True, xalign=0, selectable=True, css_classes=['error'])
        self.body.append(self.warning)
        self.ts_group = Adw.PreferencesGroup(title='TAILSCALE', description='Reach your devices and private network')
        self.body.append(self.ts_group)
        self.ts_row = Adw.ActionRow(title='Tailscale', subtitle='Checking…')
        self.ts_row.add_prefix(Gtk.Image(icon_name='network-workgroup-symbolic'))
        self.ts_button = Gtk.Button(label='Connect', valign=Gtk.Align.CENTER)
        self.ts_button.connect('clicked', lambda _: self.action('tailscale'))
        self.ts_row.add_suffix(self.ts_button)
        self.ts_group.add(self.ts_row)
        self.wg_group = Adw.PreferencesGroup(title='WIREGUARD', description='Import a .conf file from your VPN provider')
        self.body.append(self.wg_group)
        self.rows = []
        self.footer = Gtk.Label(label='Status refreshes automatically. Switching briefly interrupts connectivity.',
                                wrap=True, xalign=0, css_classes=['dim-label', 'caption'])
        self.body.append(self.footer)
        self.run(self.backend.start)
        GLib.timeout_add_seconds(5, self.tick)

    def tick(self):
        if not self.get_visible():
            return GLib.SOURCE_REMOVE
        if self.backend.authorized:
            self.refresh()
        return GLib.SOURCE_CONTINUE

    def run(self, operation, message=None):
        if self.busy:
            return
        self.busy = True
        self.spinner.start()
        self.body.set_sensitive(False)
        self.import_button.set_sensitive(False)
        self.refresh_button.set_sensitive(False)
        def work():
            error = None
            try:
                operation()
            except VPNError as exc:
                error = str(exc)
            except Exception:
                error = 'The operation could not complete. Refresh and try again.'
            state = self.backend.status()
            GLib.idle_add(self.finish, state, error, message)
        self.worker.submit(work)

    def finish(self, state, error, message):
        self.busy = False
        self.spinner.stop()
        self.body.set_sensitive(True)
        self.import_button.set_sensitive(self.backend.authorized)
        self.refresh_button.set_sensitive(True)
        self.render(state)
        if error:
            dialog = Adw.MessageDialog(transient_for=self, heading='Could not complete request', body=error)
            dialog.add_response('close', 'Close')
            dialog.present()
        elif message:
            self.toast.add_toast(Adw.Toast(title=message))
        return GLib.SOURCE_REMOVE

    def refresh(self):
        self.run(lambda: None) if self.backend.authorized else self.run(self.backend.start)

    def render(self, state):
        self.state = state
        active = [p for p in state.profiles if p.active]
        authorized = self.backend.authorized
        conflict = (state.ts_active and (active or state.external)) or len(active) > 1
        if conflict:
            title, detail = 'Connections overlap', 'Disconnect a connection below to return to one VPN.'
        elif state.errors:
            title, detail = 'Status unavailable', 'Check the services below, then refresh.'
        elif state.external:
            title, detail = 'External WireGuard connection', ', '.join(state.external)
        elif state.ts_active:
            title, detail = 'Tailscale is on', state.address or 'Connected to your private network'
        elif active:
            title, detail = 'WireGuard is on', active[0].name
        else:
            title, detail = 'Ready to connect', 'Choose Tailscale or a WireGuard profile below.'
        self.title_label.set_label(title)
        self.detail.set_label(detail)
        warnings = list(state.errors)
        if state.external:
            warnings.append('Stop externally managed WireGuard before switching: ' + ', '.join(state.external))
        self.warning.set_label('\n'.join(warnings))
        self.warning.set_visible(bool(warnings))
        self.ts_row.set_subtitle(state.tailscale + (' · ' + state.address if state.ts_active and state.address else ''))
        self.ts_button.set_label('Disconnect' if state.ts_active else 'Connect')
        self.ts_button.set_sensitive(authorized and (state.ts_active or not (state.errors or state.external)))
        for row in self.rows:
            self.wg_group.remove(row)
        self.rows = []
        for profile in sorted(state.profiles, key=lambda p: (not p.active, p.name.lower())):
            row = Adw.ActionRow(title=GLib.markup_escape_text(profile.name),
                               subtitle='Connected' if profile.active else 'Ready to connect')
            row.add_prefix(Gtk.Image(icon_name='network-vpn-symbolic'))
            button = Gtk.Button(label='Disconnect' if profile.active else 'Connect', valign=Gtk.Align.CENTER)
            if profile.active:
                button.add_css_class('destructive-action')
            button.set_sensitive(authorized and (profile.active or not (state.errors or state.external)))
            button.connect('clicked', lambda _, key=profile.uuid: self.action(key))
            row.add_suffix(button)
            remove = Gtk.Button(icon_name='user-trash-symbolic', tooltip_text='Remove profile', valign=Gtk.Align.CENTER,
                                css_classes=['flat'])
            remove.set_sensitive(not profile.active)
            remove.connect('clicked', lambda _, p=profile: self.confirm_remove(p))
            row.add_suffix(remove)
            self.wg_group.add(row)
            self.rows.append(row)
        if not self.rows:
            row = Adw.ActionRow(title='No WireGuard profiles yet', subtitle='Use Import config to add your first connection.')
            self.wg_group.add(row)
            self.rows.append(row)

    def action(self, target):
        active = self.state.ts_active if target == 'tailscale' else any(p.uuid == target and p.active for p in self.state.profiles)
        self.run(lambda: self.backend.disconnect(target) if active else self.backend.switch(target),
                 'Disconnected' if active else 'Connection updated')

    def choose_file(self, _):
        chooser = Gtk.FileChooserNative(title='Import WireGuard configuration', transient_for=self,
                                       action=Gtk.FileChooserAction.OPEN, accept_label='Import', cancel_label='Cancel')
        filter_ = Gtk.FileFilter(name='WireGuard configuration (*.conf)')
        filter_.add_pattern('*.conf')
        chooser.add_filter(filter_)
        chooser.connect('response', self.file_chosen)
        chooser.show()
        self.chooser = chooser

    def file_chosen(self, chooser, response):
        if response == Gtk.ResponseType.ACCEPT:
            path = chooser.get_file().get_path()
            if path:
                self.run(lambda: self.backend.import_config(path), 'WireGuard profile imported')
        chooser.destroy()

    def confirm_remove(self, profile):
        dialog = Adw.MessageDialog(transient_for=self, heading='Remove this profile?',
                                  body=f'“{profile.name}” will be removed from NetworkManager. Your original config file will be kept.')
        dialog.add_response('cancel', 'Cancel')
        dialog.add_response('remove', 'Remove')
        dialog.set_response_appearance('remove', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response('cancel')
        dialog.set_close_response('cancel')
        dialog.connect('response', lambda _, response: self.run(lambda: self.backend.remove(profile.uuid), 'Profile removed')
                       if response == 'remove' else None)
        dialog.present()


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.soltros.VPNManager', flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        Gtk.Window.set_default_icon_name('io.github.soltros.VPNManager')
        window = self.get_active_window() or Window(self)
        self.session = window.backend
        window.present()

    def do_shutdown(self):
        if hasattr(self, "session"):
            self.session.close()
        Adw.Application.do_shutdown(self)


if __name__ == '__main__':
    sys.exit(App().run(sys.argv))
