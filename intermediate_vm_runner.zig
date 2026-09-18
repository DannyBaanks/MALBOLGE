const std = @import("std");

const chunk_trits: usize = 5;
const chunk_base: usize = 243;
const table_size: usize = chunk_base * chunk_base;
const translated = "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";
const valid = [_]usize{ 4, 5, 23, 39, 40, 62, 68, 81 };
const crazy_digits = [3][3]u8{ .{ 1, 0, 0 }, .{ 1, 0, 2 }, .{ 2, 2, 1 } };

fn isValid(op: usize) bool {
    for (valid) |candidate| if (op == candidate) return true;
    return false;
}

fn pow3(k: usize) usize {
    var value: usize = 1;
    for (0..k) |_| value *= 3;
    return value;
}

fn buildCrazyTable() [table_size]u8 {
    var result: [table_size]u8 = undefined;
    for (0..chunk_base) |a0| {
        for (0..chunk_base) |b0| {
            var a = a0;
            var b = b0;
            var value: usize = 0;
            var place: usize = 1;
            for (0..chunk_trits) |_| {
                value += @as(usize, crazy_digits[b % 3][a % 3]) * place;
                a /= 3;
                b /= 3;
                place *= 3;
            }
            result[a0 * chunk_base + b0] = @intCast(value);
        }
    }
    return result;
}

fn crazyWidth(a0: u32, b0: u32, dimension: usize, table: *const [table_size]u8) u32 {
    var a: usize = a0;
    var b: usize = b0;
    var remaining = dimension;
    var result: usize = 0;
    var place: usize = 1;
    while (remaining > 0) {
        const take = @min(remaining, chunk_trits);
        const modulus = pow3(take);
        const chunk = @as(usize, table[a % chunk_base * chunk_base + b % chunk_base]) % modulus;
        result += chunk * place;
        a /= chunk_base;
        b /= chunk_base;
        place *= modulus;
        remaining -= take;
    }
    return @intCast(result);
}

fn hexDecode(hex: []const u8, alloc: std.mem.Allocator) ![]u8 {
    if (hex.len % 2 != 0) return error.BadHex;
    const result = try alloc.alloc(u8, hex.len / 2);
    for (0..result.len) |i| {
        const hi = std.fmt.charToDigit(hex[2 * i], 16) catch return error.BadHex;
        const lo = std.fmt.charToDigit(hex[2 * i + 1], 16) catch return error.BadHex;
        result[i] = @intCast(hi * 16 + lo);
    }
    return result;
}

const Sha256 = std.crypto.hash.sha2.Sha256;

fn tapeDigest(tape: []const u32) [Sha256.digest_length]u8 {
    // Same bytes as Python's memoryview(array('I')).cast('B') on little-endian.
    var digest: [Sha256.digest_length]u8 = undefined;
    Sha256.hash(std.mem.sliceAsBytes(tape), &digest, .{});
    return digest;
}

fn printHex(bytes: []const u8) void {
    for (bytes) |byte| std.debug.print("{x:0>2}", .{byte});
}

fn emit(status: []const u8, dimension: usize, size: usize, steps: usize,
    out: []const u8, a: u32, c: usize, d: usize, visited: u8,
    entry_steps: [3]usize, entry_ops: [3]usize,
    initial_digest: [Sha256.digest_length]u8, tape: []const u32) void {
    const out0: i32 = if (out.len > 0) out[0] else -1;
    const out1: i32 = if (out.len > 1) out[1] else -1;
    std.debug.print(
        "RESULT status={s} dimension={d} memory_cells={d} fill=true steps={d} out_len={d} out0={d} out1={d} a={d} c={d} d={d} visited={d} e0step={d} e1step={d} e2step={d} e0op={d} e1op={d} e2op={d}",
        .{ status, dimension, size, steps, out.len, out0, out1, a, c, d,
           visited, entry_steps[0], entry_steps[1], entry_steps[2],
           entry_ops[0], entry_ops[1], entry_ops[2] });
    std.debug.print(" out_hex=", .{});
    if (out.len == 0) std.debug.print("-", .{}) else printHex(out);
    std.debug.print(" initial_tape_sha256=", .{});
    printHex(&initial_digest);
    std.debug.print(" final_tape_sha256=", .{});
    const final_digest = tapeDigest(tape);
    printHex(&final_digest);
    std.debug.print("\n", .{});
}

