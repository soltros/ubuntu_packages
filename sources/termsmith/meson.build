project(
  'termsmith',
  'vala',
  version: '0.2.0',
  meson_version: '>= 0.59.0',
)

gnome = import('gnome')

executable(
  'termsmith',
  'src/application.vala',
  dependencies: [
    dependency('gtk4'),
    dependency('granite-7'),
    dependency('gee-0.8'),
  ],
  install: true,
)

install_data(
  'data/io.github.derrik.Termsmith.desktop',
  install_dir: get_option('datadir') / 'applications',
)

install_data(
  'data/io.github.derrik.Termsmith.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo',
)

install_data(
  'data/io.github.derrik.Termsmith.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps',
)
