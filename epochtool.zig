// epochtool.zig — thin CLI over the vendored Malfuck semantic backend.
//
//   epochtool compile <in.bf> <out.mal>
//       Brainfuck -> Malbolge Free text (width=10 fixed, TAPE_BASE assisted).
//
//   epochtool run <in.mal> <stdin-hex>
//       Run a compiled program on the Free core with the given stdin bytes,
//       print "status=... stdout_hex=...".
//
// This is the executor for V2 epochs: each epoch is a COMPLETE Malbolge Free
// computation that genuinely transforms its stdin; the Python harness seals the
// boundary (sha256), so no state is resumed and only output bytes cross.

const std = @import("std");
const semantic = @import("vendor/malfuck/semantic.zig");

fn hexDecode(hex: []const u8, alloc: std.mem.Allocator) ![]u8 {
    var out = try alloc.alloc(u8, hex.len / 2);
    for (0..hex.len / 2) |i| {
        const hi = std.fmt.charToDigit(hex[2 * i], 16) catch return error.BadHex;
        const lo = std.fmt.charToDigit(hex[2 * i + 1], 16) catch return error.BadHex;
        out[i] = @intCast(hi * 16 + lo);
    }
    return out;
}

fn hexEncode(data: []const u8, alloc: std.mem.Allocator) ![]const u8 {
    var out = try std.ArrayList(u8).initCapacity(alloc, data.len * 2);
    for (data) |b| try out.appendSlice(alloc, &([_]u8{ hexchars[b / 16], hexchars[b % 16] }));
    return out.toOwnedSlice(alloc);
}

const hexchars = "0123456789abcdef";

pub fn main(init: std.process.Init) !void {
    const alloc = init.arena.allocator();
    var args = try std.process.Args.Iterator.initAllocator(init.minimal.args, alloc);
    defer args.deinit();
    _ = args.next();
    const cmd = args.next() orelse {
        std.debug.print("usage: epochtool compile <in.bf> <out.mal> | epochtool run <in.mal> <stdin-hex>\n", .{});
        return;
    };

    if (std.mem.eql(u8, cmd, "compile")) {
        const bf_path = args.next() orelse return error.MissingArg;
        const out_path = args.next() orelse return error.MissingArg;
        const source = try (std.Io.Dir.cwd()).readFileAlloc(init.io, bf_path, alloc, .unlimited);
        const program = try semantic.compile(source, alloc);
        try (std.Io.Dir.cwd()).writeFile(init.io, .{ .sub_path = out_path, .data = program });
        std.debug.print("compiled={d} cells\n", .{program.len});
        return;
    }

    if (std.mem.eql(u8, cmd, "run")) {
        const mal_path = args.next() orelse return error.MissingArg;
        const hex = args.next() orelse return error.MissingArg;
        const program = try (std.Io.Dir.cwd()).readFileAlloc(init.io, mal_path, alloc, .unlimited);
        const input = try hexDecode(hex, alloc);
        var report = try semantic.runText(program, input, alloc);
        defer report.deinit(alloc);
        const shex = try hexEncode(report.stdout, alloc);
        std.debug.print("status={s} steps={d} stdout_hex={s}\n", .{ report.status, report.steps, shex });
        return;
    }

    std.debug.print("unknown command {s}\n", .{cmd});
}