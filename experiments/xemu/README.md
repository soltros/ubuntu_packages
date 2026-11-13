# XEMU (Optimizations)

`xemu-perf` is a native Ubuntu 26.10 amd64 package installed beside stable `xemu`.
Its application-menu name is **XEMU (Optimizations)**. After the independent build
and signed repository publication succeed:

```bash
sudo apt update
sudo apt install xemu-perf
```

The package backports upstream [PR #2993](https://github.com/xemu-project/xemu/pull/2993)
(pinned to `98ab977bb75b9c54ceabda870bfc78232731574a`) onto the same 0.8.139
source revision used by stable xemu. The only backport adaptation is retaining
that version's renderer argument to `pgraph_vk_compile_glsl_to_spv`.
The upstream author's patch provides persistent Vulkan driver pipeline and SPIR-V
caches with atomic writes and corruption handling. It targets repeat-run shader
compilation hitches, not sustained emulation speed. The first encounter can still
stutter. Quit normally to save caches, then repeat the same scene.

The launcher uses Vulkan by default and enables the existing disk-cache setting.
It copies the native installation's configuration and EEPROM once into
`~/.local/share/xemu-perf/xemu/xemu/` (under `XDG_DATA_HOME` if customized).
Settings and caches are isolated from stable xemu. Firmware paths, game images,
and HDD paths referenced by that copied configuration still refer to the same
files. **Do not run both emulators against the same virtual HDD concurrently.**
Portable/AppImage/Flatpak installations may store their config elsewhere; configure
firmware and disk paths in the experimental app if no native configuration exists.

## Compare audio processing on the Ryzen 5600X desktop

Close the emulator between tests and use the same scene, resolution scale,
renderer, VSync, display refresh rate, and guest FPS display. Change one option at
a time. These are experiments, not measured improvements on this machine.

```bash
xemu-perf                          # Cache patch; preserves existing DSP/worker settings
xemu-perf --workers 4              # Compare fewer voice threads with upstream auto
xemu-perf --workers 0              # Restore upstream auto worker selection
xemu-perf --dsp-jit                # Test the existing upstream DSP JIT
xemu-perf --interpreter            # Return to upstream's default DSP interpreter
xemu-perf --baseline               # Stable binary, same experimental profile/settings
xemu-perf --no-disk-cache          # Disable persistent shader caches
xemu-perf --renderer OPENGL        # Compare the other graphics backend
```

Worker and DSP selections persist in the experimental profile. The default launch
selects Vulkan and disk caching each time. DSP JIT is opt-in because its accuracy
needs game testing. This does not import unfinished DSP PR #3047, skip guest work,
overclock the guest CPU, increase Xbox RAM, or disable GPU synchronization.
A shader-cache improvement does not fix every source of FPS drops or audio glitches.

## Build and publish

`Build optimized xemu` compiles only this package in an Ubuntu 26.10 container,
checks the DEB, verifies native ELF payload and APT dependency resolution, then
uploads `debs-stonking-xemu-perf`. `Publish signed APT repository` accepts that
workflow's successful main-branch artifacts, overlays only `xemu-perf`, and signs
the existing `apt-stonking` index. Both publication paths share `apt-publish`
concurrency. Full matrix publication preserves independently built `xemu-perf`;
experimental publication preserves the other packages and refuses downgrades.

Experimental files do not match the full build's source paths. Workflow-only
changes run validation but skip the full matrix; explicit workflow dispatch can
still rebuild everything. No version pin is added to the full matrix.

`package.json` pins the source, patch provenance, hash, and DEB version. Increment
the experimental Debian revision when changing the patch. A changed stable source
revision requires reviewing/rebasing the patch rather than silently applying it.
The dedicated daily checker assigns an update issue to `soltros` when the stable
base or upstream cache PR changes.

No gameplay or hardware performance claims are made by a passing CI build.
Test affected games before choosing this over stable xemu.
