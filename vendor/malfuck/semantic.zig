// semantic.zig — backend semántico de Malfuck.
//
// Pipeline completo:
//   Brainfuck source
//     -> bf_to_ir (IR con loops)
//     -> bf_ir_image (BFIR1)
//     -> bfir1_backend.lowerImage (HeLL lmao-lite)
//     -> hell parse/resolveLayout/emit
//     -> texto de programa Malbolge Free (width=10 fixed, TAPE_BASE asistido)
//     -> malbolge_free.MalbolgeCore lo ejecuta.
//
// NOTA DE ALCANCE: el programa emitido requiere el runtime Malbolge Free
// (op asistida TAPE_BASE cero-inicializa la cinta 1000..1255, 256 celdas).
// No es un binario Malbolge Classic ejecutable por vm.c/Zigbolge; ese backend
// sigue marcado NOT_IMPLEMENTED (ver README). Aquí la semántica de BF sí es
// verdadera: loops e input se resuelven EN RUNTIME, no al compilar.

const std = @import("std");
const bf_ir = @import("bf_to_ir.zig");
const image = @import("bf_ir_image.zig");
const backend = @import("bfir1_backend.zig");
const hell = @import("hell.zig");
const mb = @import("malbolge_free.zig");
const ref_vm = @import("bf_ir_vm.zig");
const bf_ref = @import("bf_reference.zig");

pub const TAPE_SIZE: usize = 256;
pub const TAPE_BASE_ADDR: u128 = 1000;
pub const DEFAULT_MAX_STEPS: u64 = 5_000_000;

/// Compila Brainfuck a texto de programa Malbolge Free (fijado a width=10).
/// El caller libera el slice con `allocator.free`.
pub fn compile(source: []const u8, allocator: std.mem.Allocator) ![]u8 {
    var ir_prog = try bf_ir.compile(source, allocator);
    defer ir_prog.deinit();
    try bf_ir.validate(&ir_prog);

    const img = try image.encode(&ir_prog, allocator);
    defer allocator.free(img);

    var lowered = try backend.lowerImage(img, allocator);
    defer lowered.deinit(allocator);

    var parser = hell.Parser.init(lowered.slice());
    var program = try parser.parse(allocator);
    defer program.deinit(allocator);

    var layout = try hell.resolveLayout(&program, allocator);
    defer layout.deinit(allocator);

    var emitted = try hell.emit(&layout, allocator);
    defer emitted.deinit(allocator);

    return try allocator.dupe(u8, emitted.slice());
}

pub const RunReport = struct {
    status: []const u8,
    steps: u64,
    stdout: []u8,
    final_d: u128,
    tape: [TAPE_SIZE]u8,

    pub fn deinit(self: *RunReport, allocator: std.mem.Allocator) void {
        allocator.free(self.stdout);
    }
};

/// Ejecuta un texto de programa ya compilado en el core Malbolge Free
/// asistido (width 10, fixed). Útil para reusar un .mal con entrada nueva.
pub fn runText(program_text: []const u8, input: []const u8, allocator: std.mem.Allocator) !RunReport {
    var core = mb.MalbolgeCore.initFreeAssisted(allocator, 10, 59049, .fixed);
    defer core.deinit();
    try core.load(program_text);

    var res = try core.run(DEFAULT_MAX_STEPS, input);
    defer res.stdout.deinit(allocator);

    const stdout_copy = try allocator.dupe(u8, res.stdout.items);
    errdefer allocator.free(stdout_copy);

    var tape: [TAPE_SIZE]u8 = undefined;
    for (0..TAPE_SIZE) |i| {
        tape[i] = @intCast(try core.cell(TAPE_BASE_ADDR + i));
    }

    return .{
        .status = res.status,
        .steps = res.steps,
        .stdout = stdout_copy,
        .final_d = res.final_d,
        .tape = tape,
    };
}

/// Compila y ejecuta en el core Malbolge Free asistido (width 10, fixed).
pub fn run(source: []const u8, input: []const u8, allocator: std.mem.Allocator) !RunReport {
    const program_text = try compile(source, allocator);
    defer allocator.free(program_text);
    return runText(program_text, input, allocator);
}

