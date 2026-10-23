#!/bin/bash
# Rebuilds docs/convimg.wasm from the open-source convimg (BSD). Run on Linux/Mac with clang + lld + wasi-libc:
#   Ubuntu/Debian: sudo apt install clang lld wasi-libc libclang-rt-dev-wasm32 make git
# To upgrade convimg, change TAG. (Tags newer than v9.3 may need extra WASI shims.)
set -e
TAG="${TAG:-v9.3}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d)"; cd "$W"
git clone --depth 1 --branch "$TAG" --recurse-submodules --shallow-submodules https://github.com/mateoconlechuga/convimg.git c
cd c
mkdir -p wasm/shim
# zx0 only uses setjmp for out-of-memory handling; WebAssembly has no setjmp, so stub it.
printf '#include <stdlib.h>\ntypedef int jmp_buf[1];\n#define setjmp(x) 0\n#define longjmp(x,v) abort()\n' > wasm/shim/setjmp.h
SRCS=$(make -pn 2>/dev/null | grep -E "^SOURCES :?=" | head -1 | sed 's/^SOURCES :\?= //' | tr ' ' '\n' | grep -E "\.c$" | sed 's|\$(SRCDIR)|src|;s|\$(DEPDIR)|src/deps|')
FL="--target=wasm32-wasi -isystem /usr/include/wasm32-wasi -O2 -DNDEBUG -DLOG_BUILD_LEVEL=3 -std=gnu11 -w -D_WASI_EMULATED_PROCESS_CLOCKS -DPRGM_NAME=\"convimg\" -DVERSION_STRING=\"$TAG\" -DYAML_VERSION_MAJOR=1 -DYAML_VERSION_MINOR=0 -DYAML_VERSION_PATCH=0 -DYAML_VERSION_STRING=\"1.0.0\""
INC="-Isrc -Isrc/deps/libyaml/include -Isrc/deps -Isrc/deps/libimagequant"
for s in $SRCS; do clang $FL -Iwasm/shim $INC -c "$s" -o "wasm/$(echo "$s" | tr '/' '_').o"; done
clang --target=wasm32-wasi -L/usr/lib/wasm32-wasi -fuse-ld=lld -Wl,--stack-first -Wl,-z,stack-size=8388608 \
  -Wl,--initial-memory=67108864 -Wl,--max-memory=1073741824 -Wl,--export-memory wasm/*.o -lc \
  -lwasi-emulated-process-clocks /usr/lib/wasm32-wasi/libc.a -o "$ROOT/docs/convimg.wasm"
echo "Built docs/convimg.wasm ($TAG)"
