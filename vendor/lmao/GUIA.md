# GUIA: LMAO Classic en MALBOLGE

LMAO (Low-level Malbolge Assembler, Ooh!) de Matthias Lutter — ensamblador
**Classic** (10 trits, 59049 celdas). Esta copia vive en `vendor/lmao/`.
NO es LMFAO: aquel es Unshackled y vive en `MALDOOM/vendor/LMFAO`.

## 1. El comando que viniste a buscar

```sh
cd "…/MALBOLGE/vendor/lmao"
./bin/lmao -o /tmp/adder.mb example_adder.hell
```

Salida real:

```
This is LMAO v0.6.0 (Low-level Malbolge Assembler, Ooh!) by Matthias Lutter.
Malbolge code written to /tmp/adder.mb
```

Y para correrlo:

```sh
printf '999 2\n' | python3 -c "
import sys; sys.path.insert(0, '../..')
import malbolge
print(malbolge.run(open('/tmp/adder.mb').read(), sys.stdin.buffer.read(), 20_000_000))"
```

Salida real:

```
('HALTED', 253280, b'1001\n')
```

## 2. Regla de oro

La salida de LMAO **no es byte-reproducible**: `initialize.c` rellena las
celdas no usadas con `rand() % 8` y `main.c` hace `srand(time(NULL))`. Dos
builds del mismo `.hell` difieren en ~389 bytes y ambos corren igual. En
evidencia, registra el SHA-256 del `.mb` **de esa** ejecución, nunca un hash
"esperado".

## 3. Comandos, uno a uno

### 3.1 Compilar LMAO (solo la primera vez; no necesita flex/bison)

```sh
cd vendor/lmao
gcc -O3 -I bin -I src -c bin/lmao.tab.c -o bin/bison.o
gcc -O3 -I bin -I src -c bin/lex.yy.c  -o bin/lex.o
for f in globals xlat label layout prefix debug cli main malbolge initialize gen_init; do
  gcc -O3 -I bin -I src -c src/$f.c -o bin/$f.o
done
gcc bin/*.o -o bin/lmao
```

Salida real: `bin/lmao` existe, sha256
`5a6039efd995af1cf57b9bf4d6ec70da3a5303efe0ec6a1fe0fad3abc03f3f44`.

### 3.2 Sumar con el ejemplo incluido

```
printf '123 456\n' | …   → 579
printf '999 2\n'   | …   → 1001
```

Verificado idéntico en `malbolge.py`, Malbolge-Engine y MalboGost (estos dos
últimos vía wine; su salida viene con CRLF, normaliza quitando `\r`).

### 3.3 Incrementar (ADD1) con el sumador

Entrada `N 1` = `N+1`. Medido en oracle: 19/19
(0..9, 41, 99, 100, 123, 255, 500, 997, 998, 999). Acarreos:
`9 1 → 10`, `99 1 → 100`, `999 1 → 1000`.

### 3.4 Ejemplos escritos a mano

```sh
./bin/lmao -o /tmp/c5.mb handwritten/counter5.hell
./bin/lmao -o /tmp/cc.mb handwritten/carry_5x2.hell
./bin/lmao -o /tmp/h.mb  handwritten/print_h.hell
```

Salidas reales (oracle):

| programa | salida | pasos |
|---|---|---|
| `counter5.hell` | `....W` | 3906 |
| `carry_5x2.hell` | `5X` | 3370 |
| `print_h.hell` | `H` | 1833 |
| `nine_cycle.hell` | `TTTTTTTTB` | 3746 |
| `mod59049.hell` | `Z` (tras 59049 iteraciones exactas) | 314258 |
| `levels_markers.hell` | 6560 `T` + `Z` (un marcador por wrap de N1) | 354721 |

`counter5` avanza un ciclo de 5 en cada llamada e imprime `W` cuando el ciclo
envuelve. `carry_5x2` añade un segundo ciclo de 2 que avanza solo cuando el de
5 envuelve: `5` en el primer acarreo, `X` en el segundo. Esa es la mecánica del
acarreo que el sumador usa por dígito decimal.

## 4. Cómo leer la salida

| Salida | Significado | Acción |
|---|---|---|
| `Malbolge code written to …` | compiló | seguir |
| `Error: Cannot find label X` | falta la celda X en `.CODE` | declararla |
| `Error: Forced xlat cycle doesn't exist` | ciclo imposible en esa posición | cambiar la secuencia de ciclos |
| `Error: syntax error, unexpected invalid token` | etiqueta con nombre de comando (`Nop:`), no permitido | renombrar la etiqueta |
| `HALTED` en el oráculo | corrió hasta `v` | listo |
| `OUT_OF_FUEL` | se agotaron los pasos | subir `max_steps` |

## 5. Trampas

1. **Bloques sin línea en blanco.** Dos etiquetas seguidas sin línea vacía se
   parsean como un solo bloque y los ciclos xlat2 no cuadran. Separa cada
   bloque `.CODE` con una línea en blanco.
2. **`ROT 'H'` no carga `H`.** `ROT` rota el valor de la celda; para obtener
   `H` (72) hay que rotar `216` (`rot(216)==72`). Los ejemplos del repo usan
   `'H'<<1` que LMAO evalúa en ensamblado.
3. **`R_` no es una etiqueta.** Es "restaurar": `R_LABEL = LABEL + 1`. Sirve
   para devolver una celda a su comando activo tras el cifrado.
4. **No confundir con LMFAO.** `LMFAO` (Unshackled) está en
   `MALDOOM/vendor/LMFAO` y **no** produce Classic.
5. **La referencia se decrementa sola.** LMAO resta 1 a cada referencia
   (por el `d++` posterior a la instrucción); no lo "arregles" a mano.
6. **Alimentar `bolge.exe` (Zig) exige quitar los blancos.** El `.mb` de LMAO
   puede traer saltos de línea; `malbolge.py`, MalboGost y Malbolge-Engine los
   filtran, pero el empaquetado BOLG1 los mete como celdas y el VM Zig corta
   con `input_underflow` en el paso 4256. Pasa el programa sin `\n`:
   `"".join(ch for ch in raw if ch not in "\n\r\t ")`. Verificado: con el
   filtro, `mod59049.mb` da `Z` en 314258 pasos, idéntico al oráculo.