/// Diferencial semántico: compara backend Malbolge Free contra la VM de
/// referencia BFIR1 en stdout, cinta final, puntero y terminación (M6.5).
pub fn differential(source: []const u8, input: []const u8, allocator: std.mem.Allocator) !void {
    var ir_prog = try bf_ir.compile(source, allocator);
    defer ir_prog.deinit();
    try bf_ir.validate(&ir_prog);

    var ref = try ref_vm.run(&ir_prog, input, .{ .tape_size = TAPE_SIZE, .max_steps = 1_000_000 }, allocator, false);
    defer ref.deinit();

    var got = try run(source, input, allocator);
    defer got.deinit(allocator);

    if (!std.mem.eql(u8, "HALTED", got.status)) return error.BackendNotHalted;
    if (!std.mem.eql(u8, ref.output.items, got.stdout)) return error.StdoutMismatch;
    for (0..TAPE_SIZE) |i| {
        if (ref.tape.items[i] != got.tape[i]) return error.TapeMismatch;
    }
    const expect_d: u128 = @intCast(TAPE_BASE_ADDR + ref.pointer);
    if (expect_d != got.final_d) return error.PointerMismatch;
}

const HELLO_WORLD =
    ">++++++++[>+++++++++<-]>." ++
    ">++++++++++[>++++++++++<-]>+." ++
    ">++++++++++[>++++++++++<-]>++++++++." ++
    ">++++++++++[>++++++++++<-]>++++++++." ++
    ">++++++++++[>++++++++++<-]>+++++++++++." ++
    ">++++[>++++++++<-]>." ++
    ">++++++++++[>++++++++<-]>+++++++." ++
    ">++++++++++[>++++++++++<-]>+++++++++++." ++
    ">++++++++++[>++++++++++<-]>++++++++++++++." ++
    ">++++++++++[>++++++++++<-]>++++++++." ++
    ">++++++++++[>++++++++++<-]>." ++
    ">++++[>++++++++<-]>+.";

test "semantic differential: cinco programas end-to-end" {
    const allocator = std.testing.allocator;
    const cases = [_]struct { source: []const u8, input: []const u8 }{
        .{ .source = "+++[-].", .input = "" },
        .{ .source = "++[>++<-]>.", .input = "" },
        .{ .source = ",[.,]", .input = "AB" },
        .{ .source = "+[>+<-]>.", .input = "" },
        .{ .source = HELLO_WORLD, .input = "" },
    };
    for (cases) |case| {
        try differential(case.source, case.input, allocator);
    }
}

test "semantic hello world imprime Hello World!" {
    const allocator = std.testing.allocator;
    var report = try run(HELLO_WORLD, "", allocator);
    defer report.deinit(allocator);
    try std.testing.expectEqualStrings("HALTED", report.status);
    try std.testing.expectEqualStrings("Hello World!", report.stdout);
}

test "semantic compile produce texto imprimible" {
    const allocator = std.testing.allocator;
    const text = try compile(HELLO_WORLD, allocator);
    defer allocator.free(text);
    try std.testing.expect(text.len > 0);
    for (text) |ch| {
        try std.testing.expect(ch >= 33 and ch <= 126);
    }
}

test "semantic programa compilado responde a input nuevo en runtime" {
    // La prueba clave del backend verdadero: se compila UNA VEZ ",[.,]" y el
    // MISMO texto de programa se ejecuta con dos entradas distintas.
    // Si el backend fuera extensional (salida horneada), fallaría.
    const allocator = std.testing.allocator;
    const text = try compile(",[.,]", allocator);
    defer allocator.free(text);

    var first = try runText(text, "XY", allocator);
    defer first.deinit(allocator);
    var second = try runText(text, "1234", allocator);
    defer second.deinit(allocator);

    try std.testing.expectEqualStrings("HALTED", first.status);
    try std.testing.expectEqualStrings("HALTED", second.status);
    try std.testing.expectEqualStrings("XY", first.stdout);
    try std.testing.expectEqualStrings("1234", second.stdout);
}
