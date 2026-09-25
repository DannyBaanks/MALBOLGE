# Guía: Malbolge con etiquetas v0

Escribes opcodes legibles con etiquetas y `labeled_asm.py` produce Malbolge Classic
real, lo corre y demuestra que hace lo que escribiste. Toda la salida de esta guía es
real, ejecutada el 2026-09-13.

Calcbolge sigue siendo la herramienta para **aprender** a mano: qué carácter va en
qué celda, órbitas de cifrado, rampas. Este compilador es el **motor**.

## 1. Escribe un programa

`examples_labeled/call_return.mlab`:

```
main:   in          # read first byte
        out         # print it
        call sub
        out         # print what sub left in A
        end
sub:    in          # read second byte
        out
        ret
```

Instrucciones de v0: `in`, `out`, `nop`, `end`, `goto ETIQUETA`,
`call ETIQUETA`, `ret`. El texto después de `#` es comentario.

## 2. Compílalo

```bash
cd "C:\Development\ISyCo Git\MALBOLGE"
python3 labeled_asm.py compile examples_labeled/call_return.mlab
```

```
ub`A@">=<;:9876543210/.-,+*)('&%$#"@-}|{zyxwvutsrqponmlkjihgfedcba`_^]\[ZYXWVUTSRQPONMLKJIHGFEDCBr_]
```

Con `-o salida.mal` además lo guarda en un archivo.

## 3. Mira por qué quedó así

```bash
python3 labeled_asm.py explain examples_labeled/call_return.mlab
```

Filas relevantes; el resto son `nop` de relleno que nunca se ejecutan ni se leen:

```
 cell  char  op    step  role
    0  'u'   in       1  in (line 2)
    1  'b'   out      2  out (line 3)
    2  '`'   jmp      3  jmp: call sub (line 4)
    5  '"'   rot         data: landing 34 for ret (line 9)
   34  '"'   nop         landing of ret (line 9) (encrypted, never run)
   35  '@'   out      7  out (line 5)
   36  '-'   end      8  end (line 6)
   96  'B'   nop         landing of call sub (line 4) (encrypted, never run)
   97  'r'   in       4  in (line 7)
   98  '_'   out      5  out (line 8)
   99  ']'   jmp      6  jmp: ret (line 9)
```

Cómo leerlo:

- **El `call` (celda 2, paso 3) salta con su propio carácter.** En ese momento d = 2,
  así que `jmp` lee su propia celda: `` ` `` = 96. La VM cifra la celda 96 sin
  ejecutarla y sigue en la 97.
- **El `ret` (celda 99, paso 6) lee un dato.** d vale 5, porque d avanza un paso por
  instrucción aunque c haya saltado. La celda 5 guarda `"` = 34, así que vuelve a la
  35.
- **La celda 5 muestra "rot" pero nunca se ejecuta.** El cargador exige que todo byte
  decodifique a un opcode válido en su posición, así que un dato también "parece"
  instrucción.
- **8 pasos en total.** La versión hecha a mano en Calcbolge usa 46.

## 4. Verifícalo

```bash
python3 labeled_asm.py verify examples_labeled/call_return.mlab
```

```
PASS  input b'': oracle HALTED, output b'\xa8\xa8\xa8' == reference b'\xa8\xa8\xa8'
PASS  input b'': executed cells == planned path (8 steps)
PASS  input b'': Zig runner status/steps/output match
PASS  input b'AB': oracle HALTED, output b'ABB' == reference b'ABB'
PASS  input b'AB': executed cells == planned path (8 steps)
PASS  input b'AB': Zig runner status/steps/output match
PASS  input b'Hola': oracle HALTED, output b'Hoo' == reference b'Hoo'
...
PASS  control: every other valid byte in data cell 5 changes the executed path

LABELED_VERIFY=PASS
```

- `\xa8` es EOF: 59048 mod 256 = 168.
- La última línea es el control: con cualquier otro byte válido en la celda 5, el `ret`
  ya no vuelve a su sitio. Así se comprueba que el dato de verdad dirige el salto.

## 5. Lo que v0 rechaza

```bash
python3 labeled_asm.py compile examples_labeled/rejected_loop.mlab
```

```
COMPILE_ERROR: line 2: statement would execute twice; v0 has no loops (a Classic cell changes opcode every time it runs)
```

Código de salida 2. Es un límite **de v0**, no de Malbolge. En las 94 clases de
posición, **cada opcode dura exactamente una ejecución**: el cifrado no tiene puntos
fijos (sus ciclos miden 2, 4, 5, 6, 9 y 68). Los bucles se resuelven desde hace años:

- **Cómo lo hace HeLL/LMAO.** El lenguaje de Matthias Lutter
  (`github.com/esoteric-programmer/LMAO`) describe cada celda de código como un ciclo
  xlat2 (`Jmp/Nop/Nop`) y tiene `RNop`, un NOP que resiste bucles.
- **Por qué v0 no puede.** Medido el 2026-09-13: hay un `RNop` en las **94 de 94**
  posiciones, pero solo **14 de 752** candidatos pasan la validación del cargador. El
  resto hay que escribirlo **en tiempo de ejecución**, y por eso LMAO genera código de
  inicialización con `Opr`. v0 solo acomoda bytes en carga, así que no llega ahí.
- **Dónde ya está resuelto en el toolkit.** `malbolge-free` tiene lmao-lite (HeLL propio,
  bucles JZ/JNZ demostrados) para Malbolge Free, y MALDOOM usa HeLL → LMFAO →
  Unshackled.

También se rechazan:

- `ret` sin `call` pendiente;
- etiquetas desconocidas;
- programas que se acaban sin `end`;
- `rot`, `opr` y `movd`, que aún no están soportados.

## 6. Tests

```bash
python3 -m unittest test_labeled_asm -v
```

```
Ran 9 tests in 341.662s

OK

fuzz: compiled+verified=60 no_layout=0
```

El fuzz genera 60 programas al azar (bloques visitados en otro orden, con `goto`,
`call` y `ret`) y exige que todos pasen `verify`.

## Límites de v0

- **Camino fijo.** Sin condicionales ni bucles, el camino ejecutado no depende de la
  entrada. Los saltos cambian dónde vive el código, no lo que puede calcular. Son la
  base verificada para lo que viene.
- **Destinos hasta la celda 127.** Una dirección de aterrizaje sale de un byte imprimible
  (33 a 126).
- **No crecerlo hacia un HeLL propio.** Ya existen LMAO (Classic) y lmao-lite
  (Malbolge Free). Lo que aporta v0 es el arnés de verificación (oráculo + traza + Zig +
  mutación) y la vista `explain`.
