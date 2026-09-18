// bf_to_ir.zig — first lowering stage for the M6 BF -> Malbolge translator.
const std = @import("std");

pub const Op = enum { move_right, move_left, increment, decrement, output, input, jump_if_zero, jump_if_nonzero };

pub const Instruction = struct {
    op: Op,
    target: ?usize,
    source_pos: usize,
};

pub const Program = struct {
    code: std.array_list.Managed(Instruction),

    pub fn deinit(self: *Program) void {
        self.code.deinit();
    }
};

pub fn compile(source: []const u8, allocator: std.mem.Allocator) !Program {
    var code = std.array_list.Managed(Instruction).init(allocator);
    errdefer code.deinit();
    var opens = std.array_list.Managed(usize).init(allocator);
    defer opens.deinit();

    for (source, 0..) |ch, source_pos| {
        const op: ?Op = switch (ch) {
            '>' => .move_right,
            '<' => .move_left,
            '+' => .increment,
            '-' => .decrement,
            '.' => .output,
            ',' => .input,
            '[' => .jump_if_zero,
            ']' => .jump_if_nonzero,
            else => null,
        };
        if (op == null) continue;

        const index = code.items.len;
        switch (op.?) {
            .jump_if_zero => {
                try opens.append(index);
                try code.append(.{ .op = .jump_if_zero, .target = null, .source_pos = source_pos });
            },
            .jump_if_nonzero => {
                const open = opens.pop() orelse return error.UnmatchedBracket;
                try code.append(.{ .op = .jump_if_nonzero, .target = open, .source_pos = source_pos });
                code.items[open].target = index;
            },
            else => try code.append(.{ .op = op.?, .target = null, .source_pos = source_pos }),
        }
    }
    if (opens.items.len != 0) return error.UnmatchedBracket;
    return .{ .code = code };
}

pub fn validate(program: *const Program) !void {
    for (program.code.items) |instruction| {
        switch (instruction.op) {
            .jump_if_zero => {
                const target = instruction.target orelse return error.MissingJumpTarget;
                if (target >= program.code.items.len) return error.InvalidJumpTarget;
                if (program.code.items[target].op != .jump_if_nonzero) return error.WrongJumpTarget;
            },
            .jump_if_nonzero => {
                const target = instruction.target orelse return error.MissingJumpTarget;
                if (target >= program.code.items.len) return error.InvalidJumpTarget;
                if (program.code.items[target].op != .jump_if_zero) return error.WrongJumpTarget;
            },
            else => if (instruction.target != null) return error.UnexpectedJumpTarget,
        }
    }
}

pub const Error = error{
    UnmatchedBracket,
    MissingJumpTarget,
    InvalidJumpTarget,
    WrongJumpTarget,
    UnexpectedJumpTarget,
    InvalidSourcePosition,
};
