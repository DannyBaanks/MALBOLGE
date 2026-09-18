# Guia: barrido de VM completa E11-E18

Salida real capturada el 2026-09-12. Todo se ejecuta desde `MALBOLGE/`.

## Que se prueba

Si el perfil parametrico de ancho k corre sobre una cinta real de 3^k celdas
con crazy-fill completo, de E11 a E18, y si **dos implementaciones
independientes** (runner Zig y referencia Python) dan exactamente lo mismo.

## Compilar el runner

```powershell
zig build-exe intermediate_vm_runner.zig -O ReleaseSafe -femit-bin=intermediate_vm_runner.exe
```

Usa `intermediate_vm_runner.exe`. El binario sin extension que hay al lado es
anterior a los arreglos y falla con stdin vacio.

## Una ejecucion suelta del runner

Argumentos: `ancho  codigo_en_hex  stdin_en_hex  pasos_max  offset0 offset1 offset2`.
El reporte sale por **stderr**.

```powershell
.\intermediate_vm_runner.exe 15 286160723a "" 512 0 105 116
```

```text
RESULT status=HALTED dimension=15 memory_cells=14348907 fill=true steps=139 out_len=2 out0=141 out1=198 a=2391493 c=7174468 d=142 visited=7 e0step=1 e1step=3 e2step=79 e0op=40 e1op=61 e2op=70 out_hex=8dc6 initial_tape_sha256=4a639c5cc5674681638de786ee0256d0151fb614e7a3613da6a64beaa0f8d804 final_tape_sha256=f86b2859d68b24e8297e300e3de50cf9683b99f08cdcf9dcd85ab7bb5949df32
```

Para programas de mas de ~16 KB (limite de argv en Windows) usa `@archivo`
en lugar del hex:

```powershell
.\intermediate_vm_runner.exe 10 @quine_lutter.mal "" 400000000 0 0 0
```

## La referencia Python

```powershell
py reference_width_vm.py 11 "(a`r:" --offsets 0 171 154
```

```text
{"a": 29535, "c": 88588, "d": 160, "dimension": 11, "final_tape_sha256": "3cb6af80f92afa750ece781dba1c9eb128cb7abc9eba918fb37e5adf9565794c", "first_entries": {"0": {"opcode": 40, "step": 1}, "1": {"opcode": 89, "step": 3}}, "initial_tape_sha256": "140a9564a4c1cd9c86d03bfce36db3b10be01d3b0562ae69a701b0de0d319e92", "load_seconds": 0.05, "memory_cells": 177147, "status": "HALTED", "stdout_hex": "00", "steps": 223, "visited": [0, 1]}
```

## El barrido completo

```powershell
py run_intermediate_sweep.py
```

```text
E11: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=223 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 0.2s)
E12: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=41 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 0.4s)
E13: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=407 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 1.2s)
E14: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=101 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 5.3s)
E15: toy=PASS witness=PASS visited=[0, 1, 2] status=HALTED steps=139 all_region=DEMONSTRATED parity=PASS (4 runs, 34.5s)
E16: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=58 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 69.1s)
E17: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=319 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 243.1s)
E18: toy=PASS witness=FAIL visited=[0, 1] status=HALTED steps=189 all_region=NOT_DEMONSTRATED parity=PASS (2 runs, 560.6s)
```

Tarda ~15 minutos: casi todo es la referencia Python en E17 y E18.
Reporte completo: `evidence/intermediate_vm_sweep_report.json`.

| Resultado | Significa | Que hacer |
| --- | --- | --- |
| `toy=PASS` | La cinta se lleno completa y [IN,OUT,END] corrio | Nada: pero no prueba nada del ancho, da lo mismo en todos |
| `witness=FAIL visited=[0, 1]` | El testigo de E15 no llega a la region 2 en ese ancho | No es un fallo de la formula; el testigo se eligio para E15 |
| `parity=PASS` | Zig y Python coinciden en 10 campos, hashes de cinta incluidos | Es la parte fuerte del resultado |
| `parity=FAIL` | Las dos implementaciones divergen | Parar: una de las dos esta mal; ver `differences` en el reporte |
| `parity=NOT_DEMONSTRATED` | Una de las dos no pudo reservar memoria o se agoto el tiempo | No es un fallo semantico; liberar RAM y repetir |

## Trampas

- El juguete [IN,OUT,END] **no depende del ancho**: da 3 pasos, `5a` y
  a,c,d = 90,2,2 en los 8 anchos. Solo cambia la cinta. No lo uses como
  prueba de semantica de ancho k.
- E18 necesita ~1,55 GB libres para cada implementacion. Corren una detras de
  otra, nunca a la vez.
- No hay interprete canonico para k distinto de 10. La paridad es entre dos
  implementaciones del mismo perfil escrito, no contra un oraculo externo.
