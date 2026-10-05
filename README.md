# MALBOLGE — Episodic Anchuring

El ancla (`malbolge-anchuring`) llevada a su conclusión conceptual:

> **una ejecución Malbolge completa ≡ una transición atómica de la máquina
> superior.**

No decimos que una *instrucción* Malbolge sea una *instrucción* Brainfuck.
Decimos que una **época completa** de Malbolge es **una operación atómica** del
nivel de arriba. El ancla es la frontera del macroestado.

```
V0 (malbolge-anchuring)  V1 (episodic)                      V2 (primitivas)
  prog A                    ANCHOR                              E_+  = BF '+'
    → bytes                  →  computación Malbolge E₀          E_-  = BF '-'
    → hash/rebind            →  ANCHOR                           E_>  = BF '>'
    → prog B                 →  computación Malbolge E₁          E_.  = BF '.'
                             →  ANCHOR                           ...  cada primitiva
  (el anchor NO computa)     (macro-observador ve 0→1)           = una época Malbolge
```

## Índice

- [Los cuatro experimentos, ya ejecutados](#los-cuatro-experimentos-ya-ejecutados)
- [Esposas (heredadas de V0, no negociables)](#esposas-heredadas-de-v0-no-negociables)
- [Límites honestos](#límites-honestos)
- [Reproducir desde cero](#reproducir-desde-cero)
- [Tests](#tests)
- [Readout del estado propio (cascada mod59049)](#readout-del-estado-propio-cascada-mod59049)
- [Procedencia](#procedencia)
- [License](#license)

## Los cuatro experimentos, ya ejecutados

### V1 — la frontera (Classic, autocontenido)

`episodic.py` corre una cadena de épocas: cada una es un proceso Malbolge
**completo y fresco** (registros a cero, memoria reconstruida del texto), y la
única cosa que cruza la frontera son bytes sellados con SHA-256.

```
$ python3 episodic.py run
epoch0: fixtures/hello.mal status=HALTED steps=40 out=b'Hello World!'
epoch1: fixtures/echo12.mal status=HALTED steps=25 out=b'Hello World!'
epoch2: fixtures/echo12.mal status=HALTED steps=25 out=b'Hello World!'

$ python3 episodic.py macro-trace fixtures/episodic_demo.json
macro trace: 0 -> 1 -> 2 -> 3

$ python3 episodic.py verify fixtures/episodic_demo.json
replay OK: 3 epochs, all seals verified, deterministic

$ python3 episodic.py tamper-demo fixtures/episodic_demo.json
1-bit tampered epoch output -> REJECTED
```

V1 establece la FRONTERA y el SELLO. Las épocas de V1 *re-cometen* bytes (echo);
establecen que una computación Malbolge completa es un paso macroscópico válido,
pero todavía no *computan* la transición.

### V2 — la época computa (Malbolge Free)

`v2.py` + `epochtool.zig` suben la resolución: una máquina-registro de un
registro con dos operaciones, `+` (r←r+1 mod 256) y `-` (r←r−1 mod 256), donde
**cada operación es una época Malbolge completa** que lee el byte de registro
por stdin y escribe el nuevo byte por stdout.

Los programas-época se compilan del backend semántico de Malfuck (vendored en
`vendor/malfuck/`, regla copy-not-integrate): `.[,+.].` → `plus.mal` y
`.[,-.].` → `minus.mal`.

```
$ python3 v2.py compile
$ python3 v2.py run "+++-"
program '+++-' -> register 0x30 -> 0x32

$ python3 v2.py macro-trace fixtures/v2_demo.json
ops:      +  +  +  -
register: 0x30 -> 0x31 -> 0x32 -> 0x33 -> 0x32
  epoch 0: +  0x30 -> 0x31  status=HALTED steps=12 sha=6b86b273…
  epoch 1: +  0x31 -> 0x32  status=HALTED steps=12 sha=d4735e3a…
  epoch 2: +  0x32 -> 0x33  status=HALTED steps=12 sha=4e074085…
  epoch 3: -  0x33 -> 0x32  status=HALTED steps=12 sha=d4735e3a…

$ python3 v2.py verify fixtures/v2_demo.json
replay OK: 4 epochs, all seals verified

$ python3 v2.py tamper-demo fixtures/v2_demo.json
tampered epoch output -> REJECTS (seal mismatch)
```

Los sellos son los SHA-256 literales de los bytes de salida
(`sha256("\x31") = 6b86b273…`, `sha256("\x32") = d4735e3a…`). Cada `+`/`-` es
una computación Malbolge Free completa (12 steps, HALTED) que transforma su
entrada; el macroestado (el registro) solo avanza cuando el sello del output
coincide.

### V3 — las 8 primitivas (Brainfuck como máquina de épocas)

`primitives.py` es un intérprete Brainfuck donde **cada una de las 8
instrucciones despacha exactamente una época Malbolge**:

| op | época (transformer) | semántica |
|---|---|---|
| `+` | `plus.mal` (increment) | `cell ← cell+1` — aritmética real |
| `-` | `minus.mal` (decrement) | `cell ← cell-1` |
| `>` | `plus.mal` (increment) | `ptr ← ptr+1` — el epoch computa el puntero |
| `<` | `minus.mal` (decrement) | `ptr ← ptr-1` |
| `.` | `echo1.mal` (echo) | testigo sellado; el driver emite el byte |
| `,` | `echo1.mal` (echo) | testigo sellado; el driver guarda en `cell` |
| `[` | `echo1.mal` (echo) | peek sellado; si cero, salto (control macro) |
| `]` | `echo1.mal` (echo) | peek sellado; si no-cero, salto atrás |

```
$ python3 primitives.py run fixtures/three.bf --out fixtures/three.json
4 epochs, output=0x03 final_ptr=0

$ python3 primitives.py run fixtures/cat.bf fixtures/cat.in --out fixtures/cat.json
11 epochs, output=0x414243 final_ptr=0      # "ABC", echo con loop

$ python3 primitives.py verify fixtures/cat.json
replay OK: 11 epochs, all seals verified

$ python3 primitives.py tamper-demo fixtures/cat.json
tampered epoch output -> REJECTS (seal mismatch)
```

`,[.,]` con entrada `ABC` corre como **11 épocas**: cada `,` `.` `[` `]` es una
computación Malbolge completa, y el loop retorna a través del anchor. El
resultado es byte-idéntico al intérprete Brainfuck canónico.

### V4 — estado completo en la frontera

`v4.py` transporta `[ptr][cell0..cell7]` como un payload completo de 9 bytes.
La época lee y vuelve a emitir los nueve bytes, incrementando el byte 1. Tres
épocas producen `000000000000000000 -> 000100000000000000 ->
000200000000000000 -> 000300000000000000`. Cada entrada y salida tiene SHA-256;
replay y tamper gate pasan. El primer diseño con cursor interno largo falló la
conservación del payload y se conserva en `evidence/v4_fullstate_probe.txt`.
Esto demuestra transporte completo + transformación de slot seleccionado, no
indexado dinámico arbitrario por el puntero.

`dynamic_epoch.py` cierra la selección dinámica acotada: usa el payload de 17
bytes `[ptr][flag0,cell0]...[flag7,cell7]`. El puntero escalar persiste y los
flags one-hot son workspace consumible; la época Malbolge suma cada flag a su
celda correspondiente. Los ocho valores de `ptr` pasan, con replay y tamper.
La evidencia está en `evidence/dynamic_pointer_probe.txt`. Esto no reclama una
cinta sin cota.

## Esposas (heredadas de V0, no negociables)

- NO process resumption — cada época arranca fresca.
- NO serialized mid-execution machine state.
- NO Turing-completeness claim.
- Solo output bytes cruzan la frontera.
- El ancla vela por integridad, no computa semántica.

## Límites honestos

| Claim | Estado |
|---|---|
| V1: cadena de computaciones Malbolge completas sella la frontera (Classic) | **DEMONSTRATED** |
| V2: `E_+` y `E_-` computan la transición atómica (Malbolge Free) | **DEMONSTRATED** |
| V3: 8 primitivas Brainfuck como épocas (máquina BF de épocas) | **DEMONSTRATED** |
| V4: payload completo `ptr+8 celdas` cruza cada época sellada | **DEMONSTRATED** |
| V4: selección dinámica `cells[ptr]` para 8 celdas | **DEMONSTRATED** |
| Cinta completa con indexado dinámico sin cota | **NOT_IMPLEMENTED** |
| Malbolge Classic aritmético (sin TAPE_BASE) | **NOT_IMPLEMENTED** |
| Turing-completeness nueva | **NOT_DEMONSTRATED** |

Arquitectura V3 (dicha recta): el driver posee la cinta + puntero + pc; cada
época transforma **un byte seleccionado** (el operando de la primitiva), no la
cinta completa. Las primitivas de valor (`+ - > <`) son aritméticas reales; las
de I/O y salto (`. , [ ]`) son épocas-testigo selladas. Nada de esto es un
device de completitud; es la frontera macro expandida a las 8 primitivas.

## Reproducir desde cero

```bash
# V1 (solo Python 3)
python3 episodic.py run
python3 episodic.py verify fixtures/episodic_demo.json
python3 episodic.py tamper-demo fixtures/episodic_demo.json

# Binarios nativos (zig 0.16: del sistema o `pip install ziglang==0.16.0`)
python3 build_native.py      # -> ./epoch y ./intermediate_vm_runner

# V2
python3 v2.py compile
python3 v2.py run "+++-"
python3 v2.py verify fixtures/v2_demo.json
python3 v2.py tamper-demo fixtures/v2_demo.json

# V3 (primitivas; necesita ./epoch ya compilado)
./epoch compile echo.bf fixtures/echo1.mal
python3 primitives.py run fixtures/three.bf --out fixtures/three.json
python3 primitives.py run fixtures/cat.bf fixtures/cat.in --out fixtures/cat.json
python3 primitives.py verify fixtures/cat.json
python3 primitives.py tamper-demo fixtures/cat.json

# V4 (estado completo; necesita ./epoch)
python3 v4.py compile
python3 v4.py run
python3 v4.py verify
python3 v4.py tamper-demo

# V4 selección dinámica bounded (8 celdas)
python3 dynamic_epoch.py compile
python3 dynamic_epoch.py run
python3 dynamic_epoch.py verify
python3 dynamic_epoch.py tamper-demo

# Encoder manual de Malbolge Classic
python3 classic_encoder.py 68 17
python3 classic_encoder.py 68 17 --c-range 3 9
python3 classic_encoder.py 68 17 --table
python3 -m unittest test_classic_encoder.py -v
```

`classic_encoder.py` solo invierte la ecuación `r=(opcode-c) mod 94` y
normaliza al ASCII imprimible `33..126`. No simula todavía `c`, `d`, `crazy`,
rotación ni la mutación posterior de memoria; esos son pasos separados del
ensamblado Classic completo.

El reto ejecutable está en `classic_challenge.py`: genera, sin hardcodear la
cadena, `in -> out -> rot -> movd -> opr -> nop -> end`. Con entrada `Z`, el
programa generado `ub%%:?K` termina en 7 pasos y devuelve `Z`. Evidencia:
`fixtures/classic_challenge.json`.

`classic_codec.py` completa la inversa estática: ensambla opcodes a caracteres
y desensambla caracteres a opcodes usando su posición real. `parity` comprueba
exhaustivamente las 8 instrucciones en las 59 049 posiciones (472 392 pares).
También reconstruye `ub%%:?K` byte por byte y comprueba igual ejecución. Esto
es paridad del codec posicional; saltos y automodificación durante la ejecución
necesitan un decompilador de trazas separado.

```bash
python3 classic_codec.py assemble "in,out,rot,movd,opr,nop,end"
python3 classic_codec.py disassemble "ub%%:?K"
python3 classic_codec.py parity
python3 -m unittest test_classic_codec.py -v
```

### MBIR Classic — descenso bottom-up

`mbir_classic.py` es el primer IR ejecutable orientado directamente a Classic:
su plan son los ocho opcodes decodificados, y el lowering aplica la inversa
posicional `r=(opcode-c) mod 94`. No compara contra una máquina superior ni
pretende que Brainfuck sea el backend. El plan `in,out,rot,movd,opr,nop,end`
produce `ub%%:?K` y la máquina Classic devuelve `Z` en 7 pasos.

```bash
python3 mbir_classic.py assemble "in,out,rot,movd,opr,nop,end"
python3 mbir_classic.py run "in,out,rot,movd,opr,nop,end" --input Z
python3 -m unittest test_mbir_classic.py -v
```

El alcance actual es intencionalmente estrecho: el IR ya baja a la máquina
`a/c/d + memoria` de `malbolge.py`, pero todavía no es un ensamblador simbólico
de saltos ni un decompilador de la memoria automodificada.

### PITON ↔ Malbolge

`piton_malbolge_mirror.py` compara un runtime mínimo de streams: el programa
PITON `fixtures/piton_mirror.piton` y un Classic ensamblado como `[IN,OUT] × N
+ END` reciben exactamente los mismos bytes. Pasan tamaños 0, 1, 5, 7 y 256;
el último contiene todos los valores `00..ff`. En dirección inversa, Pibolge
(el intérprete Malbolge escrito en PITON) ejecuta `classic_challenge.mal` en 7
pasos y produce `Z`. Evidencia: `evidence/piton_malbolge_mirror.txt`.

```bash
python3 piton_malbolge_mirror.py
python3 -m unittest test_piton_malbolge_mirror.py -v
```

El alcance es un espejo byte-stream acotado, no toda la semántica CPython/PITON
implementada dentro de Malbolge.

El mismo `classic_challenge.mal` también pasó en Swiftbolge, Rustbolge,
Javolge, Cobolge, Fortranbolge y Wasmbolge: los seis reportaron `Z`, 7 pasos y
`a=9856,c=6,d=40`. La evidencia completa está en
`evidence/six_bolge_challenge.txt`.

Finalmente, el runtime real de MalbolgeLISP 3^19 ejecutó `(+ 1 2)` sobre la
imagen completa de 371,331,415 bytes y devolvió `3`, terminando tras
2,401,426,208 pasos. Eso confirma el probe del backend Lisp. No se mezcla con
Classic 3^10: un frontend común puede dirigir expresiones a ambos backends,
pero debe conservar explícita la diferencia de modelo. Evidencia:
`evidence/malbolge_lisp_probe.txt`.

También probamos el cat canónico publicado por `malbolge.org` (9503 bytes,
SHA-256 `CE04A6F2...A7224A52`) con entrada `MEOW` y límite de 10 000 pasos.
Los seis runtimes coincidieron en `a=9477,c=9183,d=58963`, `output_len=2` y
salida `ME`; el programa es no terminante por diseño. Evidencia:
`evidence/malbolge_org_cat_probe.txt`.

### Unshackled 3^19

`unshackled_codec.py` aplica la misma inversión modular, añadiendo el offset
de la región `c // 3^18` usado por `bolge19`. El round-trip pasa en las tres
regiones y en sus fronteras. El mismo juguete `[IN, OUT, END]` genera `ubO` y
el runtime 3^19 real lo ejecuta con entrada `Z`, produciendo `Z` y terminando
en 2 pasos. Evidencia: `evidence/unshackled_codec_probe.txt`.

### Escalera epochal E10 → E19

`dimension_epoch_ladder.py` construye una familia paramétrica experimental:
memoria `3^k`, wrap de `c/d` en `3^k` y el mismo `ubO` en cada dimensión. El
byte `Z` cruza sellado por E10, E11, ..., E19; replay y tamper pasan. Esto
demuestra la escalera de transporte para el juguete, no equivalencia completa
de `crazy`, rotación o automodificación en los anchos intermedios. Evidencia:
`evidence/dimension_epoch_ladder.txt`.

### MBIR-2L: Befunge + WebAssembly

El perfil `MBIR-2L` vive en `MBIR_2L_CONTRACT.md`. `mbir_2l.py` ejecuta una
VM local de bytecode; `befunge_mbir.py` baja el subconjunto determinista 2D de
Befunge y `wasm_mbir.py` baja expresiones binarias Wasm MVP restringidas. Ambos
frontends producen el mismo resultado MBIR para el fixture aritmético común.

```bash
python3 -m unittest test_mbir_2l.py test_befunge_mbir.py test_wasm_mbir.py test_mbir_2l_parity.py -v
python3 parity_mbir_2l.py
```

Probe actual: Befunge `23+,@` y Wasm `i32.const 2; i32.const 3; i32.add`
convergen a `output_bytes=[5]` y `status=HALTED`; los pasos son 9 y 5
respectivamente porque Befunge baja saltos explicitos. Esto es paridad del
perfil y del fixture, no equivalencia total entre los lenguajes.

El backend opcional `mbir_classic_backend.py` ya baja la frontera demostrada
`IN_BYTE, OUT_BYTE, HALT` a Classic `ubO`; con entrada `Z` termina en 3 pasos
y devuelve `Z`. Aritmetica y control MBIR sin una reduccion Classic demostrada
se rechazan explicitamente, no se simulan.

### Malbolge con etiquetas v0 (`labeled_asm.py`)

Opcodes legibles con etiquetas (`in`, `out`, `nop`, `end`, `goto L`, `call L`,
`ret`) compilados a Classic. El compilador coloca cada `jmp` para que la celda
que lee `d` contenga la dirección de aterrizaje. Sus libertades son cuántos `nop`
ejecutados insertar antes del salto y cuál de los 8 bytes válidos poner en una celda
de dato libre. Usa búsqueda con backtracking. Guía paso a paso: `GUIA_ETIQUETAS.md`.

```bash
python3 labeled_asm.py compile examples_labeled/call_return.mlab
python3 labeled_asm.py explain examples_labeled/call_return.mlab
python3 labeled_asm.py verify  examples_labeled/call_return.mlab
python3 -m unittest test_labeled_asm -v
```

`verify` exige, con 5 entradas distintas:

- **oráculo:** `malbolge.run` termina y su salida es igual a la semántica de referencia
  del programa etiquetado;
- **traza:** las celdas ejecutadas son exactamente el camino planeado;
- **Zig:** el runner da el mismo estado, los mismos pasos y la misma salida;
- **mutación:** cualquier otro byte válido en una celda de dato cambia el camino.

Suite: 9 tests; el fuzz compila y verifica 60 programas aleatorios de 60.

Límites de v0 (se rechazan con explicación):

- **Sin bucles en v0.** Ningún enunciado puede ejecutarse dos veces, porque v0 solo
  acomoda bytes en carga. Los bucles ya están resueltos en HeLL/LMAO de Lutter
  (ciclos xlat2 y `RNop`, que existe en 94/94 posiciones pero solo 14/752 veces
  pasa la carga, así que requiere inicialización en ejecución) y en `malbolge-free`
  (lmao-lite, JZ/JNZ demostrados).
- **Sin `rot`, `opr` ni `movd`.**
- **Destinos de salto hasta la celda 127.**
- **Camino fijo.** Sin condicionales, el camino no depende de la entrada: los saltos
  cambian el acomodo, no lo que el programa puede calcular.

## Tests

```bash
pip install -r requirements-dev.txt   # zig 0.16 si no lo tienes instalado
python3 build_native.py                 # opcional: sin ./epoch los tests V2-V4 se saltan
python3 -m unittest discover -v
```

Los tests que necesitan `./epoch` se marcan `skipped` si el binario no existe;
`test_piton_malbolge_mirror.py` se salta si `piton` no está en el `PATH`. Las
rutas de los binarios se pueden forzar con `MALBOLGE_EPOCH` y
`MALBOLGE_VM_RUNNER`. CI (`.github/workflows/tests.yml`) compila los binarios con
zig 0.16 y corre la suite completa en Linux.

## Readout del estado propio (cascada mod59049)

`mod59049_readout_gen.py` genera programas HeLL/LMAO con 5 celdas de cascada
(N1..N5) y celdas de parada, de modo que tras `T` ticks (producto de las
longitudes de parada; ciclos xlat válidos: 2, 4, 5, 6, 9) un readout imprime
los 5 dígitos base-9 del **estado de la cascada, leído desde dentro del
mismo programa Malbolge** — no desde un host. Cada dígito lo produce una
cadena de lectura mid-wrap (una llamada por posición, un wrap, y los bloques
`a_kk` imprimen y transfieren). La verificación es doble: oráculo `malbolge.py`
y segundo intérprete (`intermediate_vm_runner.zig`, compilado natively).

| Claim | Estado |
|---|---|
| Readout integrado mod59049 (barrido 12/12 + potencias de 9 hasta 59049) | **DEMONSTRATED** |
| Segundo intérprete (6/6 coincidencia en salida y pasos) | **DEMONSTRATED** |
| Readout **no destructivo**: restauración estática (T=10, 5/5 celdas; generalidad T=5, 6, 9, 10, 12, 90 con paradas de 2 y 3 celdas) | **DEMONSTRATED** |
| Lectura repetida sin reparación (relectura dentro del programa) | **DEMONSTRATED** |
| `p=1` (orden de tick por programa) y dígito de posición 3 (T=12) | **DEMONSTRATED** |
| LMAO valida etiquetas en compilación; presupuesto de espacio libre (~130 instr. avisa, ~165 falla) | **DEMONSTRATED** |
| El readout simple es destructivo: consume 1 posición por celda; reparar exige conocer la posición (circular) | **DEMONSTRATED** |
| `OFFSET_ORIGIN`: el offset crudo es función de la estructura de la cascada de paradas — `(+1,−1,0,0,0)` en dígitos para paradas estándar; `−8` en la celda 1 si hay parada de 9; se reparte con muchas paradas; independiente de T y del orden | **CARACTERIZADO** |
| Lectura incremental (leer tick a tick pasando por el bucle) | **NOT_DEMONSTRATED** (límite fundamental) |

Mecanismo (trazado sobre el `.mb` compilado):

- `OUT` imprime el valor de una **celda de datos** (`a%256`, fijado por el
  `ROT` anterior), no un literal del bloque: el dígito es un valor calibrado
  de la celda espejo, y la calibración (`pre`/`shift` por cadena) compensa la
  fase de la cascada.
- El readout simple consume 1 posición por celda leída; añadir en cada bloque
  `a_kk` las `9−kk` llamadas de restauración (constante de ese bloque) lo hace
  no destructivo — acotado por el presupuesto de espacio libre de LMAO.
- La lectura incremental falla porque la cascada es **flujo de control de un
  solo uso**: en la segunda pasada su código ya está auto-cifrado (trazo:
  pasada 1 = 55 `jmp`/8 `movd`; pasada 2 = sopa de ~50 ops distintos).
  Refutadas por medición: "anclar `d` con `movd`" (lo roto es el flujo de
  código, no la alineación de datos) y "K copias frescas del readout" (la
  cascada no puede llegar a ninguna copia).

Límites honestos:

- **Lectura incremental:** para leerla K veces haría falta una cascada de
  K pasadas (layout de flujo de control estable para K×T ejecuciones), que es
  una tarea de layout de LMAO, no de generador.
- **Offset:** caracterizado empíricamente; no hay fórmula primera-principios
  sin el layout completo de LMAO.

Evidencia: manifiesto append-only `evidence/readout_chain9_hashes.json`
(223 archivos, SHA-256 por artifact) y los directorios por experimento:
`evidence/mod59049_readout/` (barrido 12/12), `evidence/second_interpreter/`
(6/6), `evidence/nondestructivo/` (consumo, reparación, generalidad),
`evidence/destructivity/` (medición de destructividad con control absoluto),
`evidence/lectura_incremental/` (trazos ROT→OUT, refutaciones, offsets).

## Procedencia

`malbolge.py`, `gen_echo.py` y las fixtures echo/hello son copia del anchor V0
(`malbolge-anchuring`). `vendor/malfuck/` es copia del backend semántico de
`Malfuck` (a su vez derivado de `malbolge-free` y `Malbolge-Translator`). Todo
copiado, nada enlazado: este repo es autocontenido.

## License

MIT
