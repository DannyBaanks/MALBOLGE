# Direct Opcode Encoding + Quijote first divergence — 2026-09-12

## 1. Formula exacta (auditada en codigo)

Classic (`classic_encoder.py:29-35`):

    r     = (op - c) % 94
    ascii = r if r >= 33 else r + 94

Malbolge-19 (`unshackled_codec.py:39-44`):

    r     = (op - c - OFFSETS[c // THIRD]) % 94
    ascii = r if r >= 33 else r + 94
    END = 3**19, THIRD = 3**18, OFFSETS = (0, 117, 140)

`offset(c)` = `OFFSETS[c // 3**18]`: un desplazamiento aditivo por tercio de
memoria. La formula general `offset_epoch_ladder.offsets_for(19)` reproduce
exactamente `(0, 117, 140)` (test `test_offset_epoch_ladder.py:21`).

## 2. Significado de cada variable

| simbolo | significado |
|---|---|
| `op` | opcode decodificado: uno de {4,5,23,39,40,62,68,81} |
| `c` | posicion de carga de la celda (loader) == valor del registro `c` al ejecutarla |
| `OFFSETS[r]` | correccion aditiva mod 94 del runtime 3^19 por tercio de memoria |
| `r` | residuo mod 94 antes del plegado ASCII |
| `ascii` | caracter fuente imprimible 33..126 |

## 3. Prueba encode/decode

DIRECT_OPCODE_ENCODING=PASS.

- Caso minimo: `assemble19([23,5,81])` -> `'ubO'`; `decode` por posicion
  recupera `[23,5,81]` exacto (test `test_direct_opcode_encoding_minimum`).
- Fronteras de region: `{0,1,THIRD-1,THIRD,THIRD+1,2*THIRD-1,2*THIRD,END-1}`
  x 8 opcodes = 64/64 round-trip OK.
- Cobertura completa: `encode` depende de `c` solo via `(op - c - offset) % 94`,
  asi que 94 posiciones x 3 regiones x 8 opcodes = 2256 casos agotan todos los
  residuos posibles (`test_all_residues_all_regions_always_printable`).
- Classic: paridad exhaustiva 8 x 59049 = 472392 pares PASS.
- `start_c != 0` soportado: `verify_plan(ops, start_c=THIRD + 7)` PASS.

## 4. Assembler minimo

```python
def assemble19(opcodes: list[int], start_c: int = 0) -> str:
    return "".join(encode(opcode, start_c + i)
                   for i, opcode in enumerate(opcodes))
```

En `unshackled_codec.py`. Verificador independiente: `decode_program(source,
start_c)` (decodifica sin tocar el plan) y `verify_plan(plan, start_c)`.

## 5. Tests

`py -m unittest test_unshackled_codec.py test_classic_codec.py test_classic_encoder.py -v`
-> 13/13 OK (2026-09-12). Suite malbolge-free intacta (34/34 PASS, verificado
antes de esta entrega).

## 6. Workers/rutas que quedan innecesarios

Para el PROBLEMA A (opcode conocido -> caracter fuente):

- Todo brute force sobre caracteres fuente para una posicion conocida. En
  MALBOLGE se audito `classic_challenge.py`, `e15_region_search.py`,
  `e15_vm_probe.py`, `dimension_epoch_ladder.py`, `dynamic_epoch.py`: todos
  resuelven ya via encoders directos; `e15_region_search.py` busca REGIONES
  (problema B), no caracteres, y no se toca.
- En `malbolge-free`, `tests/branch_gadget_search*.py` son problema B
  (sintesis semantica), no encoding; no quedan obsoletos por este trabajo.

## 7. Primera divergencia Classic vs 19 (causa raiz)

Sondas sobre planes literales, trazas paso a paso y cross-check contra el
runtime real `intermediate_vm_runner.exe` (dimension 19, tape 3^19 completo):

| caso | fuentes | decode | primera divergencia |
|---|---|---|---|
| echo `[23,5,81]` in='H' | identicas | identico | ninguna (ambos imprimen 'H') |
| literal opr `[62,5,81]` | identicas | identico | **step 1, campo `mem_d_after` — SEMANTICA** |
| literal rot `[39,5,81]` | identicas | identico | ninguna en este caso (39%3==0) |

Detalle del caso divergente (opcodes decodificados identicos: `[62,5,81]`):

- Classic k10: `mem[0] = crazy10(0,62) = 29555`, out byte `115` ('s').
- k19: `mem[0] = crazy19(0,62) = 581130764`, out byte `12` (`0x0c`).
- Runtime real k19 confirma: `a=581130764 out_hex=0c steps=3 HALTED`.

Conclusion: **el opcode deseado SI es el ejecutado; lo que cambia es la
semantica del opcode bajo ancho 19** (crazy/rotate operan sobre 19 trits, EOF
es 3^19-1). La codificacion no es la causa.

Evidencia: `evidence/quijote_first_divergence_20260912.json`
(claims: `QUIJOTE_ENCODING_INTACT_ON_CASES=true`,
`QUIJOTE_OPCODE_PLAN=DEMONSTRATED_SEMANTIC_DIVERGENCE_NOT_ENCODING`).
Hashes: `evidence/direct_encoding_20260912.hashes.json`.

## 8. Pertenece a ENCODING (resuelto, directo)

- opcode conocido + posicion -> caracter. Inverso exacto del dispatch.
- Cobertura: Classic 472392 pares; k19 residuos completos y fronteras.
- `assemble19(ops, start_c=0)` + `decode_program` + `verify_plan`.

## 9. Pertenece a SEMANTIC SYNTHESIS (otra capa)

- Paso de "quiero imprimir H" a una secuencia de opcodes/estados.
- Revisitas a celdas ya cifradas por xlat (el assembler calcula solo la
  posicion inicial; una celda reejecutada tras cifrado ya no decodifica igual).
- Saltos que cambian `c` (la posicion efectiva deja de ser `start_c + i`).
- Efectos width-19 de crazy/rotate/EOF al trasladar planes Classic.

## 10. NOT_DEMONSTRATED

- Paridad contra un Unshackled externo con `srand(time())`: irreproducible por
  construccion (documentado en malbolge-free `docs/FREE_SEMANTICS.md`).
- Crossings de region 1->2 por `c` con un programa fuente real > 3^18:
  probado solo a nivel de codec (encode/decode en limites), no en runtime.
- Sintesis semantica general (problema B) para literales arbitrarios.
