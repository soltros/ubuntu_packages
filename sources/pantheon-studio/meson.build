project('pantheon-studio', 'vala', version: '0.2.0')
deps = [dependency('gtk4'), dependency('granite-7'), dependency('gio-unix-2.0'), dependency('gee-0.8')]
executable('pantheon-studio', 'src/application.vala', 'src/store.vala', 'src/preferences.vala', 'src/customize.vala', dependencies: deps, install: true)
test('overrides', executable('test-overrides', 'src/test-store.vala', 'src/store.vala', dependencies: deps))
install_data('data/io.github.soltros.PantheonStudio.desktop', install_dir: get_option('datadir') / 'applications')
test('preferences', executable('test-preferences', 'src/test-preferences.vala', 'src/preferences.vala', dependencies: deps))
ui_test = executable('test-ui', 'src/test-ui.vala', 'src/customize.vala', 'src/preferences.vala', dependencies: deps)
test('interface', find_program('xvfb-run'), args: ['-a', ui_test], env: ['GSK_RENDERER=cairo', 'GTK_A11Y=none'])