pub fn main(init: std.process.Init) !void {
    const arena = init.arena.allocator();
    var args = try std.process.Args.Iterator.initAllocator(init.minimal.args, arena);
    defer args.deinit();
    _ = args.next();
    const dimension = try std.fmt.parseInt(usize, args.next() orelse return error.MissingDimension, 10);
    // Source is hex on argv, or `@path` to read a file. argv is capped at
    // ~32K chars on Windows, so programs above ~16KB need the file form.
    // File form strips whitespace, as the Classic loader does.
    const source_arg = args.next() orelse return error.MissingSource;
    const source = if (source_arg.len > 0 and source_arg[0] == '@') blk: {
        const raw = try (std.Io.Dir.cwd()).readFileAlloc(init.io, source_arg[1..], arena, .unlimited);
        var kept: usize = 0;
        for (raw) |byte| {
            if (byte == ' ' or byte == '\t' or byte == '\r' or byte == '\n' or byte == 0x0b or byte == 0x0c) continue;
            raw[kept] = byte;
            kept += 1;
        }
        break :blk raw[0..kept];
    } else try hexDecode(source_arg, arena);
    const input_arg = args.next() orelse return error.MissingInput;
    const input = if (input_arg.len == 0) try arena.alloc(u8, 0) else try hexDecode(input_arg, arena);
    const max_steps = try std.fmt.parseInt(usize, args.next() orelse return error.MissingFuel, 10);
    const offsets = [3]usize{
        try std.fmt.parseInt(usize, args.next() orelse return error.MissingOffset, 10),
        try std.fmt.parseInt(usize, args.next() orelse return error.MissingOffset, 10),
        try std.fmt.parseInt(usize, args.next() orelse return error.MissingOffset, 10),
    };
    const size = pow3(dimension);
    const third = pow3(dimension - 1);
    const tape = std.heap.page_allocator.alloc(u32, size) catch {
        std.debug.print("RESULT status=RESOURCE_LIMIT dimension={d} memory_cells={d} fill=false\n", .{ dimension, size });
        return;
    };
    defer std.heap.page_allocator.free(tape);
    @memset(tape, 0);
    // The crazy-fill reads the two previous cells, so a program needs >= 2 cells.
    if (source.len < 2) return error.ProgramTooShort;
    if (source.len > size) return error.ProgramTooLong;
    for (source, 0..) |char, position| {
        if (char < 33 or char > 126) return error.InvalidCharacter;
        const op = (@as(usize, char) + position + offsets[position / third]) % 94;
        if (!isValid(op)) return error.InvalidSource;
        tape[position] = char;
    }
    var table = buildCrazyTable();
    for (source.len..size) |position| {
        tape[position] = crazyWidth(tape[position - 1], tape[position - 2], dimension, &table);
    }
    const initial_digest = tapeDigest(tape);

    var a: u32 = 0;
    var c: usize = 0;
    var d: usize = 0;
    var input_pos: usize = 0;
    var output: [65536]u8 = undefined;
    var output_len: usize = 0;
    var visited: u8 = 0;
    var entry_steps = [3]usize{ 0, 0, 0 };
    var entry_ops = [3]usize{ 0, 0, 0 };
    var steps: usize = 0;
    while (steps < max_steps) {
        steps += 1;
        const region = c / third;
        const op = (@as(usize, tape[c]) + c + offsets[region]) % 94;
        const bit: u8 = @as(u8, 1) << @intCast(region);
        if (visited & bit == 0) {
            visited |= bit;
            entry_steps[region] = steps;
            entry_ops[region] = op;
        }
        switch (op) {
            4 => c = tape[d],
            5 => {
                if (output_len == output.len) {
                    // Never overflow the buffer and never drop bytes silently.
                    emit("OUTPUT_CAP", dimension, size, steps, output[0..output_len], a, c, d,
                        visited, entry_steps, entry_ops, initial_digest, tape);
                    return;
                }
                output[output_len] = @truncate(a);
                output_len += 1;
            },
            23 => {
                if (input_pos < input.len) {
                    a = input[input_pos];
                    input_pos += 1;
                } else a = @intCast(size - 1);
            },
            39 => {
                const value = tape[d];
                tape[d] = value / 3 + (value % 3) * @as(u32, @intCast(third));
                a = tape[d];
            },
            40 => d = tape[d],
            62 => {
                tape[d] = crazyWidth(a, tape[d], dimension, &table);
                a = tape[d];
            },
            81 => {
                emit("HALTED", dimension, size, steps, output[0..output_len], a, c, d,
                    visited, entry_steps, entry_ops, initial_digest, tape);
                return;
            },
            else => {},
        }
        if (tape[c] >= 33 and tape[c] <= 126) tape[c] = translated[tape[c] - 33];
        c = (c + 1) % size;
        d = (d + 1) % size;
    }
    emit("OUT_OF_FUEL", dimension, size, steps, output[0..output_len], a, c, d,
        visited, entry_steps, entry_ops, initial_digest, tape);
}
